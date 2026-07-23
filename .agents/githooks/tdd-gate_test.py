#!/usr/bin/env python3
"""tdd-gate 회귀 테스트 — 스펙 docs/specs/2026-07-13-tdd-gate-hook.md 완료 기준(C1~C16).

실행: python3 .agents/githooks/tdd-gate_test.py   (훅 수정 시 반드시 통과 — R7)
부수 효과: 임시 디렉토리만 사용하며 전부 정리한다.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
HOOK = os.path.join(HERE, "tdd-gate.py")
HARNESS_ROOT = os.path.dirname(os.path.dirname(HERE))
GITHOOKS = HERE

# 스위트 자신의 한글 PASS/FAIL 출력도 로케일 비의존이어야 한다(C 로케일에서
# print가 UnicodeEncodeError로 죽으면 검증 자체가 불가) — 단일 원본을 공유한다.
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
try:
    from _common import utf8_stdio
except Exception:
    def utf8_stdio():
        pass

results = []

# 사내 Windows 머신에서 보안 에이전트(AV/EDR)가 프로세스 생성마다 지연을 더해
# 30초를 초과한 실측(2026-07-23 큐 보고) — 느린 머신은 환경변수로 상향한다.
TIMEOUT = int(os.environ.get("TDD_GATE_TEST_TIMEOUT", "30"))


class _TimeoutRC:
    """어느 기대값과도 일치하지 않는 rc — ==·!= 모두 False라서 양성형(== 65)·
    부정형(!= 0) 판정이 전부 FAIL로 남는다(타임아웃의 거짓 PASS 방지)."""
    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return False

    def __repr__(self):
        return "timeout(%ds)" % TIMEOUT


class _Timeout:
    """TimeoutExpired 대체 결과 — 스위트를 죽이지 않고 해당 케이스만 FAIL로 남긴다.
    크래시는 이후 케이스의 PASS/FAIL 집계 전부를 잃는다(2026-07-23 큐 보고 ①)."""
    returncode = _TimeoutRC()
    stderr = ""


def run(cmd, timeout=None, **kw):
    """공통 subprocess 실행 — 타임아웃을 잡아 _Timeout으로 치환한다.
    encoding 명시 — 자식(훅)의 한글 안내는 UTF-8 바이트인데, 미지정 text=True는
    로케일 기본 인코딩(cp949 등)으로 디코딩해 리더 스레드가 죽고 stderr가 None이
    된다(2026-07-15 큐 보고 — 한글 Windows에서 스위트가 C1 이후 진행 불가)."""
    try:
        return subprocess.run(cmd, capture_output=True,
                              timeout=TIMEOUT if timeout is None else timeout,
                              encoding="utf-8", errors="replace", **kw)
    except subprocess.TimeoutExpired:
        return _Timeout()


def run_git_hook(repo, message, msg_path=None, env=None):
    """git commit-msg 모드 실행 — cwd를 저장소 루트로 두고 메시지 파일 경로를 넘긴다."""
    made = None
    if msg_path is None:
        fd, made = tempfile.mkstemp(prefix="tdd-gate-msg-")
        with os.fdopen(fd, "w") as f:
            f.write(message)
        msg_path = made
    try:
        p = run([sys.executable, HOOK, "--commit-msg", msg_path],
                cwd=repo, env={**os.environ, **env} if env else None)
        return p.returncode, p.stderr
    finally:
        if made:
            os.remove(made)


def git_with_hooks(repo, *args):
    """전역 core.hooksPath 등록을 흉내 내 .agents/githooks/ 경유로 git을 실행한다."""
    return run(["git", "-c", "core.hooksPath=%s" % GITHOOKS, *args], cwd=repo)


def sh(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_repo(path, initial_commit=True):
    os.makedirs(path, exist_ok=True)
    sh(path, "init", "-q")
    sh(path, "config", "user.email", "tdd-gate-test@local")
    sh(path, "config", "user.name", "tdd-gate-test")
    if initial_commit:
        sh(path, "commit", "-q", "--allow-empty", "-m", "init")
    return path


def put(repo, rel, content="x = 1\n"):
    p = os.path.join(repo, rel)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(p, "w") as f:
        f.write(content)
    return rel


def check(cid, desc, got, want):
    ok = got == want
    results.append(ok)
    print(("PASS" if ok else "FAIL") + " %s: %s (exit=%s, want=%s)" % (cid, desc, got, want))


def main():
    utf8_stdio()
    tmp = tempfile.mkdtemp(prefix="tdd-gate-test-")
    try:
        # C1: 코드만 스테이징 → 차단(전용 코드 65 — 인터프리터 rc 1/2와 구분, R4)
        g1 = make_repo(os.path.join(tmp, "g1"))
        put(g1, "app.py"); sh(g1, "add", "app.py")
        code1, err1 = run_git_hook(g1, "feat: x")
        check("C1", "코드만 스테이징 → 차단", code1, 65)
        check("C1-msg", "stderr에 차단 안내 포함", "커밋 차단" in err1, True)

        # C2: 코드+테스트 → 통과 (git commit -a 경로는 C11 shim 통합이 실커밋으로 검증)
        put(g1, "test_app.py", "def test_x(): pass\n"); sh(g1, "add", "test_app.py")
        check("C2", "코드+테스트 동시 스테이징 → 통과", run_git_hook(g1, "feat: x")[0], 0)

        # C4: 메시지 파일의 [no-test] → 통과
        sh(g1, "reset", "-q", "test_app.py"); os.remove(os.path.join(g1, "test_app.py"))
        check("C4", "[no-test] 마커 → 통과", run_git_hook(g1, "chore: fmt [no-test]")[0], 0)

        # C5: merge·cherry-pick 진행 상태 → 통과 (pull 머지 커밋 거짓 차단 방지)
        for cid, marker, msg in (
            ("C5a", "MERGE_HEAD", "Merge branch 'x'"),
            ("C5b", "CHERRY_PICK_HEAD", "feat: picked"),
        ):
            mpath = os.path.join(g1, ".git", marker)
            with open(mpath, "w") as f:
                f.write("0" * 40 + "\n")
            check(cid, "%s 상태 → 통과" % marker, run_git_hook(g1, msg)[0], 0)
            os.remove(mpath)

        # C3: 문서만 스테이징 → 통과
        g3 = make_repo(os.path.join(tmp, "g3"))
        put(g3, "note.md", "hi\n"); sh(g3, "add", "note.md")
        check("C3", "문서만 스테이징 → 통과", run_git_hook(g3, "docs: note")[0], 0)

        # C6: 루트 하네스 저장소 → 통과 (dev/ 예외는 2026-07-19 제거 — ADR 024)
        check("C6a", "루트 하네스 저장소 → 통과",
              run_git_hook(HARNESS_ROOT, "chore(harness): x")[0], 0)

        # C7: 최초 커밋(HEAD 없음) → 통과
        g7 = make_repo(os.path.join(tmp, "g7"), initial_commit=False)
        put(g7, "app.py"); sh(g7, "add", "app.py")
        check("C7", "최초 커밋 → 통과", run_git_hook(g7, "init")[0], 0)

        # C8: 메시지 파일 없음 → fail-open 통과
        check("C8", "메시지 파일 없음 → 통과",
              run_git_hook(g1, None, msg_path=os.path.join(tmp, "no-such-msg"))[0], 0)

        # C9: 테스트 판정 — tests/ 디렉토리 인정, 구분자 없는 파일명(latest.py) 오분류 금지
        g9 = make_repo(os.path.join(tmp, "g9"))
        put(g9, "app.py"); put(g9, "tests/y_check.py", "def test_y(): pass\n")
        sh(g9, "add", "-A")
        check("C9a", "tests/ 하위 파일 인정 → 통과", run_git_hook(g9, "feat: y")[0], 0)
        g9b = make_repo(os.path.join(tmp, "g9b"))
        put(g9b, "latest.py"); sh(g9b, "add", "latest.py")
        check("C9b", "latest.py 단독 → 차단", run_git_hook(g9b, "feat: latest")[0], 65)

        # C9c: 정확 파일명 allowlist — Django `tests.py`·pytest `conftest.py`는
        # 테스트로 인정(구분자 규약 밖의 주류 관행 — false block이 [no-test] 남용을
        # 학습시킨다). 유사 이름(contest.py)은 여전히 코드다(allowlist는 정확 일치만).
        g9c = make_repo(os.path.join(tmp, "g9c"))
        put(g9c, "app/models.py"); put(g9c, "app/tests.py", "def test_m(): pass\n")
        sh(g9c, "add", "-A")
        check("C9c", "app/models.py + app/tests.py → 통과", run_git_hook(g9c, "feat: dj")[0], 0)
        g9d = make_repo(os.path.join(tmp, "g9d"))
        put(g9d, "util.py"); put(g9d, "conftest.py", "import pytest\n")
        sh(g9d, "add", "-A")
        check("C9d", "util.py + conftest.py → 통과", run_git_hook(g9d, "feat: cf")[0], 0)
        g9e = make_repo(os.path.join(tmp, "g9e"))
        put(g9e, "contest.py"); sh(g9e, "add", "contest.py")
        check("C9e", "contest.py 단독 → 차단(allowlist 정확 일치만)",
              run_git_hook(g9e, "feat: c")[0], 65)

        # C10: cp949 stdio(한글 Windows 콘솔) → 차단 메시지의 em dash가 인코딩
        # 예외를 던지면 fail-open이 차단을 삼켜 게이트가 무력화된다(2026-07-14 장애)
        g10 = make_repo(os.path.join(tmp, "g10"))
        put(g10, "app.py"); sh(g10, "add", "app.py")
        code10, err10 = run_git_hook(g10, "feat: x", env={"PYTHONIOENCODING": "cp949"})
        check("C10", "cp949 stdio에서도 차단 유지", code10, 65)
        check("C10-msg", "cp949 stdio에서도 차단 안내 출력", "커밋 차단" in err10, True)

        # C11: shim 통합 — core.hooksPath 경유 실제 git commit이 차단/통과
        g11 = make_repo(os.path.join(tmp, "g11"))
        put(g11, "app.py"); sh(g11, "add", "app.py")
        p11 = git_with_hooks(g11, "commit", "-m", "feat: x")
        check("C11", "shim 통합 — 코드만 커밋 차단", p11.returncode != 0, True)
        check("C11-msg", "shim 통합 — 차단 안내 출력", "커밋 차단" in p11.stderr, True)
        put(g11, "tests/test_app.py", "def test_x(): pass\n"); sh(g11, "add", "-A")
        check("C11b", "shim 통합 — 코드+테스트 커밋 성공",
              git_with_hooks(g11, "commit", "-q", "-m", "feat: x").returncode, 0)
        put(g11, "app.py", "x = 2\n")
        check("C11c", "shim 통합 — tracked 수정 commit -am 차단",
              git_with_hooks(g11, "commit", "-am", "fix: tweak").returncode != 0, True)

        # C12: shim 체인 — 게이트 통과 후 저장소 로컬 commit-msg 훅이 실행됨
        g12 = make_repo(os.path.join(tmp, "g12"))
        marker = os.path.join(g12, ".git", "local-hook-ran")
        local_hook = os.path.join(g12, ".git", "hooks", "commit-msg")
        with open(local_hook, "w") as f:
            f.write("#!/bin/sh\ntouch \"%s\"\n" % marker)
        os.chmod(local_hook, 0o755)
        put(g12, "note.md", "hi\n"); sh(g12, "add", "note.md")
        check("C12-commit", "체인 대상 커밋 성공",
              git_with_hooks(g12, "commit", "-q", "-m", "docs: note").returncode, 0)
        check("C12", "로컬 commit-msg 훅으로 체인됨", os.path.exists(marker), True)

        # C13: 게이트 스크립트 부재 → shim이 fail-open (하네스 이동·삭제 시
        # 머신 전역 커밋이 막히면 안 된다 — reviewer F2 회귀)
        orphan = os.path.join(tmp, "orphan-githooks")
        shutil.copytree(GITHOOKS, orphan,
                        ignore=shutil.ignore_patterns("tdd-gate*"))
        g13 = make_repo(os.path.join(tmp, "g13"))
        put(g13, "app.py"); sh(g13, "add", "app.py")
        p13 = run(
            ["git", "-c", "core.hooksPath=%s" % orphan, "commit", "-q", "-m", "feat: x"],
            cwd=g13)
        check("C13", "게이트 스크립트 부재 → 커밋 통과", p13.returncode, 0)

        # C13b: 게이트 스크립트 손상(SyntaxError → 인터프리터 rc 1) → 커밋 통과.
        # shim이 모든 비0 rc를 차단으로 전파하면 손상 시 머신 전역 커밋이 막히고,
        # 게이트 수정 커밋조차 막힌다(2026-07-16 감사 HOOK-F1 재현) — 의도적
        # 차단(65)만 차단하고 나머지는 fail-open이어야 한다(R4).
        broken = os.path.join(tmp, "broken-githooks")
        shutil.copytree(GITHOOKS, broken, ignore=shutil.ignore_patterns("__pycache__"))
        with open(os.path.join(broken, "tdd-gate.py"), "a") as f:
            f.write("\ndef broken(:\n")
        g13b = make_repo(os.path.join(tmp, "g13b"))
        put(g13b, "note.md", "hi\n"); sh(g13b, "add", "note.md")
        p13b = run(
            ["git", "-c", "core.hooksPath=%s" % broken, "commit", "-q", "-m", "docs: note"],
            cwd=g13b)
        check("C13b", "게이트 스크립트 손상 → 커밋 통과(fail-open)", p13b.returncode, 0)

        # C14: 알 수 없는 진입(구버전 PreToolUse 등록: 무인자 + stdin JSON) → fail-open
        # 혼합 상태(구 settings.json + 신 스크립트)에서 세션·커밋이 깨지면 안 된다 (ADR 015)
        p14 = run(
            [sys.executable, HOOK], cwd=g1,
            input='{"tool_name": "Bash", "tool_input": {"command": "git commit"}}',
        )
        check("C14a", "구버전 stdin 진입 → 통과", p14.returncode, 0)
        p14b = run([sys.executable, HOOK, "--commit-msg"], cwd=g1)
        check("C14b", "인자 누락 진입 → 통과", p14b.returncode, 0)

        # C15: 비UTF-8 로케일(한글 Windows cp949, C 로케일)에서 한글 파일명 → 차단 유지.
        # 훅 내부 git 출력 디코딩이 로케일 기본 인코딩에 의존하면 UnicodeDecodeError가
        # 나고, fail-open이 그것을 삼켜 차단해야 할 커밋이 통과한다(2026-07-15 큐 보고).
        g15 = make_repo(os.path.join(tmp, "g15"))
        try:
            put(g15, "한글코드.py")
        except UnicodeEncodeError:
            # 파일시스템 인코딩이 한글 파일명을 못 담는 환경(C 로케일 전체 실행
            # 시뮬레이션)에서만 발생 — 실제 대상 환경(한글 Windows·UTF-8 리눅스)
            # 에서는 생성이 되므로 케이스가 돈다. 침묵 누락 금지: SKIP을 남긴다.
            print("SKIP C15: 파일시스템이 한글 파일명 미지원(비UTF-8 fs 인코딩)")
        else:
            sh(g15, "add", "한글코드.py")
            code15, _ = run_git_hook(g15, "feat: kr", env={
                "LC_ALL": "C", "LANG": "C",
                "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"})
            check("C15", "비UTF-8 로케일 + 한글 파일명 → 차단 유지", code15, 65)

        # C16: subprocess 타임아웃 → 크래시 대신 해당 케이스만 FAIL 가능한 센티널
        # 반환(2026-07-23 큐 보고 ① — 크래시는 이후 케이스 집계 전부를 잃는다)
        p16 = run([sys.executable, "-c", "import time; time.sleep(60)"],
                  cwd=tmp, timeout=1)
        check("C16", "타임아웃 → 스위트 크래시 없이 센티널 반환",
              type(p16).__name__, "_Timeout")
        check("C16b", "센티널 rc는 어떤 기대값과도 불일치(거짓 PASS 방지)",
              p16.returncode == 0 or p16.returncode != 0, False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total, passed = len(results), sum(results)
    print("\n%d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
