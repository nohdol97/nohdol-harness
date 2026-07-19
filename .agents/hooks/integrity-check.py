#!/usr/bin/env python3
"""integrity-check — 하네스 구조 무결성의 결정론적 점검 (리포트 전용, 커밋 게이트 아님).

harness-review 주간 무결성 점검의 기계 판정 항목을 이 스크립트 1개로 결정론화한다
(루트 AGENTS.md 8절 승격 원칙 — tdd-gate·secret-gate 계보). 검사: 심링크(R1)·
`.claude/` 실파일 침입(R2)·스킬/에이전트 frontmatter(R3·R4)·MOC 정합(R5)·CLAUDE.md
첫 줄(R6)·gitignore 필수 항목(R7)·Codex agent 어댑터 정합(R12). 심링크 불가 설치처는
R1·R2를 SKIP한다(R11).

실행: python3 .agents/hooks/integrity-check.py [--root <경로>]
      (미지정 시 CLAUDE_PROJECT_DIR → 스크립트 위치 기준 루트 순으로 해석)
종료: 문제 0건 exit 0, 1건 이상 exit 1. 출력 라벨은 영어(소비자=harness-review).

스펙: docs/specs/2026-07-19-integrity-check-script.md
회귀 테스트: .agents/hooks/integrity-check_test.py (수정 시 반드시 통과)
"""
import argparse
import ast
import os
import re
import subprocess
import sys

try:
    import tomllib
except ImportError:  # Python < 3.11: 집합·참조 검사는 유지하고 TOML 구문 검사는 SKIP
    tomllib = None

HERE = os.path.dirname(os.path.realpath(__file__))

sys.path.insert(0, HERE)
try:
    from _common import utf8_stdio
except Exception:
    def utf8_stdio():
        pass

CLAUDE_ALLOWLIST = {"settings.json", "settings.local.json", "agents", "skills"}
GITIGNORE_REQUIRED = ["_workspace/", "project/", "REGISTRY.md",
                      ".agents/projects/*", "!.agents/projects/README.md",
                      ".codex/*", "!.codex/agents/", ".codex/agents/*",
                      "!.codex/agents/*.toml"]
EXPECTED_LINKS = {".claude/agents": "../.agents/agents",
                  ".claude/skills": "../.agents/skills"}
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


def resolve_root(cli_root):
    if cli_root:
        return os.path.realpath(cli_root)
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return os.path.realpath(env)
    # 스크립트 위치: <root>/.agents/hooks/ → 2단계 위가 루트
    return os.path.dirname(os.path.dirname(HERE))


def git_ignored(root, path):
    """path가 git에 의해 무시되는지(.gitignore + .git/info/exclude). repo 아니면 False."""
    try:
        p = subprocess.run(["git", "-C", root, "check-ignore", "-q", path],
                           capture_output=True, timeout=10)
        return p.returncode == 0
    except Exception:
        return False


def symlink_installation(root):
    """`.claude/agents`가 심링크면 심링크 설치처(R1·R2 적용), 아니면 SKIP 대상(R11)."""
    return os.path.islink(os.path.join(root, ".claude", "agents"))


# --- 개별 검사 (각각 (label, status, detail) 리스트 반환) ---

def check_symlinks(root):
    if not symlink_installation(root):
        return [("R1 symlinks", SKIP, "non-symlink installation — verify sync script per AGENTS.md 11")]
    out = []
    for rel, target in EXPECTED_LINKS.items():
        path = os.path.join(root, rel)
        if not os.path.islink(path):
            out.append(("R1 symlink %s" % rel, FAIL, "not a symlink"))
        elif os.readlink(path) != target:
            out.append(("R1 symlink %s" % rel, FAIL, "points to %r, expected %r" % (os.readlink(path), target)))
        elif not os.path.exists(path):
            out.append(("R1 symlink %s" % rel, FAIL, "dangling symlink — target %r does not exist" % target))
        else:
            out.append(("R1 symlink %s" % rel, PASS, ""))
    return out


def check_claude_intrusion(root):
    if not symlink_installation(root):
        return [(".claude intrusion (R2)", SKIP, "non-symlink installation")]
    claude = os.path.join(root, ".claude")
    if not os.path.isdir(claude):
        return [(".claude intrusion (R2)", FAIL, ".claude directory missing")]
    out = []
    for entry in sorted(os.listdir(claude)):
        path = os.path.join(claude, entry)
        if os.path.islink(path):
            continue
        if entry in CLAUDE_ALLOWLIST:
            continue
        if git_ignored(root, path):
            continue  # 런타임 산출물(예: scheduled_tasks.lock)은 침입 아님
        out.append((".claude intrusion", FAIL, "unexpected non-ignored real file: .claude/%s" % entry))
    if not out:
        out.append((".claude intrusion (R2)", PASS, ""))
    return out


def _frontmatter_keys(path):
    """첫 줄 `---`로 시작하는 YAML frontmatter의 키 집합과 CRLF 여부를 반환."""
    with open(path, "rb") as f:
        raw = f.read()
    has_crlf = b"\r\n" in raw
    text = raw.decode("utf-8", errors="replace")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, has_crlf  # frontmatter 없음
    keys = set()
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][\w-]*):", line)
        if m:
            keys.add(m.group(1))
    return keys, has_crlf


def _frontmatter_values(path):
    """단순 단일행 YAML frontmatter 값을 반환한다(에이전트 메타데이터 대조용)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    values = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        value = m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            try:
                value = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                pass
        values[m.group(1)] = value
    return None


def check_skill_frontmatter(root):
    base = os.path.join(root, ".agents", "skills")
    if not os.path.isdir(base):
        return [("R3 skills", FAIL, ".agents/skills directory missing (harness damage)")]
    out = []
    for name in sorted(os.listdir(base)):
        skill_md = os.path.join(base, name, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        keys, crlf = _frontmatter_keys(skill_md)
        if keys is None:
            out.append(("R3 skill %s" % name, FAIL, "no frontmatter (first line not '---')"))
        elif "description" not in keys:
            out.append(("R3 skill %s" % name, FAIL, "missing 'description' key"))
        elif crlf:
            out.append(("R3 skill %s" % name, FAIL, "CRLF line endings (must be LF)"))
        else:
            out.append(("R3 skill %s" % name, PASS, ""))
    return out or [("R3 skills", SKIP, "no SKILL.md found")]


def check_agent_frontmatter(root):
    base = os.path.join(root, ".agents", "agents")
    if not os.path.isdir(base):
        return [("R4 agents", FAIL, ".agents/agents directory missing (harness damage)")]
    out = []
    required = {"name", "description", "tools", "tier"}
    for fn in sorted(os.listdir(base)):
        if not fn.endswith(".md") or fn == "README.md":
            continue
        path = os.path.join(base, fn)
        keys, crlf = _frontmatter_keys(path)
        if keys is None:
            out.append(("R4 agent %s" % fn, FAIL, "no frontmatter"))
            continue
        missing = required - keys
        if missing:
            out.append(("R4 agent %s" % fn, FAIL, "missing keys: %s" % ", ".join(sorted(missing))))
        else:
            out.append(("R4 agent %s" % fn, PASS, ""))
    return out or [("R4 agents", SKIP, "no agent .md found")]


def check_codex_agent_adapters(root):
    """공용 Markdown 역할 계약과 Codex TOML 어댑터의 1:1·메타데이터 정합을 검사한다."""
    contract_dir = os.path.join(root, ".agents", "agents")
    adapter_dir = os.path.join(root, ".codex", "agents")
    if not os.path.isdir(contract_dir):
        return [("R12 Codex agent adapters", FAIL, ".agents/agents directory missing")]
    if not os.path.isdir(adapter_dir):
        return [("R12 Codex agent adapters", FAIL, ".codex/agents directory missing")]

    contracts = {os.path.splitext(fn)[0]: os.path.join(contract_dir, fn)
                 for fn in os.listdir(contract_dir)
                 if fn.endswith(".md") and fn != "README.md"}
    adapters = {os.path.splitext(fn)[0]: os.path.join(adapter_dir, fn)
                for fn in os.listdir(adapter_dir) if fn.endswith(".toml")}
    out = []
    for name in sorted(set(contracts) - set(adapters)):
        out.append(("R12 Codex agent adapter", FAIL, "missing adapter for contract: %s" % name))
    for name in sorted(set(adapters) - set(contracts)):
        out.append(("R12 Codex agent adapter", FAIL, "orphan adapter without contract: %s" % name))

    for name in sorted(set(contracts) & set(adapters)):
        if tomllib is None:
            out.append(("R12 Codex agent %s" % name, SKIP,
                        "Python < 3.11 — TOML parse unavailable; set/contract checks only"))
            continue
        try:
            with open(adapters[name], "rb") as f:
                adapter = tomllib.load(f)
        except Exception as e:
            out.append(("R12 Codex agent %s" % name, FAIL, "invalid TOML: %s" % e))
            continue

        metadata = _frontmatter_values(contracts[name]) or {}
        required = {"name", "description", "developer_instructions"}
        missing = required - set(adapter)
        if missing:
            out.append(("R12 Codex agent %s" % name, FAIL,
                        "missing required keys: %s" % ", ".join(sorted(missing))))
            continue
        unexpected = set(adapter) - required
        if unexpected:
            out.append(("R12 Codex agent %s" % name, FAIL,
                        "unexpected/fixed settings forbidden: %s" % ", ".join(sorted(unexpected))))
            continue
        if adapter["name"] != name or adapter["name"] != metadata.get("name"):
            out.append(("R12 Codex agent %s" % name, FAIL, "name differs from contract/filename"))
            continue
        if adapter["description"] != metadata.get("description"):
            out.append(("R12 Codex agent %s" % name, FAIL, "description differs from contract"))
            continue
        instructions = adapter["developer_instructions"]
        contract_ref = ".agents/agents/%s.md" % name
        if not isinstance(instructions, str) or contract_ref not in instructions or "in full" not in instructions:
            out.append(("R12 Codex agent %s" % name, FAIL,
                        "developer_instructions must preload contract in full: %s" % contract_ref))
            continue
        if "unavailable" not in instructions:
            out.append(("R12 Codex agent %s" % name, FAIL,
                        "developer_instructions must report an unavailable contract"))
            continue
        out.append(("R12 Codex agent %s" % name, PASS, ""))
    return out or [("R12 Codex agent adapters", SKIP, "no contracts or adapters found")]


def check_moc(root):
    """docs/{adr,specs,proposals}의 .md 파일 ↔ docs/README.md 링크의 양방향 대조."""
    docs = os.path.join(root, "docs")
    readme = os.path.join(docs, "README.md")
    if not os.path.isfile(readme):
        return [("R5 MOC", FAIL, "docs/README.md missing (index gone)")]
    with open(readme, encoding="utf-8", errors="replace") as f:
        readme_text = f.read()
    out = []
    for sub in ("adr", "specs", "proposals"):
        d = os.path.join(docs, sub)
        if not os.path.isdir(d):
            continue
        files = {fn for fn in os.listdir(d) if fn.endswith(".md") and fn != "README.md"}
        linked = set(re.findall(r"%s/([^)\s]+\.md)" % sub, readme_text))
        for orphan in sorted(files - linked):
            out.append(("R5 MOC %s" % sub, FAIL, "file not in index: %s/%s" % (sub, orphan)))
        for ghost in sorted(linked - files):
            out.append(("R5 MOC %s" % sub, FAIL, "index row has no file: %s/%s" % (sub, ghost)))
    if not out:
        out.append(("R5 MOC", PASS, ""))
    return out


def check_claude_md(root):
    path = os.path.join(root, "CLAUDE.md")
    if not os.path.isfile(path):
        return [("R6 CLAUDE.md", FAIL, "CLAUDE.md missing")]
    with open(path, encoding="utf-8", errors="replace") as f:
        first = f.readline().strip()
    if first != "@AGENTS.md":
        return [("R6 CLAUDE.md", FAIL, "first line is %r, expected '@AGENTS.md' (ADR 021)" % first)]
    return [("R6 CLAUDE.md", PASS, "")]


def check_gitignore(root):
    path = os.path.join(root, ".gitignore")
    if not os.path.isfile(path):
        return [("R7 gitignore", FAIL, ".gitignore missing")]
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = {ln.strip() for ln in f}
    out = []
    for pat in GITIGNORE_REQUIRED:
        if pat not in lines:
            out.append(("R7 gitignore", FAIL, "missing required pattern: %s" % pat))
    return out or [("R7 gitignore", PASS, "")]


CHECKS = [check_symlinks, check_claude_intrusion, check_skill_frontmatter,
          check_agent_frontmatter, check_codex_agent_adapters, check_moc,
          check_claude_md, check_gitignore]


def run(root):
    results = []
    for check in CHECKS:
        try:
            results.extend(check(root))
        except Exception as e:  # 항목 단위 격리 — 한 검사 예외가 전체를 죽이지 않는다(R9)
            results.append((check.__name__, FAIL, "check crashed: %s" % e))
    return results


def main(argv=None):
    utf8_stdio()
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    args = ap.parse_args(argv)
    root = resolve_root(args.root)

    results = run(root)
    n_pass = n_fail = n_skip = 0
    for label, status, detail in results:
        if status == PASS:
            n_pass += 1
            print("PASS %s" % label)
        elif status == SKIP:
            n_skip += 1
            print("SKIP %s: %s" % (label, detail))
        else:
            n_fail += 1
            print("FAIL %s: %s" % (label, detail))
    print("integrity: %d pass, %d fail, %d skip (root: %s)" % (n_pass, n_fail, n_skip, root))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
