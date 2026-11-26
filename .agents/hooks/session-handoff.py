#!/usr/bin/env python3
"""Session handoff: measure this session's context and open one successor under Paseo.

Usage:
  session-handoff.py context
  session-handoff.py spawn --prompt-file PATH [--title TEXT]

context  prints the token count of this session's latest main-thread request
         (input + cache read + cache creation). A Pi session is read from
         PI_SESSION_FILE (latest assistant message usage, Pi 1.6.0 session JSONL)
         and/or the Claude Code transcript of CLAUDE_CODE_SESSION_ID; when both
         exist, the more recently written record is this session's.
         Prints `unknown` and exits 3 when neither yields a usage record.
spawn    opens a successor agent with this agent's provider, model, thinking and
         mode (mode only when `paseo provider ls` lists modes for the provider),
         in the same working directory, labelled handoff-from=<this agent>,
         then detaches it so it outlives this agent. Prints the new agent id.

Exit codes for spawn: 0 opened; 64 usage or empty/option-like prompt; 69 not a
Paseo agent session (PASEO_CLI / PASEO_AGENT_ID unset); 73 this agent already
opened a successor; 71 the Paseo CLI failed before the open was attempted. Those
mean no successor was opened. 70 means the open was attempted and its result could not
be read: stderr names the successor found by label, or says none is listed.
A failed detach is warned on stderr with exit 0.
The environment check cannot tell a Paseo agent's main thread from a subagent
or child process that inherited its variables; the caller must be the former.
"""
import glob
import json
import os
import subprocess
import sys

EX_USAGE, EX_UNAVAILABLE, EX_SOFTWARE, EX_OSERR, EX_CANTCREAT = 64, 69, 70, 71, 73
FAILURES = (RuntimeError, ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.TimeoutExpired)


def read_lines(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except OSError:
        return []


def records(lines):
    for line in reversed(lines):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("message"), dict):
            yield rec, rec["message"]


def pi_total(path):
    # Pi 1.6.0 session JSONL: count assistant requests only. Tool results may carry
    # usage, and top-level `usage` entries (e.g. cache warming) have no `message`.
    for _, msg in records(read_lines(path)):
        usage = msg.get("usage")
        if msg.get("role") == "assistant" and isinstance(usage, dict):
            total = sum(int(usage.get(k) or 0) for k in ("input", "cacheRead", "cacheWrite"))
            if total:
                return total
    return None


def claude_total(path):
    for rec, msg in records(read_lines(path)):
        usage = msg.get("usage")
        if not rec.get("isSidechain") and isinstance(usage, dict):
            total = sum(int(usage.get(k) or 0) for k in
                        ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            if total:
                return total
    return None


def context():
    candidates = []
    pi_file = os.environ.get("PI_SESSION_FILE", "")
    if pi_file:
        candidates.append((pi_file, pi_total))
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    root = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    for path in (glob.glob(os.path.join(root, "projects", "*", f"{sid}.jsonl")) if sid else [])[:1]:
        candidates.append((path, claude_total))

    # A child CLI inherits its parent's variables (Pi passes PI_SESSION_FILE to a
    # `claude -p` it launches), so the running session is the one whose record was
    # written last. A Codex child of Pi has no record here and reads its parent.
    def mtime(item):
        try:
            return os.path.getmtime(item[0])
        except OSError:
            return -1.0
    for path, total_of in sorted(candidates, key=mtime, reverse=True):
        total = total_of(path)
        if total:
            print(total)
            return 0
    print("unknown")
    return 3


def paseo(cli, *args):
    r = subprocess.run([cli, *args], capture_output=True, text=True, timeout=120, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"paseo {args[0]} exited {r.returncode}: {r.stderr.strip()[:300]}")
    return r.stdout


def spawn(argv):
    opts = {"--prompt-file": None, "--title": None}
    i = 0
    while i < len(argv):
        if argv[i] in opts and i + 1 < len(argv):
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            return usage()
    try:
        with open(opts["--prompt-file"] or "", encoding="utf-8") as f:
            prompt = f.read().strip()
    except (ValueError, OSError):
        return usage()
    if not prompt or prompt.startswith("-"):
        return usage()
    cli, me = os.environ.get("PASEO_CLI"), os.environ.get("PASEO_AGENT_ID")
    if not cli or not me:
        print("session-handoff: not a Paseo agent session; no successor opened", file=sys.stderr)
        return EX_UNAVAILABLE
    labelled = ("ls", "-a", "-g", "--label", f"handoff-from={me}", "--json")
    try:
        prior = json.loads(paseo(cli, *labelled))
        if prior:
            print(f"session-handoff: successor already opened ({prior[0].get('id')}); none opened", file=sys.stderr)
            return EX_CANTCREAT
        info = json.loads(paseo(cli, "inspect", me, "--json"))
        # `run --mode` accepts only registered modes, yet inspect reports a placeholder
        # ("default") for providers with none (pi, opencode, copilot) — pass it only when registered.
        providers = {p.get("provider"): p for p in json.loads(paseo(cli, "provider", "ls", "--json"))}
        mode_args = ["--mode", info["Mode"]] if providers.get(info["Provider"], {}).get("modes") else []
        args = ["run", "--no-wait", "--json", "--provider", f"{info['Provider']}/{info['Model']}",
                *mode_args,
                "--cwd", os.environ.get("PASEO_AGENT_CWD") or os.getcwd(),
                "--label", f"handoff-from={me}"]
        if info.get("Thinking"):
            args += ["--thinking", info["Thinking"]]
        if opts["--title"]:
            args += ["--title", opts["--title"]]
    except FAILURES as e:
        print(f"session-handoff: {e}; no successor opened", file=sys.stderr)
        return EX_OSERR
    try:
        new = json.loads(paseo(cli, *args, prompt))["agentId"]
    except FAILURES as e:
        try:
            found = [a.get("id") for a in json.loads(paseo(cli, *labelled))]
        except FAILURES:
            found = None
        state = "no successor is listed" if found == [] else "the agent list could not be read"
        if found:
            try:
                paseo(cli, "agent", "detach", found[0])
                state = f"successor {found[0]} is listed and detached"
            except FAILURES:
                state = f"successor {found[0]} is listed but still attached"
        print(f"session-handoff: open attempted but it failed or its result was unreadable ({e}); {state}",
              file=sys.stderr)
        return EX_SOFTWARE
    try:
        paseo(cli, "agent", "detach", new)
    except FAILURES as e:
        print(f"session-handoff: successor {new} opened but not detached: {e}", file=sys.stderr)
    print(new)
    return 0


def usage():
    print(__doc__, file=sys.stderr)
    return EX_USAGE


def main(argv):
    if argv == ["context"]:
        return context()
    if argv[:1] == ["spawn"]:
        return spawn(argv[1:])
    return usage()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
