#!/usr/bin/env python3
"""secret-gate 회귀 테스트 — 스펙 docs/specs/2026-07-18-secret-gate-hook.md 완료 기준(C1~C12).

실행: python3 .agents/githooks/secret-gate_test.py   (훅 수정 시 반드시 통과 — R6)
부수 효과: 임시 디렉토리만 사용하며 전부 정리한다.

픽스처의 시크릿 유사 문자열은 전부 문자열 연결로 조립한다 — 소스 원문에 패턴이
그대로 있으면 이 테스트 파일의 커밋이 게이트 자신에게 차단된다(스펙 R2 자기 매칭).
"""
import os
import shlex
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

        # A-C02: 사용자 diff 설정(color.ui=always·diff.external·textconv)이 훅의
        # diff 출력을 바꿔 게이트가 조용히 꺼지면 안 된다(감사 1127 C-02).
        ga = make_repo(os.path.join(tmp, "ga"))
        put(ga, "cfg.txt", "key = %s\n" % AWS_KEY)
        sh(ga, "add", "cfg.txt")
        sh(ga, "config", "color.ui", "always")
        check("A-C02a", "color.ui=always 설정 → 여전히 차단", run_hook(ga, "feat: cfg")[0], 65)
        sh(ga, "config", "--unset", "color.ui")
        ext = put(tmp, "ext-diff.sh", "#!/bin/sh\nexit 0\n")
        os.chmod(os.path.join(tmp, ext), 0o755)
        sh(ga, "config", "diff.external", os.path.join(tmp, ext))
        check("A-C02b", "diff.external 설정 → 여전히 차단", run_hook(ga, "feat: cfg")[0], 65)
        sh(ga, "config", "--unset", "diff.external")
        put(ga, ".gitattributes", "*.txt diff=hide\n")
        sh(ga, "config", "diff.hide.textconv", "true")
        check("A-C02c", "textconv 드라이버 → 여전히 차단", run_hook(ga, "feat: cfg")[0], 65)
        os.remove(os.path.join(ga, ".gitattributes"))

        # A-C04: [secret-ok]는 실제 메시지 본문에서만 인정한다 — 주석 줄·`commit -v`
        # 가위선 아래 diff는 최종 메시지가 아니다(감사 1127 C-04).
        check("A-C04a", "주석 줄의 [secret-ok] → 무시(차단)",
              run_hook(ga, "feat: cfg\n# [secret-ok]\n")[0], 65)
        check("A-C04b", "가위선 아래의 [secret-ok] → 무시(차단)",
              run_hook(ga, "feat: cfg\n# ------------------------ >8 ------------------------\n"
                           "+see [secret-ok] docs\n")[0], 65)
        check("A-C04c", "본문의 [secret-ok] + 주석 줄 → 통과",
              run_hook(ga, "docs: example [secret-ok]\n# Please enter the commit message\n")[0], 0)
        sh(ga, "config", "core.commentChar", ";")
        check("A-C04d", "core.commentChar=; 주석 줄의 [secret-ok] → 무시(차단)",
              run_hook(ga, "feat: cfg\n; [secret-ok]\n")[0], 65)
        sh(ga, "config", "--unset", "core.commentChar")

        # A-C04e: 실커밋 재현 — 마커를 언급한 문서가 `git commit -v` diff로 메시지
        # 파일에 들어가도 확인 없는 면제가 되면 안 된다.
        gv = make_repo(os.path.join(tmp, "gv"))
        put(gv, "cfg.txt", "k=%s\n" % AWS_KEY)
        put(gv, "NOTES.md", "see the [secret-ok] marker docs\n")
        sh(gv, "add", "-A")
        editor = put(tmp, "prepend-editor.py",
                     "import sys\np = sys.argv[1]\nold = open(p).read()\n"
                     "open(p, 'w').write('feat: add cfg\\n' + old)\n")
        p_v = subprocess.run(
            ["git", "-c", "core.hooksPath=%s" % GITHOOKS, "commit", "-q", "-v"],
            cwd=gv, capture_output=True, timeout=30, encoding="utf-8", errors="replace",
            env={**os.environ, "GIT_EDITOR": "%s %s" % (
                shlex.quote(sys.executable), shlex.quote(os.path.join(tmp, editor)))})
        check("A-C04e", "commit -v diff 속 [secret-ok] → 차단", p_v.returncode != 0, True)

        # A-C04f: core.commentChar=auto — 메시지에 `#`로 시작하는 줄이 있으면 git은
        # 다른 후보(`;` 등)를 주석 문자로 골라 가위선도 `; … >8 …`이 된다. 훅이 `#`로
        # 가정하면 가위선 아래 diff의 마커가 면제가 된다(리뷰 V-02 실커밋 재현).
        sh(gv, "config", "core.commentChar", "auto")
        p_f = subprocess.run(
            ["git", "-c", "core.hooksPath=%s" % GITHOOKS, "commit", "-q", "-v", "-e",
             "-m", "#123 feat: add cfg"],
            cwd=gv, capture_output=True, timeout=30, encoding="utf-8", errors="replace",
            env={**os.environ, "GIT_EDITOR": "true"})
        check("A-C04f", "commentChar=auto + `#` 줄 메시지의 commit -v diff 속 [secret-ok] → 차단",
              p_f.returncode != 0, True)
        sh(gv, "config", "--unset", "core.commentChar")

        # A-C04h: 실커밋 — core.commentString을 설정해도 git <2.45는 `#` 가위선을 쓴다.
        # 훅이 commentString만 따르면 `#` 가위선을 놓쳐 diff 속 마커가 면제가 된다(리뷰
        # V2-01).
        sh(gv, "config", "core.commentString", "//")
        p_h = subprocess.run(
            ["git", "-c", "core.hooksPath=%s" % GITHOOKS, "commit", "-q", "-v"],
            cwd=gv, capture_output=True, timeout=30, encoding="utf-8", errors="replace",
            env={**os.environ, "GIT_EDITOR": "%s %s" % (
                shlex.quote(sys.executable), shlex.quote(os.path.join(tmp, editor)))})
        check("A-C04h", "commentString=// + commit -v diff 속 [secret-ok] → 차단",
              p_h.returncode != 0, True)
        sh(gv, "config", "--unset", "core.commentString")

        # A-C04i·j: git ≥2.45가 쓰는 가위선을 훅 수준에서 재현 — 뒤 공백 접두 "// "의
        # `//  --- >8 ---`(V2-02), `#`이 가릴 수 있는 더 긴 접두 "##"(V3-01). 가위선 아래
        # 마커는 무시돼야 한다.
        for cid, val in (("A-C04i", "// "), ("A-C04j", "##")):
            sh(ga, "config", "core.commentString", val)
            check(cid, "commentString=%r 가위선 아래 [secret-ok] → 무시(차단)" % val,
                  run_hook(ga, "feat: cfg\n%s %s\n[secret-ok]\n" % (val, "------------------------ >8 ------------------------"))[0], 65)
            sh(ga, "config", "--unset", "core.commentString")

        # A-C04g: core.commentString(git ≥2.45)도 주석 접두에 더한다 — 접두는 `#`·commentChar·
        # commentString의 합집합이다(리뷰 V-03, V2-01).
        sh(ga, "config", "core.commentChar", ";")
        sh(ga, "config", "core.commentString", "//")
        check("A-C04g", "core.commentString=// 주석 줄의 [secret-ok] → 무시(차단)",
              run_hook(ga, "feat: cfg\n// [secret-ok]\n")[0], 65)
        sh(ga, "config", "--unset", "core.commentString")
        sh(ga, "config", "--unset", "core.commentChar")

        # A-C09: 내용이 `++ `로 시작하는 추가 줄(diff 줄 `+++ …`)도 검사한다 —
        # `+++ `는 파일 헤더 구간에서만 헤더다(감사 1127 C-09).
        gp = make_repo(os.path.join(tmp, "gp"))
        put(gp, "plus.txt", "++ %s\nok\n" % AWS_KEY)
        sh(gp, "add", "plus.txt")
        check("A-C09", "`++ ` 접두 줄의 시크릿 → 차단", run_hook(gp, "feat: plus")[0], 65)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total, passed = len(results), sum(results)
    print("\n%d/%d passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
