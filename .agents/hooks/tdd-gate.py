#!/usr/bin/env python3
"""tdd-gate — 루트 AGENTS.md 13절 TDD의 실행 계층 게이트 (PreToolUse / Bash).

git commit 시점에 코드 파일이 테스트 변경 없이 커밋되는 것을 차단한다.
규칙의 원본은 문서(13절)이고 이 훅은 보조 게이트다. 따라서 판단이 불가능한
상황은 전부 통과시킨다(fail-open) — 훅이 정상 커밋까지 막으면 우회를
학습시켜 게이트 자체가 죽기 때문이다.

스펙: docs/specs/2026-07-13-tdd-gate-hook.md / 결정: docs/adr/008
회귀 테스트: .agents/hooks/tdd-gate_test.py (수정 시 반드시 통과)

예외(통과) — R4:
- 루트 하네스 저장소 자신 (문서 중심 — 5절 main 직커밋 예외와 동일 근거)
- dev/ 아래 저장소 (실험 공간 — 13절 적용 대상이 아님)
- 최초 커밋(HEAD 없음) — 스캐폴딩 커밋에 테스트를 요구하면 마찰만 남는다
- 커밋 메시지에 [no-test] 포함 — 동작 불변 수정, 사용자 확인 전제(13절 4항).
  커밋 메시지에 흔적이 남는 유일한 우회 경로다. 무추적 바이패스는 두지 않는다.
"""
import json
import os
import re
import subprocess
import sys

# 앱 코드 확장자 중심. .sh/.sql/.tf 등 스크립트·마이그레이션·IaC는 의도적 제외
# (테스트 관행이 낮아 게이트 마찰 > 가치 — R7, ADR 008).
CODE_EXTS = {
    ".c", ".cc", ".cpp", ".cs", ".dart", ".ex", ".exs", ".go", ".h", ".hpp",
    ".java", ".js", ".jsx", ".kt", ".kts", ".m", ".mjs", ".cjs", ".mm",
    ".php", ".py", ".rb", ".rs", ".scala", ".svelte", ".swift", ".ts",
    ".tsx", ".vue",
}
TEST_DIRS = {
    "test", "tests", "__tests__", "spec", "specs", "e2e", "testing",
    "integration_test", "androidtest", "unittest",
}
PATH_TOKEN = r"(\"[^\"]+\"|'[^']+'|[^\s;&|]+)"


def strip_quotes(s):
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def strip_quoted_segments(cmd):
    """커밋 감지·플래그 탐지 전에 따옴표 안 문자열(커밋 메시지 등)을 제거한다 —
    메시지 본문의 'git commit'·'-a' 따위가 명령·플래그로 오인되는 것을 막기 위해서다(R2)."""
    return re.sub(r"\"[^\"]*\"|'[^']*'", "", cmd)


def git(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=15
    )


def resolve_target_dir(cmd, cwd):
    """커밋이 실행될 디렉토리를 추정한다(R3): `git -C <path>`(전역 위치만) > `cd` 체인 > cwd.

    - `cd`는 등장 순서대로 누적 적용한다 (`cd a && cd ../b`).
    - git의 `-C`는 subcommand(commit) 이전의 전역 옵션 위치만 인정한다 —
      `git commit -C HEAD`의 `-C`는 커밋 메시지 재사용 플래그다.
    """
    target = cwd
    for m in re.finditer(r"(?:^|&&|;)\s*cd\s+" + PATH_TOKEN, cmd):
        p = os.path.expanduser(strip_quotes(m.group(1)))
        target = p if os.path.isabs(p) else os.path.join(target, p)
    m = re.search(
        r"\bgit\s+(?:(?!commit\b)[^\s;&|]+\s+)*-C\s+" + PATH_TOKEN, cmd
    )
    if m:
        p = os.path.expanduser(strip_quotes(m.group(1)))
        target = p if os.path.isabs(p) else os.path.join(cwd, p)
    return target


def changed_files(repo_dir, bare_cmd):
    """커밋에 포함될 파일 목록(R2). -a/--all이면 tracked 수정분도 포함된다.
    bare_cmd는 따옴표 세그먼트가 제거된 명령이어야 한다."""
    commit_part = bare_cmd[bare_cmd.find("commit"):]
    use_all = bool(re.search(r"\s--all\b|\s-[a-zA-Z]*a", commit_part))
    if use_all:
        r = git(["diff", "HEAD", "--name-only", "--diff-filter=ACMR"], repo_dir)
        if r.returncode == 0:
            return r.stdout.splitlines()
    r = git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], repo_dir)
    return r.stdout.splitlines() if r.returncode == 0 else []


def is_test_file(path):
    """테스트 판정(R5): 테스트 디렉토리 세그먼트 또는 구분자 있는 파일명 규약만.
    구분자 없는 포함 문자열(latest, backtest)은 테스트로 취급하지 않는다."""
    parts = [p.lower() for p in path.split("/")[:-1]]
    if any(p in TEST_DIRS for p in parts):
        return True
    base = os.path.basename(path).lower()
    stem = base.split(".")[0]
    return bool(
        re.match(r"^(test|spec)_", stem)
        or re.search(r"_(test|tests|spec)$", stem)
        or re.search(r"\.(test|spec)\.", base)
    )


def utf8_stdio():
    """stderr를 UTF-8(errors=replace)로 재구성한다 — 한글 Windows 콘솔의 기본
    인코딩(cp949)은 차단 안내의 em dash(U+2014)를 못 담아 write가 예외를 던지고,
    최상위 fail-open이 그것을 삼켜 차단해야 할 커밋이 통과한다(2026-07-14 장애)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main():
    utf8_stdio()
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    bare = strip_quoted_segments(cmd)
    # 서브커맨드 위치의 commit만 인정(R2) — `git log --grep=commit`처럼 인자에
    # 들어간 단어로 오탐하지 않도록, git 뒤에 전역 옵션만 허용하고 commit을 찾는다.
    if not re.search(
        r"\bgit(?:\s+(?:-[cC]\s+[^\s;&|]+|--[^\s;&|]+|-\w+))*\s+commit\b", bare
    ):
        return 0
    if "[no-test]" in cmd:  # 마커는 따옴표(커밋 메시지) 안에 있으므로 원문에서 찾는다
        return 0

    cwd = data.get("cwd") or os.getcwd()
    repo = git(["rev-parse", "--show-toplevel"], resolve_target_dir(cmd, cwd))
    if repo.returncode != 0:
        return 0  # 저장소 아님 — git 자신이 실패하게 둔다
    repo_dir = os.path.realpath(repo.stdout.strip())

    harness_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    )
    if repo_dir == harness_root:
        return 0
    if repo_dir.startswith(os.path.join(harness_root, "dev") + os.sep):
        return 0
    if git(["rev-parse", "HEAD"], repo_dir).returncode != 0:
        return 0  # 최초 커밋

    files = changed_files(repo_dir, bare)
    code = [f for f in files
            if os.path.splitext(f)[1].lower() in CODE_EXTS and not is_test_file(f)]
    tests = [f for f in files
             if os.path.splitext(f)[1].lower() in CODE_EXTS and is_test_file(f)]
    if not code or tests:
        return 0

    shown = ", ".join(code[:10]) + (" 외 %d개" % (len(code) - 10) if len(code) > 10 else "")
    sys.stderr.write(
        "[tdd-gate] 커밋 차단 — 코드 변경에 테스트 변경이 없습니다 (루트 AGENTS.md 13절 TDD).\n"
        "코드 파일: %s\n"
        "조치 중 하나를 선택하세요:\n"
        "  1) 스펙의 완료 기준을 실패 테스트로 먼저 작성하고 테스트를 함께 커밋한다 (원칙).\n"
        "  2) 동작이 변하지 않는 수정(주석·포맷·상수 조정 등)이면, 사용자에게 확인받은 뒤\n"
        "     커밋 메시지에 [no-test] 를 포함해 다시 커밋한다.\n" % shown
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail-open — 훅 오류가 커밋을 막으면 안 된다 (R6, ADR 008)
