#!/usr/bin/env python3
"""secret-gate — 루트 AGENTS.md 3절 시크릿 기록 금지의 실행 계층 게이트 (git commit-msg 훅).

전역 core.hooksPath(`.agents/githooks/`) 경유로 실행되어, 스테이징된 diff의 추가
줄에 형식이 확정적인 자격증명 패턴(개인키 블록·프로바이더 키)이 있으면 커밋을
차단한다. tdd-gate와 달리 **루트 하네스 예외가 없다** — 시크릿은 어느 git
이력에 들어가도 사고다.

규칙의 원본은 문서(3절)이고 이 훅은 보조 게이트다. 판단 불가 상황은 전부
통과(fail-open) — 정상 커밋을 막으면 우회를 학습시켜 게이트가 죽는다.

스펙: docs/specs/2026-07-18-secret-gate-hook.md / 결정: docs/adr/023
회귀 테스트: .agents/githooks/secret-gate_test.py (수정 시 반드시 통과)
"""
import os
import re
import subprocess
import sys

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "hooks")
)
try:
    from _common import utf8_stdio
except Exception:
    def utf8_stdio():
        pass

# 고신뢰 형식 확정 패턴만(R2) — 일반 대입문·고엔트로피 추정은 비목표다. 오탐이
# 잦으면 [secret-ok] 남용을 학습시켜 게이트 자체가 죽는다(tdd-gate R3 교훈).
# 패턴 추가·제거는 스펙 개정으로만 한다.
PATTERNS = [
    ("개인키 블록", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY")),
    ("AWS Access Key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub 토큰", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("GitHub fine-grained 토큰", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("Slack 토큰", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}")),
    ("Google API 키", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("Stripe 키", re.compile(r"\b[sr]k_(?:live|test)_[0-9a-zA-Z]{20,}\b")),
    ("OpenAI/Anthropic 계열 키", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
]

BLOCK_EXIT = 65  # 의도적 차단 전용 — 인터프리터 실패 코드(1·2)와 구분(tdd-gate R1 근거 동일)

SEQUENCER_MARKERS = (
    "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply",
)


def git(args, cwd):
    # 비ASCII 파일명 방어는 tdd-gate와 동일 근거: quotepath=false + encoding 명시.
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args], cwd=cwd, capture_output=True,
        timeout=15, encoding="utf-8", errors="replace",
    )


# 마커 판정은 최종 커밋 메시지가 될 부분만 본다(감사 1127 C-04). git은 commit-msg
# 훅을 주석 제거 전에 부르므로, 메시지 파일엔 주석 줄(템플릿 안내 등)과
# `commit -v`의 가위선 아래 diff가 남아 있다 — 마커를 언급한 문서의 diff가 확인 없는
# 면제가 되면 안 된다. 주석 접두는 `#`·core.commentChar·core.commentString의
# 합집합이다 — git 버전마다 실제로 쓰는 쪽이 달라(commentString은 ≥2.45만) 훅이 하나를
# 고르면 git이 쓴 가위선을 놓친다(감사 1127 V2-01). `auto`면 후보 전부를 더한다. 접두가
# 늘수록 줄을 더 버리고 더 일찍 자를 뿐이라 판정은 차단 쪽으로만 기운다.
CUT_LINE = " ------------------------ >8 ------------------------"
AUTO_COMMENT_CHARS = "#;@!$%^&|:"  # git builtin/commit.c adjust_comment_line_char 후보


def comment_prefixes(cwd):
    prefixes = {"#"}
    for key in ("core.commentChar", "core.commentString"):
        value = git(["config", "--get", key], cwd).stdout.strip()
        if value == "auto":
            prefixes.update(AUTO_COMMENT_CHARS)
        elif value:
            prefixes.add(value)
    return tuple(sorted(prefixes))


def message_text(msg_path, cwd):
    prefixes = comment_prefixes(cwd)
    with open(msg_path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    kept = []
    for line in lines:
        # 가위선은 일치하는 접두 전부에 대해 본다 — `#`이 `##`·`#!` 같은 더 긴 접두를
        # 가리면 가위선을 놓친다(감사 1127 V3-01).
        if any(line.startswith(p) and line[len(p):].strip() == CUT_LINE.strip()
               for p in prefixes):
            break
        if not line.startswith(prefixes):
            kept.append(line)
    return "\n".join(kept)


def scan(diff_text):
    """diff의 추가 줄만 검사해 (파일, 줄 번호, 패턴명) 목록을 돌려준다(R1).
    삭제 줄은 보지 않는다 — 시크릿 제거 커밋을 막으면 안 된다."""
    findings = []
    path, lineno = None, 0
    # `+++ `는 `diff --git`과 첫 `@@` 사이(파일 헤더 구간)에서만 헤더다 — 헝크 안의
    # `+++ …`는 내용이 `++ `로 시작하는 추가 줄이다(감사 1127 C-09).
    in_header = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            in_header = True
        elif in_header and line.startswith("+++ "):
            p = line[4:]
            path = p[2:] if p.startswith("b/") else p
        elif line.startswith("@@"):
            in_header = False
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+"):
            for label, rx in PATTERNS:
                if rx.search(line):
                    findings.append((path or "?", lineno, label))
                    break
            lineno += 1
    return findings


def judge(findings):
    if not findings:
        return 0
    # 시크릿 값 자체는 출력하지 않는다(R5) — 터미널 로그도 기록면이다.
    lines = "\n".join("  %s:%d — %s" % f for f in findings[:10])
    more = " 외 %d건" % (len(findings) - 10) if len(findings) > 10 else ""
    sys.stderr.write(
        "[secret-gate] 커밋 차단 — 스테이징된 변경에 자격증명 패턴이 있습니다"
        " (루트 AGENTS.md 3절: 시크릿 기록 금지).\n%s%s\n"
        "조치 중 하나를 선택하세요:\n"
        "  1) 시크릿을 제거(환경변수·시크릿 매니저로 이동)하고 다시 커밋한다 (원칙).\n"
        "  2) 문서 예시·테스트 픽스처 등 오탐이면, 사용자에게 확인받은 뒤\n"
        "     커밋 메시지에 [secret-ok] 를 포함해 다시 커밋한다.\n" % (lines, more)
    )
    return BLOCK_EXIT


def git_hook_main(msg_path):
    """git commit-msg 훅 진입점 — cwd는 git이 워크트리 루트로 맞춰준다.
    최초 커밋도 검사한다(R3) — `diff --cached`는 HEAD 없이 빈 트리 대비로 동작하며,
    첫 커밋이야말로 .env가 딸려 들어가는 전형적 시점이다."""
    utf8_stdio()
    cwd = os.getcwd()
    if "[secret-ok]" in message_text(msg_path, cwd):
        return 0

    repo = git(["rev-parse", "--show-toplevel"], cwd)
    if repo.returncode != 0:
        return 0
    repo_dir = os.path.realpath(repo.stdout.strip())

    gitdir = git(["rev-parse", "--git-dir"], repo_dir)
    if gitdir.returncode == 0:
        gd = gitdir.stdout.strip()
        if not os.path.isabs(gd):
            gd = os.path.join(repo_dir, gd)
        if any(os.path.exists(os.path.join(gd, m)) for m in SEQUENCER_MARKERS):
            return 0

    # 사용자 diff 설정이 파서가 읽는 출력 형식을 바꾸지 못하게 고정한다(감사 1127
    # C-02): color.ui=always는 줄 앞에 ANSI 코드를 붙여 `+` 판정을 깨고, diff.external·
    # textconv는 내용 자체를 다른 프로그램 출력으로 바꾼다 — 어느 쪽이든 조용한 통과다.
    r = git(["diff", "--cached", "-U0", "--no-color", "--no-ext-diff", "--no-textconv",
             "--diff-filter=ACMR"], repo_dir)
    if r.returncode != 0:
        return 0
    return judge(scan(r.stdout))


if __name__ == "__main__":
    try:
        if len(sys.argv) >= 3 and sys.argv[1] == "--commit-msg":
            sys.exit(git_hook_main(sys.argv[2]))
        sys.exit(0)  # 알 수 없는 진입 — fail-open
    except Exception:
        sys.exit(0)  # fail-open — 훅 오류가 커밋을 막으면 안 된다(R4)
