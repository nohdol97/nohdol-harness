#!/usr/bin/env python3
"""tdd-gate 회귀 테스트 — 스펙 docs/specs/2026-07-13-tdd-gate-hook.md 완료 기준(C1~C23).

실행: python3 .agents/hooks/tdd-gate_test.py   (훅 수정 시 반드시 통과 — R8)
부수 효과: 임시 디렉토리와 dev/_tddgate_selftest/(예외 경로 검증용)만 사용하며 전부 정리한다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
HOOK = os.path.join(HERE, "tdd-gate.py")
HARNESS_ROOT = os.path.dirname(os.path.dirname(HERE))
GITHOOKS = os.path.join(os.path.dirname(HERE), "githooks")

results = []


def run_hook(command, cwd, raw=None, env=None):
    payload = raw if raw is not None else json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
    )
    p = subprocess.run([sys.executable, HOOK], input=payload,
                       capture_output=True, text=True, timeout=30,
                       env={**os.environ, **env} if env else None)
    return p.returncode, p.stderr


def run_git_hook(repo, message, msg_path=None):
    """git commit-msg 모드 실행 — cwd를 저장소 루트로 두고 메시지 파일 경로를 넘긴다."""
    made = None
    if msg_path is None:
        fd, made = tempfile.mkstemp(prefix="tdd-gate-msg-")
        with os.fdopen(fd, "w") as f:
            f.write(message)
        msg_path = made
    try:
        p = subprocess.run([sys.executable, HOOK, "--commit-msg", msg_path],
                           cwd=repo, capture_output=True, text=True, timeout=30)
        return p.returncode, p.stderr
    finally:
        if made:
            os.remove(made)


def git_with_hooks(repo, *args):
    """전역 core.hooksPath 등록을 흉내 내 .agents/githooks/ 경유로 git을 실행한다."""
    return subprocess.run(
        ["git", "-c", "core.hooksPath=%s" % GITHOOKS, *args],
        cwd=repo, capture_output=True, text=True, timeout=30,
    )


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
    tmp = tempfile.mkdtemp(prefix="tdd-gate-test-")
    dev_probe = os.path.join(HARNESS_ROOT, "dev", "_tddgate_selftest")
    try:
        # C1: 코드만 스테이징 → 차단
        r1 = make_repo(os.path.join(tmp, "r1"))
        put(r1, "app.py"); sh(r1, "add", "app.py")
        code, err = run_hook('git commit -m "feat: x"', r1)
        check("C1", "코드만 스테이징 → 차단", code, 2)
        check("C1-msg", "stderr에 차단 안내 포함", "커밋 차단" in err, True)

        # C2: 코드+테스트 → 통과
        put(r1, "test_app.py", "def test_x(): pass\n"); sh(r1, "add", "test_app.py")
        check("C2", "코드+테스트 동시 스테이징 → 통과", run_hook('git commit -m "feat: x"', r1)[0], 0)

        # C9d: [no-test] 마커 → 통과
        sh(r1, "reset", "-q", "test_app.py"); os.remove(os.path.join(r1, "test_app.py"))
        check("C9d", "[no-test] 마커 → 통과", run_hook('git commit -m "chore: fmt [no-test]"', r1)[0], 0)

        # C3: 문서만 → 통과
        r3 = make_repo(os.path.join(tmp, "r3"))
        put(r3, "note.md", "hi\n"); sh(r3, "add", "note.md")
        check("C3", "문서만 스테이징 → 통과", run_hook('git commit -m "docs: note"', r3)[0], 0)

        # C4: tracked 코드 수정 + -am → 차단
        r4 = make_repo(os.path.join(tmp, "r4"))
        put(r4, "app.py"); sh(r4, "add", "app.py")
        sh(r4, "commit", "-q", "-m", "feat: app [no-test]")
        put(r4, "app.py", "x = 2\n")
        check("C4", "tracked 코드 수정 + -am → 차단", run_hook('git commit -am "fix: tweak"', r4)[0], 2)

        # C5: 따옴표 안 'git commit' 텍스트 → 비커밋으로 통과 (F2 회귀)
        check("C5", "echo \"git commit\" → 통과", run_hook('echo "git commit now"', r4)[0], 0)

        # C5b: 인자 속 무따옴표 commit 단어 → 비커밋으로 통과 (F9 회귀)
        check("C5b", "git log --grep=commit → 통과", run_hook("git log --grep=commit", r4)[0], 0)

        # C6: 메시지 안 '-a' 텍스트 플래그 오인 없음 (docs만 스테이징, 코드는 미스테이징)
        put(r4, "note.md", "doc\n"); sh(r4, "add", "note.md")
        check("C6", "메시지 안 -a 텍스트 → 통과", run_hook('git commit -m "docs: explain -a flag"', r4)[0], 0)
        sh(r4, "checkout", "-q", "app.py")

        # C7: 저장소 해석 — cd 프리픽스 / 다중 cd 체인 / 공백 경로 / 서브디렉토리 cwd
        put(r4, "app.py", "x = 3\n")
        sh(r4, "add", "app.py")
        check("C7a", "cd 프리픽스 → 차단", run_hook("cd %s && git commit -m 'feat: y'" % r4, "/")[0], 2)
        sub = os.path.join(tmp, "elsewhere"); os.makedirs(sub, exist_ok=True)
        check("C7b", "다중 cd 체인 → 차단",
              run_hook("cd %s && cd ../r4 && git commit -m 'feat: y'" % sub, tmp)[0], 2)
        rsp = make_repo(os.path.join(tmp, "repo with spaces"))
        put(rsp, "app.py"); sh(rsp, "add", "app.py")
        check("C7c", "공백 경로 cd → 차단",
              run_hook('cd "%s" && git commit -m "feat: z"' % rsp, "/")[0], 2)
        subdir = os.path.join(r4, "pkg"); os.makedirs(subdir, exist_ok=True)
        check("C7d", "서브디렉토리 cwd → 차단", run_hook('git commit -m "feat: y"', subdir)[0], 2)

        # C8: git commit -C HEAD — 전역 -C가 아니므로 경로로 오인 금지 (F3 회귀)
        check("C8", "commit -C HEAD → 차단", run_hook("git commit -C HEAD", r4)[0], 2)

        # C5c: 전역 옵션 뒤 commit도 감지 → 차단 (F9 수정의 과소 감지 방지, 코드 스테이징 상태)
        check("C5c", "전역 옵션 뒤 commit 감지 → 차단",
              run_hook("git -c core.autocrlf=false commit -m 'feat: y'", r4)[0], 2)

        # C9a: 루트 하네스 저장소 → 통과
        check("C9a", "루트 하네스 저장소 → 통과",
              run_hook('git commit -m "chore(harness): x"', HARNESS_ROOT)[0], 0)

        # C9b: dev/ 저장소 → 통과
        rd = make_repo(dev_probe)
        put(rd, "z.py"); sh(rd, "add", "z.py")
        check("C9b", "dev/ 저장소 → 통과", run_hook('git commit -m "feat: z"', rd)[0], 0)

        # C9c: 최초 커밋(HEAD 없음) → 통과
        r9 = make_repo(os.path.join(tmp, "r9"), initial_commit=False)
        put(r9, "app.py"); sh(r9, "add", "app.py")
        check("C9c", "최초 커밋 → 통과", run_hook('git commit -m "init"', r9)[0], 0)

        # C10a: tests/ 디렉토리 인식 → 통과
        r10 = make_repo(os.path.join(tmp, "r10"))
        put(r10, "app.py"); put(r10, "tests/y_check.py", "def test_y(): pass\n")
        sh(r10, "add", "-A")
        check("C10a", "tests/ 하위 파일 인정 → 통과", run_hook('git commit -m "feat: y"', r10)[0], 0)

        # C10b: latest.py 오분류 금지 → 차단 (F4 회귀)
        r10b = make_repo(os.path.join(tmp, "r10b"))
        put(r10b, "latest.py"); sh(r10b, "add", "latest.py")
        check("C10b", "latest.py 단독 → 차단", run_hook('git commit -m "feat: latest"', r10b)[0], 2)

        # C11: 깨진 JSON → fail-open 통과
        check("C11", "깨진 JSON → 통과", run_hook(None, None, raw="not json")[0], 0)

        # C13: cp949 stdio(한글 Windows 콘솔) → 차단 메시지의 em dash가 인코딩
        # 예외를 던지면 fail-open이 차단을 삼켜 게이트가 무력화된다(2026-07-14 장애)
        r13 = make_repo(os.path.join(tmp, "r13"))
        put(r13, "app.py"); sh(r13, "add", "app.py")
        code13, err13 = run_hook('git commit -m "feat: x"', r13,
                                 env={"PYTHONIOENCODING": "cp949"})
        check("C13", "cp949 stdio에서도 차단 유지", code13, 2)
        check("C13-msg", "cp949 stdio에서도 차단 안내 출력", "커밋 차단" in err13, True)

        # 비커밋 git 명령 → 통과
        check("C-etc", "git status → 통과", run_hook("git status", r4)[0], 0)

        # ---- git commit-msg 훅 모드 (R9·R10, ADR 014 — 도구 무관 실행 계층) ----

        # C14: git 모드 — 코드만 스테이징 → 차단
        g1 = make_repo(os.path.join(tmp, "g1"))
        put(g1, "app.py"); sh(g1, "add", "app.py")
        code14, err14 = run_git_hook(g1, "feat: x")
        check("C14", "git 모드 코드만 → 차단", code14, 2)
        check("C14-msg", "git 모드 stderr에 차단 안내", "커밋 차단" in err14, True)

        # C15: git 모드 — 코드+테스트 → 통과
        put(g1, "test_app.py", "def test_x(): pass\n"); sh(g1, "add", "test_app.py")
        check("C15", "git 모드 코드+테스트 → 통과", run_git_hook(g1, "feat: x")[0], 0)

        # C16: git 모드 — 메시지 파일의 [no-test] → 통과
        sh(g1, "reset", "-q", "test_app.py"); os.remove(os.path.join(g1, "test_app.py"))
        check("C16", "git 모드 [no-test] → 통과",
              run_git_hook(g1, "chore: fmt [no-test]")[0], 0)

        # C17: git 모드 — merge 진행 상태 → 통과 (pull 머지 커밋 거짓 차단 방지)
        merge_head = os.path.join(g1, ".git", "MERGE_HEAD")
        with open(merge_head, "w") as f:
            f.write("0" * 40 + "\n")
        check("C17", "merge 상태 → 통과", run_git_hook(g1, "Merge branch 'x'")[0], 0)
        os.remove(merge_head)

        # C17b: git 모드 — cherry-pick 진행 상태 → 통과
        cp_head = os.path.join(g1, ".git", "CHERRY_PICK_HEAD")
        with open(cp_head, "w") as f:
            f.write("0" * 40 + "\n")
        check("C17b", "cherry-pick 상태 → 통과", run_git_hook(g1, "feat: picked")[0], 0)
        os.remove(cp_head)

        # C18: git 모드 — 루트 하네스 / dev/ 저장소 → 통과
        check("C18a", "git 모드 루트 하네스 → 통과",
              run_git_hook(HARNESS_ROOT, "chore(harness): x")[0], 0)
        check("C18b", "git 모드 dev/ 저장소 → 통과", run_git_hook(rd, "feat: z")[0], 0)

        # C19: git 모드 — 메시지 파일 없음 → fail-open 통과
        check("C19", "메시지 파일 없음 → 통과",
              run_git_hook(g1, None, msg_path=os.path.join(tmp, "no-such-msg"))[0], 0)

        # C22: git 모드 — 최초 커밋(HEAD 없음) → 통과
        g4 = make_repo(os.path.join(tmp, "g4"), initial_commit=False)
        put(g4, "app.py"); sh(g4, "add", "app.py")
        check("C22", "git 모드 최초 커밋 → 통과", run_git_hook(g4, "init")[0], 0)

        # C20: shim 통합 — core.hooksPath 경유 실제 git commit이 차단/통과
        g2 = make_repo(os.path.join(tmp, "g2"))
        put(g2, "app.py"); sh(g2, "add", "app.py")
        p20 = git_with_hooks(g2, "commit", "-m", "feat: x")
        check("C20", "shim 통합 — 코드만 커밋 차단", p20.returncode != 0, True)
        check("C20-msg", "shim 통합 — 차단 안내 출력", "커밋 차단" in p20.stderr, True)
        put(g2, "tests/test_app.py", "def test_x(): pass\n"); sh(g2, "add", "-A")
        check("C20b", "shim 통합 — 코드+테스트 커밋 성공",
              git_with_hooks(g2, "commit", "-q", "-m", "feat: x").returncode, 0)

        # C21: shim 체인 — 게이트 통과 후 저장소 로컬 commit-msg 훅이 실행됨
        g3 = make_repo(os.path.join(tmp, "g3"))
        marker = os.path.join(g3, ".git", "local-hook-ran")
        local_hook = os.path.join(g3, ".git", "hooks", "commit-msg")
        with open(local_hook, "w") as f:
            f.write("#!/bin/sh\ntouch \"%s\"\n" % marker)
        os.chmod(local_hook, 0o755)
        put(g3, "note.md", "hi\n"); sh(g3, "add", "note.md")
        check("C21-commit", "체인 대상 커밋 성공",
              git_with_hooks(g3, "commit", "-q", "-m", "docs: note").returncode, 0)
        check("C21", "로컬 commit-msg 훅으로 체인됨", os.path.exists(marker), True)

        # C23: 게이트 스크립트 부재 → shim이 fail-open (하네스 이동·삭제 시
        # 머신 전역 커밋이 막히면 안 된다 — reviewer F2 회귀)
        orphan = os.path.join(tmp, "orphan-githooks")
        shutil.copytree(GITHOOKS, orphan)
        g5 = make_repo(os.path.join(tmp, "g5"))
        put(g5, "app.py"); sh(g5, "add", "app.py")
        p23 = subprocess.run(
            ["git", "-c", "core.hooksPath=%s" % orphan, "commit", "-q", "-m", "feat: x"],
            cwd=g5, capture_output=True, text=True, timeout=30,
        )
        check("C23", "게이트 스크립트 부재 → 커밋 통과", p23.returncode, 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(dev_probe, ignore_errors=True)

    total, passed = len(results), sum(results)
    print("\n%d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
