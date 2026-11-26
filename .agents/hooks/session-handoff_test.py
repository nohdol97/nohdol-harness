#!/usr/bin/env python3
"""Behavior of the session handoff helper (context measurement, successor guards)."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "session-handoff.py")
ME = "agent-me"

# Fake Paseo CLI. Like the real parser it rejects unknown options and options
# missing their value, so a call the real CLI would refuse fails here too.
FAKE = r'''#!/usr/bin/env python3
import json, os, sys
state = os.environ["FAKE_STATE"]
argv = sys.argv[1:]
with open(os.path.join(state, "calls.jsonl"), "a") as f:
    f.write(json.dumps(argv) + "\n")
def load(name, default):
    p = os.path.join(state, name)
    return json.load(open(p)) if os.path.exists(p) else default
def parse(args, valued, flags, positional):
    opts, pos, i = {}, [], 0
    while i < len(args):
        a = args[i]
        if a in valued:
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                sys.exit(f"error: option {a} argument missing")
            opts[a] = args[i + 1]; i += 2
        elif a in flags:
            opts[a] = True; i += 1
        elif a.startswith("-"):
            sys.exit(f"error: unknown option {a}")
        else:
            pos.append(a); i += 1
    if len(pos) != positional:
        sys.exit(f"error: expected {positional} positional argument(s), got {len(pos)}")
    return opts, pos
cmd, rest = argv[0], argv[1:]
if os.environ.get("FAKE_FAIL") == cmd:
    sys.exit("boom")
if cmd == "ls":
    opts, _ = parse(rest, {"--label"}, {"-a", "-g", "--json"}, 0)
    if os.environ.get("FAKE_BAD_LS"):
        print(json.dumps(["not-an-agent"]))
    elif "--label" in opts:
        print(json.dumps(load("successors.json", [])))
    else:
        print(json.dumps(load("ls.json", [])))
elif cmd == "inspect":
    parse(rest, set(), {"--json"}, 1)
    info = {"Provider": "claude", "Model": "m-1", "Thinking": "medium", "Mode": "auto"}
    if os.environ.get("FAKE_UTF8"):
        # Real Paseo writes UTF-8 regardless of locale; "가" carries byte 0x80.
        info["Title"] = "가"
        sys.stdout.buffer.write(json.dumps(info, ensure_ascii=False).encode("utf-8") + b"\n")
    else:
        print(json.dumps(info))
elif cmd == "run":
    parse(rest, {"--provider", "--mode", "--cwd", "--label", "--thinking", "--title"}, {"--no-wait", "--json"}, 1)
    if os.environ.get("FAKE_RUN_GARBAGE"):
        if os.environ["FAKE_RUN_GARBAGE"] == "created":
            json.dump([{"id": "agent-new"}], open(os.path.join(state, "successors.json"), "w"))
        print("not json")
    else:
        print(json.dumps({"agentId": "agent-new", "status": "running"}))
elif cmd == "agent" and rest[:1] == ["detach"]:
    parse(rest[1:], set(), set(), 1)
    if os.environ.get("FAKE_FAIL") == "detach":
        sys.exit("boom")
else:
    sys.exit(f"error: unknown command {cmd}")
'''


class Handoff(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.cli = os.path.join(self.dir, "paseo")
        Path(self.cli).write_text(FAKE)
        os.chmod(self.cli, os.stat(self.cli).st_mode | stat.S_IXUSR)
        self.prompt = os.path.join(self.dir, "prompt.txt")
        Path(self.prompt).write_text("이어서 진행해\n")

    def run_script(self, args, **env):
        e = {k: v for k, v in os.environ.items()
             if not k.startswith(("PASEO_", "FAKE_"))
             and k not in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_CONFIG_DIR", "PI_SESSION_FILE")}
        e.update({"FAKE_STATE": self.dir, "PASEO_CLI": self.cli, "PASEO_AGENT_ID": ME,
                  "PASEO_AGENT_CWD": "/work", **env})
        e = {k: v for k, v in e.items() if v is not None}
        return subprocess.run([sys.executable, SCRIPT, *args], env=e, capture_output=True, text=True, timeout=30)

    def calls(self, cmd):
        p = Path(self.dir) / "calls.jsonl"
        rows = [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []
        return [r for r in rows if r[0] == cmd]

    def spawn(self, *extra, **env):
        return self.run_script(["spawn", "--prompt-file", self.prompt, *extra], **env)

    def test_spawn_inherits_settings_labels_and_detaches(self):
        r = self.spawn("--title", "PKI 이어서")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "agent-new"), r.stderr)
        run = self.calls("run")[0]
        self.assertEqual(run[-1], "이어서 진행해")
        for opt, val in (("--provider", "claude/m-1"), ("--mode", "auto"), ("--thinking", "medium"),
                         ("--cwd", "/work"), ("--label", f"handoff-from={ME}"), ("--title", "PKI 이어서")):
            self.assertEqual(run[run.index(opt) + 1], val)
        self.assertIn("--no-wait", run)
        self.assertEqual(self.calls("agent"), [["agent", "detach", "agent-new"]])
        self.assertEqual(self.calls("ls"), [["ls", "-a", "-g", "--label", f"handoff-from={ME}", "--json"]])

    def test_spawn_decodes_cli_output_as_utf8_under_non_utf8_locale(self):
        # Windows Korean locale decodes child output as cp949 unless told otherwise.
        r = self.spawn(FAKE_UTF8="1", LC_ALL="ko_KR.CP949", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0",
                       PYTHONIOENCODING=None)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "agent-new"), r.stderr)

    def test_refuses_outside_paseo(self):
        for missing in ("PASEO_CLI", "PASEO_AGENT_ID"):
            with self.subTest(missing=missing):
                self.assertEqual(self.spawn(**{missing: None}).returncode, 69)
        self.assertEqual(self.calls("run"), [])

    def test_refuses_second_successor(self):
        (Path(self.dir) / "successors.json").write_text(json.dumps([{"id": "agent-old"}]))
        r = self.spawn()
        self.assertEqual(r.returncode, 73)
        self.assertIn("agent-old", r.stderr)
        self.assertEqual(self.calls("run"), [])

    def test_running_agents_do_not_limit_the_successor(self):
        (Path(self.dir) / "ls.json").write_text(json.dumps([{"id": f"p{n}", "status": "running"} for n in range(50)]))
        r = self.spawn()
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "agent-new"), r.stderr)

    def test_cli_failure_opens_nothing_and_detach_failure_still_reports_id(self):
        for cmd in ("ls", "inspect"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.spawn(FAKE_FAIL=cmd).returncode, 71)
        self.assertEqual(self.spawn(FAKE_BAD_LS="1").returncode, 71)
        self.assertEqual(self.calls("run"), [])
        self.assertEqual(self.spawn(FAKE_FAIL="run").returncode, 70)
        r = self.spawn(FAKE_FAIL="detach")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "agent-new"))
        self.assertIn("not detached", r.stderr)

    def test_unreadable_open_result_reports_what_is_listed(self):
        r = self.spawn(FAKE_RUN_GARBAGE="none")
        self.assertEqual(r.returncode, 70)
        self.assertIn("no successor is listed", r.stderr)
        r = self.spawn(FAKE_RUN_GARBAGE="created")
        self.assertEqual(r.returncode, 70)
        self.assertIn("successor agent-new is listed and detached", r.stderr)
        self.assertEqual(self.calls("agent"), [["agent", "detach", "agent-new"]])
        self.assertNotIn("no successor opened", r.stderr)

    def test_usage_errors(self):
        Path(self.prompt).write_text("  \n")
        self.assertEqual(self.spawn().returncode, 64)
        Path(self.prompt).write_text("--mode bypass")
        self.assertEqual(self.spawn().returncode, 64)
        Path(self.prompt).write_text("ok")
        for args in ([], ["spawn"], ["spawn", "--prompt-file", "/nonexistent-x"], ["spawn", "--prompt-file"],
                     ["spawn", "--prompt-file", self.prompt, "--max-running", "5"],
                     ["spawn", "--prompt-file", self.prompt, "--bogus", "1"], ["context", "x"]):
            with self.subTest(args=args):
                self.assertEqual(self.run_script(args).returncode, 64)
        self.assertEqual(self.calls("run"), [])

    def write_transcript(self, rows):
        d = Path(self.dir) / "claude" / "projects" / "-some-project"
        d.mkdir(parents=True)
        (d / "sess-1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        return {"CLAUDE_CONFIG_DIR": str(Path(self.dir) / "claude"), "CLAUDE_CODE_SESSION_ID": "sess-1"}

    def test_context_reads_latest_main_thread_usage(self):
        usage = lambda a, b, c: {"message": {"usage": {
            "input_tokens": a, "cache_read_input_tokens": b, "cache_creation_input_tokens": c, "output_tokens": 999}}}
        env = self.write_transcript([usage(1, 1, 1), {"type": "user", "message": {"content": "hi"}},
                                     usage(2, 100000, 500), {**usage(9, 9, 9), "isSidechain": True},
                                     usage(0, 0, 0)])
        r = self.run_script(["context"], **env)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "100502"))

    def test_context_unknown_without_transcript(self):
        for env in ({}, {"CLAUDE_CODE_SESSION_ID": "absent", "CLAUDE_CONFIG_DIR": self.dir}):
            with self.subTest(env=env):
                r = self.run_script(["context"], **env)
                self.assertEqual((r.returncode, r.stdout.strip()), (3, "unknown"))

    def write_pi_session(self, rows):
        # Pi 1.6.0 session JSONL (docs/session-format.md, message-types.md Usage).
        p = Path(self.dir) / "pi-session.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        return str(p)

    def test_context_reads_latest_pi_assistant_usage(self):
        def assistant(i, r, w):
            return {"type": "message", "message": {"role": "assistant", "usage": {
                "input": i, "output": 999, "cacheRead": r, "cacheWrite": w, "totalTokens": 1}}}
        path = self.write_pi_session([
            {"type": "session", "version": 3, "id": "s"},
            assistant(1, 1, 1),
            assistant(3, 150000, 700),
            # Tool results may carry usage too (Pi message-types.md); only assistant requests count.
            {"type": "message", "message": {"role": "toolResult", "content": [],
                                            "usage": {"input": 900000, "cacheRead": 0, "cacheWrite": 0}}},
            {"type": "usage", "usage": {"input": 9, "cacheRead": 9, "cacheWrite": 9}},
            assistant(0, 0, 0),
        ])
        r = self.run_script(["context"], PI_SESSION_FILE=path)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "150703"))

    def test_most_recently_written_session_record_wins(self):
        # A `claude -p` child of Pi inherits PI_SESSION_FILE; the record the running
        # session writes is the newer one, whichever CLI it is.
        env = self.write_transcript([{"message": {"usage": {"input_tokens": 5}}}])
        claude = next((Path(self.dir) / "claude" / "projects").glob("*/sess-1.jsonl"))
        path = self.write_pi_session([{"type": "message", "message": {
            "role": "assistant", "usage": {"input": 7, "cacheRead": 0, "cacheWrite": 0}}}])
        for newer, older, expected in ((path, claude, "7"), (claude, path, "5")):
            with self.subTest(expected=expected):
                os.utime(older, (1_000_000, 1_000_000))
                os.utime(newer, (2_000_000, 2_000_000))
                r = self.run_script(["context"], PI_SESSION_FILE=path, **env)
                self.assertEqual(r.stdout.strip(), expected)

    def test_context_unknown_for_unreadable_or_empty_pi_session(self):
        empty = self.write_pi_session([{"type": "session", "version": 3}])
        for path in (empty, str(Path(self.dir) / "missing.jsonl")):
            with self.subTest(path=path):
                r = self.run_script(["context"], PI_SESSION_FILE=path)
                self.assertEqual((r.returncode, r.stdout.strip()), (3, "unknown"))


if __name__ == "__main__":
    unittest.main()
