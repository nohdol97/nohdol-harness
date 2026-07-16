#!/usr/bin/env python3
"""tdd-gate — 루트 AGENTS.md 13절 TDD의 실행 계층 게이트 (git commit-msg 훅).

전역 core.hooksPath(`.agents/githooks/`) 경유로 실행되어, Claude Code·Codex·수동
커밋 등 **도구와 무관하게** 코드 파일이 테스트 변경 없이 커밋되는 것을 차단한다.
진입: `tdd-gate.py --commit-msg <메시지 파일>` (`.agents/githooks/commit-msg` shim).
등록은 머신별 설정이라 harness-install 1단계가 수행하고, 미등록은 harness-review
주간 무결성 점검이 잡는다(ADR 015).

규칙의 원본은 문서(13절)이고 이 훅은 보조 게이트다. 따라서 판단이 불가능한
상황은 전부 통과시킨다(fail-open) — 훅이 정상 커밋까지 막으면 우회를
학습시켜 게이트 자체가 죽기 때문이다.

스펙: docs/specs/2026-07-13-tdd-gate-hook.md / 결정: docs/adr/008, 014, 015
회귀 테스트: .agents/githooks/tdd-gate_test.py (수정 시 반드시 통과)
"""
import os
import re
import subprocess
import sys

# stdio UTF-8 재구성의 단일 원본은 세션 훅 디렉토리의 `_common.py`다(스펙
# 2026-07-15-hooks-common-bootstrap) — git 훅은 임의 저장소 cwd에서 실행되므로
# 이 파일 위치 기준으로 경로를 잡는다. 유실 시 no-op 폴백(fail-open).
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "hooks")
)
try:
    from _common import utf8_stdio
except Exception:
    def utf8_stdio():
        pass

# 앱 코드 확장자 중심. .sh/.sql/.tf 등 스크립트·마이그레이션·IaC는 의도적 제외
# (테스트 관행이 낮아 게이트 마찰 > 가치 — R5, ADR 008).
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


def git(args, cwd):
    # 비ASCII 파일명 방어 2중(C15): ① core.quotepath=false — 기본값(true)은 한글
    # 경로를 8진수 이스케이프(`"\355..."`)로 감싸 확장자 판정(.py → .py")을 깨뜨려
    # 어떤 로케일에서든 게이트가 통과된다. ② encoding 명시 — 미지정 text=True는
    # 로케일 기본 인코딩(한글 Windows cp949, C 로케일 ASCII)으로 디코딩해 원문
    # UTF-8 경로에서 UnicodeDecodeError가 나고, fail-open이 그것을 삼킨다.
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args], cwd=cwd, capture_output=True,
        timeout=15, encoding="utf-8", errors="replace",
    )


# 구분자 규약 밖의 주류 테스트 관행 — 정확 일치만 인정한다(R3). substring 판정은
# latest/backtest 오분류를 다시 연다(contest.py는 여전히 코드).
TEST_BASENAMES = {"tests.py", "conftest.py"}


def is_test_file(path):
    """테스트 판정(R3): 테스트 디렉토리 세그먼트, 구분자 있는 파일명 규약,
    또는 정확 파일명 allowlist(Django tests.py·pytest conftest.py)만.
    구분자 없는 포함 문자열(latest, backtest)은 테스트로 취급하지 않는다."""
    parts = [p.lower() for p in path.split("/")[:-1]]
    if any(p in TEST_DIRS for p in parts):
        return True
    base = os.path.basename(path).lower()
    if base in TEST_BASENAMES:
        return True
    stem = base.split(".")[0]
    return bool(
        re.match(r"^(test|spec)_", stem)
        or re.search(r"_(test|tests|spec)$", stem)
        or re.search(r"\.(test|spec)\.", base)
    )


def exempt_repo(repo_dir):
    """13절 적용 제외 저장소(R2) — 루트 하네스 자신과 dev/ 실험 공간."""
    harness_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    )
    if repo_dir == harness_root:
        return True
    return repo_dir.startswith(os.path.join(harness_root, "dev") + os.sep)


# 의도적 차단 전용 exit 코드(R4). 인터프리터가 자체 실패에 쓰는 코드와 겹치면
# 안 된다 — 스크립트 손상(SyntaxError)은 rc 1, 파일 열기 실패는 rc 2라, 그 값을
# 차단으로 쓰면 shim이 게이트 오류를 차단으로 오인해 머신 전역 커밋이 막힌다.
BLOCK_EXIT = 65


def judge(files):
    """판정(R1): 코드 변경에 테스트 변경이 없으면 차단(exit 65)."""
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
    return BLOCK_EXIT


# git이 통합 커밋(merge)·재적용(cherry-pick/revert/rebase) 상태에서 남기는 마커 —
# 이미 게이트를 통과한 커밋의 재조합이므로 재검사하지 않는다(R2).
SEQUENCER_MARKERS = (
    "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply",
)


def git_hook_main(msg_path):
    """git commit-msg 훅 진입점(R1) — cwd는 git이 워크트리 루트로 맞춰준다.

    커밋 대상은 `diff --cached`만 본다: `git commit -a`도 훅 시점에는 git이
    임시 인덱스(GIT_INDEX_FILE 상속)에 스테이징을 끝낸 상태라 명령 파싱이 필요 없다.
    """
    utf8_stdio()
    with open(msg_path, encoding="utf-8", errors="replace") as f:
        if "[no-test]" in f.read():
            return 0

    cwd = os.getcwd()
    repo = git(["rev-parse", "--show-toplevel"], cwd)
    if repo.returncode != 0:
        return 0
    repo_dir = os.path.realpath(repo.stdout.strip())
    if exempt_repo(repo_dir):
        return 0
    if git(["rev-parse", "HEAD"], repo_dir).returncode != 0:
        return 0  # 최초 커밋

    gitdir = git(["rev-parse", "--git-dir"], repo_dir)
    if gitdir.returncode == 0:
        gd = gitdir.stdout.strip()
        if not os.path.isabs(gd):
            gd = os.path.join(repo_dir, gd)
        if any(os.path.exists(os.path.join(gd, m)) for m in SEQUENCER_MARKERS):
            return 0

    r = git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], repo_dir)
    return judge(r.stdout.splitlines() if r.returncode == 0 else [])


if __name__ == "__main__":
    try:
        if len(sys.argv) >= 3 and sys.argv[1] == "--commit-msg":
            sys.exit(git_hook_main(sys.argv[2]))
        sys.exit(0)  # 알 수 없는 진입(구버전 PreToolUse 등록 등) — fail-open
    except Exception:
        sys.exit(0)  # fail-open — 훅 오류가 커밋을 막으면 안 된다 (R4, ADR 008)
