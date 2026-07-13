#!/usr/bin/env python3
"""tdd-gate 회귀 테스트 — 스펙 docs/specs/2026-07-13-tdd-gate-hook.md 완료 기준(C1~C11).

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

results = []


def run_hook(command, cwd, raw=None):
    payload = raw if raw is not None else json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd}
    )
    p = subprocess.run([sys.executable, HOOK], input=payload,
                       capture_output=True, text=True, timeout=30)
    return p.returncode, p.stderr


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

        # 비커밋 git 명령 → 통과
        check("C-etc", "git status → 통과", run_hook("git status", r4)[0], 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(dev_probe, ignore_errors=True)

    total, passed = len(results), sum(results)
    print("\n%d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
