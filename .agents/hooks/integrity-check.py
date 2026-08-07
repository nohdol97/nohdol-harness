#!/usr/bin/env python3
"""integrity-check — 하네스 구조 무결성의 결정론적 점검 (리포트 전용, 커밋 게이트 아님).

harness-review 주간 무결성 점검의 기계 판정 항목을 이 스크립트 1개로 결정론화한다
(루트 AGENTS.md 8절 승격 원칙 — tdd-gate·secret-gate 계보). 검사: 심링크(R1)·
`.claude/` 실파일 침입(R2)·스킬/에이전트 frontmatter(R3·R4)·MOC 정합(R5)·CLAUDE.md
첫 줄(R6)·gitignore 필수 항목(R7)·Codex agent 어댑터 정합(R12)·AGENTS.md 32KB
안전 예산(R14)·항상-온 문서의 ADR 참조 실재(R15)·한글 뷰 드리프트(R16·R17,
ADR 030)·Codex 프로젝트 설정 계약(R18)·상시 노출 토큰 예산(R19)·경량 목록 상태(R20).
심링크 불가 설치처는 R1·R2를 SKIP한다(R11).

실행: python3 .agents/hooks/integrity-check.py [--root <경로>]
      (미지정 시 CLAUDE_PROJECT_DIR → 스크립트 위치 기준 루트 순으로 해석)
종료: 문제 0건 exit 0, 1건 이상 exit 1. 출력 라벨은 영어(소비자=harness-review).

스펙: docs/specs/2026-07-19-integrity-check-script.md
회귀 테스트: .agents/hooks/integrity-check_test.py (수정 시 반드시 통과)
"""
import argparse
import ast
import hashlib
import json
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
    from _common import read_lightweight_models, utf8_stdio
except Exception:
    def utf8_stdio():
        pass

    def read_lightweight_models(base):
        return set()  # 판독기 유실 — R20은 SKIP으로 떨어진다

CLAUDE_ALLOWLIST = {"settings.json", "settings.local.json", "agents", "skills"}
GITIGNORE_REQUIRED = ["_workspace/", "project/", "REGISTRY.md",
                      ".agents/projects/*", "!.agents/projects/README.md",
                      ".codex/*", "!.codex/agents/", ".codex/agents/*",
                      "!.codex/agents/*.toml"]
EXPECTED_LINKS = {".claude/agents": "../.agents/agents",
                  ".claude/skills": "../.agents/skills"}
# CLI 로더 하드캡 — 초과하면 스킬이 통째로 로드되지 않는다(2026-07-20 Codex 실장애: wrapup 1041자).
# 권장값은 800자(metaskill 공통 규칙 2)지만, 권장 초과는 노이즈라 하드캡만 FAIL로 잡는다.
DESC_HARDCAP = 1024
SKILL_CATALOG_BUDGET = 9_000
CLAUDE_MD_BUDGET = 5_500
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
        # Windows os.readlink()는 백슬래시 표기('..\\.agents\\agents')로 반환한다 —
        # 표기 형식 차이는 무결성 문제가 아니므로 양쪽을 '/'로 정규화해 비교한다
        # (2026-07-21 주간 점검 실측: 정상 심링크 R1 FAIL 오판정).
        elif os.readlink(path).replace("\\", "/") != target.replace("\\", "/"):
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
            desc = (_frontmatter_values(skill_md) or {}).get("description", "")
            if len(desc) > DESC_HARDCAP:
                out.append(("R13 skill %s" % name, FAIL,
                            "description %d chars exceeds %d hardcap — CLI loader rejects the skill"
                            % (len(desc), DESC_HARDCAP)))
            else:
                out.append(("R3 skill %s" % name, PASS, ""))
    return out or [("R3 skills", SKIP, "no SKILL.md found")]


def check_always_on_budget(root):
    """R19: 자동 노출되는 스킬 description 합계와 CLAUDE.md 바이트 예산."""
    out = []
    base = os.path.join(root, ".agents", "skills")
    total = 0
    if os.path.isdir(base):
        for name in sorted(os.listdir(base)):
            skill_md = os.path.join(base, name, "SKILL.md")
            if not os.path.isfile(skill_md):
                continue
            desc = (_frontmatter_values(skill_md) or {}).get("description", "")
            total += len(desc.encode("utf-8"))
    if total > SKILL_CATALOG_BUDGET:
        out.append(("R19 skill description catalog", FAIL,
                    "%d bytes exceeds %d always-on catalog budget"
                    % (total, SKILL_CATALOG_BUDGET)))

    claude = os.path.join(root, "CLAUDE.md")
    if os.path.isfile(claude):
        size = os.path.getsize(claude)
        if size > CLAUDE_MD_BUDGET:
            out.append(("R19 CLAUDE.md budget", FAIL,
                        "%d bytes exceeds %d Claude-only anchor budget"
                        % (size, CLAUDE_MD_BUDGET)))
    if not out:
        out.append(("R19 always-on budget", PASS, ""))
    return out


def check_agent_frontmatter(root):
    base = os.path.join(root, ".agents", "agents")
    if not os.path.isdir(base):
        return [("R4 agents", FAIL, ".agents/agents directory missing (harness damage)")]
    out = []
    required = {"name", "description", "tools", "tier"}
    for fn in sorted(os.listdir(base)):
        # README.ko.md는 생성된 한글 뷰(ADR 030) — 에이전트 정의가 아니므로 R4 대상 제외(정합은 R17)
        if not fn.endswith(".md") or fn in ("README.md", "README.ko.md"):
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
                 if fn.endswith(".md") and fn not in ("README.md", "README.ko.md")}
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


AGENTS_BUDGET = 32_000  # Codex 기본 project_doc_max_bytes 32,768 대비 안전 여유


def check_agents_budget(root):
    """R14: AGENTS.md 32KB 안전 예산 — Codex 기본 절단점 전에 비대화를 잡는다."""
    path = os.path.join(root, "AGENTS.md")
    if not os.path.isfile(path):
        return [("R14 AGENTS.md budget", FAIL, "AGENTS.md missing")]
    size = os.path.getsize(path)
    if size > AGENTS_BUDGET:
        return [("R14 AGENTS.md budget", FAIL,
                 "%d bytes exceeds %d safety budget below Codex default 32768 — trim before commit"
                 % (size, AGENTS_BUDGET))]
    return [("R14 AGENTS.md budget", PASS, "")]


CODEX_DOC_MAX = 65_536
CODEX_HOOK_EVENTS = {"SessionStart", "PreToolUse", "PostToolUse"}
CODEX_HOOK_MATCHERS = {
    "SessionStart": {"startup", "resume", "clear"},
    # 발행 게이트 2종은 `Agent` 매처에 걸린다. 이 항목이 없던 동안 두 등록을
    # 통째로 지워도 R18이 PASS였다(독립 검증 2026-08-03 F6 — ADR 037 때 생겨
    # ADR 038로 둘이 됐다). `spawn_agent`는 Codex 도구명 미실측이라 넣지 않는다.
    "PreToolUse": {"apply_patch", "Agent"},
    "PostToolUse": {"Bash", "shell", "local_shell"},
}
# Claude 쪽 필수 등록(R21). Codex 목록과 일부러 따로 둔다 — 두 런타임의
# 이벤트·매처 규약이 다르고, 한쪽을 다른 쪽에서 유도하면 어느 한쪽이 바뀔 때
# 검사가 조용히 헐거워진다.
CLAUDE_HOOK_COMMANDS = {
    "SessionStart": ["agentsview-daemon.py", "harness-review-reminder.py",
                     "worklog-reminder.py"],
    "PreToolUse": ["gate-reminder.py", "tier-gate.py", "dispatch-gate.py"],
    "PostToolUse": ["gate-reminder.py"],
}

CODEX_HOOK_COMMANDS = {
    "SessionStart": [
        ("agentsview-daemon.py",),
        ("harness-review-reminder.py",),
        ("worklog-reminder.py",),
    ],
    "PreToolUse": [
        ("gate-reminder.py", "--check"),
        ("tier-gate.py",),
        ("dispatch-gate.py",),
    ],
    "PostToolUse": [("gate-reminder.py", "--record")],
}


def check_codex_config(root):
    """R18: 정식 hooks 키·64KiB 보조 한도·실측된 inline hook 등록을 검사한다."""
    config_path = os.path.join(root, ".codex", "config.toml")
    legacy_path = os.path.join(root, ".codex", "hooks.json")
    if os.path.isfile(legacy_path):
        return [("R18 Codex config", FAIL,
                 ".codex/hooks.json is a parallel source not loaded in the verified runtime — keep hooks inline in config.toml")]
    if not os.path.isfile(config_path):
        return [("R18 Codex config", FAIL, ".codex/config.toml missing")]
    if tomllib is None:
        return [("R18 Codex config", SKIP,
                 "Python < 3.11 has no tomllib — Codex validates TOML at runtime")]
    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        return [("R18 Codex config", FAIL, "invalid TOML: %s" % e)]

    out = []
    features = data.get("features") or {}
    if "codex_hooks" in features:
        out.append(("R18 Codex config", FAIL,
                    "deprecated features.codex_hooks present — use features.hooks"))
    if features.get("hooks") is not True:
        out.append(("R18 Codex config", FAIL, "features.hooks must be true"))
    if data.get("project_doc_max_bytes") != CODEX_DOC_MAX:
        out.append(("R18 Codex config", FAIL,
                    "project_doc_max_bytes must be %d defense-in-depth headroom" % CODEX_DOC_MAX))
    hooks = data.get("hooks") or {}
    missing = sorted(CODEX_HOOK_EVENTS - set(hooks))
    if missing:
        out.append(("R18 Codex config", FAIL,
                    "missing inline hook events: %s" % ", ".join(missing)))
    for event in sorted(CODEX_HOOK_EVENTS & set(hooks)):
        entries = hooks.get(event)
        if not isinstance(entries, list) or not entries:
            out.append(("R18 Codex config", FAIL,
                        "%s must have a non-empty event definition" % event))
            continue
        commands = []
        matchers = set()
        valid_handlers = True
        for entry in entries:
            if not isinstance(entry, dict):
                valid_handlers = False
                continue
            matchers.update(part for part in str(entry.get("matcher") or "").split("|") if part)
            handlers = entry.get("hooks")
            if not isinstance(handlers, list) or not handlers:
                valid_handlers = False
                continue
            for handler in handlers:
                if (not isinstance(handler, dict)
                        or handler.get("type") != "command"
                        or not isinstance(handler.get("command"), str)
                        or not handler["command"].strip()):
                    valid_handlers = False
                    continue
                commands.append(handler["command"])
        missing_matchers = CODEX_HOOK_MATCHERS[event] - matchers
        if missing_matchers:
            out.append(("R18 Codex config", FAIL,
                        "%s matcher missing: %s" % (event, ", ".join(sorted(missing_matchers)))))
        if not valid_handlers or not commands:
            out.append(("R18 Codex config", FAIL,
                        "%s must have non-empty type=command handlers" % event))
            continue
        for fragments in CODEX_HOOK_COMMANDS[event]:
            if not any(all(fragment in command for fragment in fragments) for command in commands):
                out.append(("R18 Codex config", FAIL,
                            "%s command missing contract: %s"
                            % (event, " + ".join(fragments))))
    return out or [("R18 Codex config", PASS, "")]


# R15 대상은 항상-온 문서만 — 스테일 포인터의 피해가 매 세션 곱으로 붙는 곳.
# 전 문서 스캔은 비목표(오탐 표면·유지비 대비 이득 없음 — 스펙 3절).
ADR_REF_DOCS = ("CLAUDE.md", "AGENTS.md")


def check_adr_refs(root):
    """R15: 항상-온 문서(CLAUDE.md·AGENTS.md)가 참조하는 ADR 번호의 파일 실재 검사."""
    adr_dir = os.path.join(root, "docs", "adr")
    existing = set()
    if os.path.isdir(adr_dir):
        for fn in os.listdir(adr_dir):
            m = re.match(r"^(\d{3})-.+\.md$", fn)
            if m:
                existing.add(m.group(1))
    out = []
    for rel in ADR_REF_DOCS:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue  # 파일 부재는 R6 등 별도 검사의 몫
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        refs = set()
        # "ADR 021", "ADR 019·029", "ADR 002·005·006·027" 같은 열거를 전부 편다.
        # (?!\d): "ADR 2026" 같은 4자리+ 숫자에서 앞 3자리를 오탐 추출하지 않는다(리뷰 F2).
        for m in re.finditer(r"ADR\s*((?:\d{3})(?:\s*[·,]\s*\d{3})*)(?!\d)", text):
            refs.update(re.findall(r"\d{3}", m.group(1)))
        for missing in sorted(refs - existing):
            out.append(("R15 ADR ref %s" % rel, FAIL,
                        "referenced ADR %s has no file in docs/adr/" % missing))
    return out or [("R15 ADR refs", PASS, "")]


# 한글 뷰 재생성 안내(ADR 030) — 실패 메시지가 '무엇을 할지'를 말해야 한다
SOURCE_HASH_RE = re.compile(r"source-hash: `?([0-9a-f]{12})`?")


def check_agents_kr_view(root):
    """R16: AGENTS.ko.md 한글 뷰의 source-hash ↔ 현재 AGENTS.md sha256[:12] 대조(ADR 030 ⓐ)."""
    src = os.path.join(root, "AGENTS.md")
    view = os.path.join(root, "AGENTS.ko.md")
    if not os.path.isfile(src):
        # 원본 부재는 R14의 몫 — 원본 없는 해시 대조는 불가하므로 SKIP(repo-shape 안전)
        return [("R16 AGENTS.ko.md view", SKIP, "AGENTS.md missing — covered by R14")]
    if not os.path.isfile(view):
        return [("R16 AGENTS.ko.md view", FAIL,
                 "AGENTS.ko.md missing — Korean view is mandatory; regenerate AGENTS.ko.md in the same commit (ADR 030)")]
    with open(view, encoding="utf-8", errors="replace") as f:
        m = SOURCE_HASH_RE.search(f.read())
    if not m:
        return [("R16 AGENTS.ko.md view", FAIL,
                 "no 'source-hash: <12 hex>' banner line — regenerate AGENTS.ko.md in the same commit (ADR 030)")]
    with open(src, "rb") as f:
        expected = hashlib.sha256(f.read()).hexdigest()[:12]
    if m.group(1) != expected:
        return [("R16 AGENTS.ko.md view", FAIL,
                 "source-hash %s != AGENTS.md sha256[:12] %s — Korean view stale; regenerate AGENTS.ko.md in the same commit (ADR 030)"
                 % (m.group(1), expected))]
    return [("R16 AGENTS.ko.md view", PASS, "")]


def _heading_set(path):
    """README.ko.md의 `## <name>` 헤딩 집합을 반환한다(R17 대조용)."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return set(re.findall(r"^## (.+?)\s*$", f.read(), re.M))


def check_korean_readme_views(root):
    """R17: 한글 요약 README.ko.md의 헤딩 집합 ↔ 실제 스킬 디렉토리·에이전트 파일 집합 1:1(ADR 030 ⓑ)."""
    out = []
    targets = [
        (".agents/skills",
         lambda base: {n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n))}),
        (".agents/agents",
         lambda base: {os.path.splitext(fn)[0] for fn in os.listdir(base)
                       if fn.endswith(".md") and fn != "README.ko.md"}),
    ]
    for rel, collect in targets:
        base = os.path.join(root, rel)
        label = "R17 %s/README.ko.md" % rel
        if not os.path.isdir(base):
            out.append((label, SKIP, "%s missing — covered by R3/R4" % rel))
            continue
        view = os.path.join(base, "README.ko.md")
        if not os.path.isfile(view):
            out.append((label, FAIL,
                        "README.ko.md missing — Korean view is mandatory; regenerate it in the same commit (ADR 030)"))
            continue
        headings = _heading_set(view)
        actual = collect(base)
        ok = True
        for name in sorted(actual - headings):
            ok = False
            out.append((label, FAIL,
                        "missing '## %s' — Korean view stale; regenerate README.ko.md in the same commit (ADR 030)" % name))
        for name in sorted(headings - actual):
            ok = False
            out.append((label, FAIL,
                        "'## %s' has no source entry — Korean view stale; regenerate README.ko.md in the same commit (ADR 030)" % name))
        if ok:
            out.append((label, PASS, ""))
    return out


def check_lightweight_section(root):
    """R20: REGISTRY.md 「경량 모델」 절의 상태를 주간 점검 출력에 드러낸다(ADR 040).

    이 절은 `tier-gate`의 유일한 판정 입력인데 **gitignore 대상**이라, 지워지거나
    비어도 `git status`에 흔적이 없고 게이트는 조용히 잠든다(독립 검증 2026-08-04
    F9). `dispatch-gate`의 프로필 판독은 미상이 '발행이 돌아간다'로 떨어져 안전하지만
    이쪽 fail-open은 '금지가 안 걸린다'로 떨어진다 — 그래서 상태를 눈에 보이게 한다.

    **FAIL로 만들지 않는다.** 절을 안 채운 설치처는 결함이 아니라 설계된 상태이고
    (`harness-install`이 그 결과를 사용자에게 말한다), FAIL이면 새 설치처가 무결성
    실패로 시작한다. SKIP은 "이 설치처에서 게이트가 잠들어 있다"를 뜻한다.
    """
    try:
        names = read_lightweight_models(root)
    except Exception as exc:
        return [("R20 lightweight list", FAIL, "read failed: %s" % exc)]
    if not names:
        return [("R20 lightweight list", SKIP,
                 "REGISTRY.md has no 「경량 모델」 entries — tier-gate never fires here "
                 "(fill it via harness-install, or accept the gate is off; ADR 040)")]
    return [("R20 lightweight list", PASS, "%d entrie(s)" % len(names))]


def check_claude_hook_registrations(root):
    """R21: `.claude/settings.json`의 세션 훅 등록이 살아 있는지 검사한다(ADR 042).

    R18은 `.codex/config.toml`만 본다. 그래서 **Claude 쪽 등록을 지워도 무결성이
    바이트 단위로 동일했다** — 9개 스위트도 전부 초록이다(독립 검증 2026-08-04
    C-03 실측). ADR 037·038 때는 그 유실의 대가가 "게이트 하나가 안 걸린다"였지만,
    ADR 042 이후로는 **사내에서 발행 차단이 통째로 꺼지는 것**이다. 조용히 사라질
    수 있는 판정 장치는 무결성이 이름을 불러 줘야 한다(R18·R20과 같은 이유).

    커맨드 문자열 전체를 고정하지는 않는다 — shim은 인터프리터 탐색 형태가 바뀔
    수 있고, 여기서 잡으려는 것은 **등록의 유실**이지 표기 변화가 아니다.
    """
    path = os.path.join(root, ".claude", "settings.json")
    if not os.path.exists(path):
        return [("R21 Claude hooks", FAIL, ".claude/settings.json missing")]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [("R21 Claude hooks", FAIL, "invalid JSON: %s" % e)]
    hooks = (data or {}).get("hooks")
    if not isinstance(hooks, dict):
        return [("R21 Claude hooks", FAIL, "no 'hooks' object")]
    out = []
    for event, required in CLAUDE_HOOK_COMMANDS.items():
        blob = repr(hooks.get(event, []))
        for script in required:
            label = "R21 Claude hooks %s" % script
            if script in blob:
                out.append((label, PASS, ""))
            else:
                out.append((label, FAIL,
                            "not registered under %s in .claude/settings.json — "
                            "the hook silently stops firing (ADR 042)" % event))
    return out or [("R21 Claude hooks", PASS, "")]


CHECKS = [check_symlinks, check_claude_intrusion, check_skill_frontmatter,
          check_always_on_budget,
          check_agent_frontmatter, check_codex_agent_adapters, check_moc,
          check_claude_md, check_gitignore, check_agents_budget, check_adr_refs,
          check_agents_kr_view, check_korean_readme_views, check_codex_config,
          check_lightweight_section, check_claude_hook_registrations]


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
