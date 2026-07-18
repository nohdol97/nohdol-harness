#!/usr/bin/env python3
"""secret-gate 회귀 테스트 — 스펙 docs/specs/2026-07-18-secret-gate-hook.md 완료 기준(C1~C12).

실행: python3 .agents/githooks/secret-gate_test.py   (훅 수정 시 반드시 통과 — R6)
부수 효과: 임시 디렉토리만 사용하며 전부 정리한다.

픽스처의 시크릿 유사 문자열은 전부 문자열 연결로 조립한다 — 소스 원문에 패턴이
그대로 있으면 이 테스트 파일의 커밋이 게이트 자신에게 차단된다(스펙 R2 자기 매칭).
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
HOOK = os.path.join(HERE, "secret-gate.py")
GITHOOKS = HERE

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "hooks"))
try:
    from _common import utf8_stdio
except Exception:
    def utf8_stdio():
        pass

results = []

# 연결 조립 — 원문 비노출(모두 공개 문서의 예시 형식이며 실키 아님)
AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"
GH_TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0" + "k1L2m3N4o5P6q7R8"
SLACK_TOKEN = "xoxb-" + "123456789012-abcdefABCDEF"
PRIVATE_KEY = "-----BEGIN OPENSSH " + "PRIVATE KEY-----\nZm9vCg==\n-----END OPENSSH " + "PRIVATE KEY-----"


def run_hook(repo, message, msg_path=None):
    made = None
    if msg_path is None:
        fd, made = tempfile.mkstemp(prefix="secret-gate-msg-")
        with os.fdopen(fd, "w") as f:
            f.write(message)
        msg_path = made
    try:
        p = subprocess.run([sys.executable, HOOK, "--commit-msg", msg_path],
                           cwd=repo, capture_output=True, timeout=30,
                           encoding="utf-8", errors="replace")
        return p.returncode, p.stderr
    finally:
        if made:
            os.remove(made)


def sh(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def make_repo(path, initial_commit=True):
    os.makedirs(path, exist_ok=True)
    sh(path, "init", "-q")
    sh(path, "config", "user.email", "secret-gate-test@local")
    sh(path, "config", "user.name", "secret-gate-test")
    if initial_commit:
        sh(path, "commit", "-q", "--allow-empty", "--no-verify", "-m", "init")
    return path


def put(repo, rel, content):
    p = os.path.join(repo, rel)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(p, mode) as f:
        f.write(content)
    return rel


def check(cid, desc, got, want):
    ok = got == want
    results.append(ok)
    print(("PASS" if ok else "FAIL") + " %s: %s (got=%s, want=%s)" % (cid, desc, got, want))


def main():
    utf8_stdio()
    tmp = tempfile.mkdtemp(prefix="secret-gate-test-")
    try:
        # C1·C12: AWS 키 스테이징 → 차단, stderr에 파일명은 있고 원문은 없다(R5 마스킹)
        g1 = make_repo(os.path.join(tmp, "g1"))
        put(g1, "config.txt", "key = %s\n" % AWS_KEY)
        sh(g1, "add", "config.txt")
        code1, err1 = run_hook(g1, "feat: config")
        check("C1", "AWS 키 스테이징 → 차단", code1, 65)
        check("C1-file", "stderr에 파일명 포함", "config.txt" in err1, True)
        check("C12", "stderr에 시크릿 원문 미포함", AWS_KEY in err1, False)

        # C3: [secret-ok] 마커 → 통과 (스테이징 상태 그대로)
        check("C3", "[secret-ok] 마커 → 통과",
              run_hook(g1, "docs: example key [secret-ok]")[0], 0)

        # C2: 시크릿 없는 diff → 통과
        g2 = make_repo(os.path.join(tmp, "g2"))
        put(g2, "note.md", "hello world\napi design notes\n")
        sh(g2, "add", "note.md")
        check("C2", "시크릿 없는 diff → 통과", run_hook(g2, "docs: note")[0], 0)

        # C4: 개인키 블록 → 차단
        g4 = make_repo(os.path.join(tmp, "g4"))
        put(g4, "id_key", PRIVATE_KEY + "\n")
        sh(g4, "add", "id_key")
        check("C4", "개인키 블록 → 차단", run_hook(g4, "chore: key")[0], 65)

        # C5: 시크릿이 삭제 줄에만 → 통과 (제거 커밋을 막으면 안 된다)
        g5 = make_repo(os.path.join(tmp, "g5"))
        put(g5, "leak.txt", "token = %s\n" % AWS_KEY)
        sh(g5, "add", "leak.txt")
        sh(g5, "commit", "-q", "--no-verify", "-m", "seed")
        put(g5, "leak.txt", "token = REDACTED\n")
        sh(g5, "add", "leak.txt")
        check("C5", "삭제 줄의 시크릿만 → 통과", run_hook(g5, "fix: remove leak")[0], 0)

        # C6: 최초 커밋(HEAD 없음)에 시크릿 → 차단 (예외 아님 — 스펙 R3)
        g6 = make_repo(os.path.join(tmp, "g6"), initial_commit=False)
        put(g6, ".env", "AWS_KEY=%s\n" % AWS_KEY)
        sh(g6, "add", ".env")
        check("C6", "최초 커밋의 시크릿 → 차단", run_hook(g6, "init")[0], 65)

        # C7: 메시지 파일 없음 → fail-open 통과
        check("C7", "메시지 파일 없음 → 통과",
              run_hook(g1, "", msg_path=os.path.join(tmp, "no-such-msg"))[0], 0)

        # C8: MERGE_HEAD 진행 상태 → 통과 (재조합 커밋 — 스펙 R3)
        mpath = os.path.join(g1, ".git", "MERGE_HEAD")
        with open(mpath, "w") as f:
            f.write("0" * 40 + "\n")
        check("C8", "MERGE_HEAD 상태 → 통과", run_hook(g1, "Merge branch 'x'")[0], 0)
        os.remove(mpath)

        # C9: GitHub 토큰·Slack 토큰 → 차단
        g9 = make_repo(os.path.join(tmp, "g9"))
        put(g9, "ci.txt", "gh auth: %s\n" % GH_TOKEN)
        sh(g9, "add", "ci.txt")
        check("C9a", "GitHub 토큰 → 차단", run_hook(g9, "ci: token")[0], 65)
        put(g9, "ci.txt", "slack: %s\n" % SLACK_TOKEN)
        sh(g9, "add", "ci.txt")
        check("C9b", "Slack 토큰 → 차단", run_hook(g9, "ci: slack")[0], 65)

        # C10: 바이너리 파일 → 통과 (크래시 없음)
        g10 = make_repo(os.path.join(tmp, "g10"))
        put(g10, "blob.bin", b"\x00\x01\x02" + AWS_KEY.encode() + b"\x00\xff")
        sh(g10, "add", "blob.bin")
        check("C10", "바이너리 파일 → 통과", run_hook(g10, "chore: blob")[0], 0)

        # C11: shim 통합 — core.hooksPath 경유 실커밋 차단·[secret-ok] 통과
        g11 = make_repo(os.path.join(tmp, "g11"))
        put(g11, "cfg.txt", "k=%s\n" % AWS_KEY)
        sh(g11, "add", "cfg.txt")
        p_block = subprocess.run(
            ["git", "-c", "core.hooksPath=%s" % GITHOOKS, "commit", "-q", "-m", "feat: cfg"],
            cwd=g11, capture_output=True, timeout=30,
            encoding="utf-8", errors="replace")
        check("C11a", "shim 경유 시크릿 커밋 → 차단", p_block.returncode != 0, True)
        p_ok = subprocess.run(
            ["git", "-c", "core.hooksPath=%s" % GITHOOKS, "commit", "-q",
             "-m", "docs: example [secret-ok]"],
            cwd=g11, capture_output=True, timeout=30,
            encoding="utf-8", errors="replace")
        check("C11b", "shim 경유 [secret-ok] 커밋 → 통과", p_ok.returncode, 0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total, passed = len(results), sum(results)
    print("\n%d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
