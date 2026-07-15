#!/usr/bin/env python3
"""agentsview-daemon — 세션 시작 시 동기화 데몬 자동 기동 (SessionStart).

agentsview의 세션 인덱싱(로컬 SQLite 동기화)은 데몬이 떠 있어야 지속된다.
이 훅은 Claude Code 세션이 열릴 때마다 데몬 기동을 보장해 수동 sync를 없앤다.
보조 도구가 세션 시작을 막으면 안 되므로 미설치·실패는 전부 조용히
통과한다(fail-open).

스펙: docs/specs/2026-07-14-agentsview-daemon-hook.md
회귀 테스트: .agents/hooks/agentsview-daemon_test.py (수정 시 반드시 통과)
"""
import os
import re
import shutil
import subprocess
import sys

try:
    # stdio UTF-8 재구성의 단일 원본(스펙 2026-07-15-hooks-common-bootstrap).
    from _common import utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    def utf8_stdio():
        pass


NOT_RUNNING_RE = re.compile(
    # 부정문을 먼저 배제한다 — 버전마다 문구가 다르다: "daemon not running",
    # "No agentsview daemon is running."(v0.38.1 실측), "stopped".
    # 긍정 substring("running") 단독 판정은 부정문까지 실행 중으로 오판해
    # 재기동을 영원히 건너뛴다(2026-07-14 오판정 장애).
    r"\bnot\s+running\b|\bno\b[^\n]*\brunning\b|\bstopped\b"
)


def daemon_running(rc, output):
    """status 결과로 실행 여부 판정(R2) — 정상 종료 + 부정문 부재 + running 표기."""
    if rc != 0:
        return False
    low = (output or "").lower()
    if NOT_RUNNING_RE.search(low):
        return False
    return "running" in low


def start_daemon(binary):
    """데몬을 분리(detached) 실행한다(R3) — 훅이 데몬 수명을 기다리지 않는다."""
    kwargs = dict(
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
    )
    if os.name == "nt":
        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        kwargs["creationflags"] = 0x00000008 | 0x00000200
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([binary, "daemon", "start"], **kwargs)


def main():
    # 정상 경로는 상태 한 줄을 남긴다(훅 동작 가시화 — 2026-07-14 사용자 요청).
    # 예외 경로만 무출력 fail-open(R4) — print 포함 전 구간이 try 안에 있어야 한다.
    try:
        utf8_stdio()
        binary = shutil.which("agentsview")
        if not binary:
            print("[세션 훅 상태] agentsview 데몬: 미설치 — 건너뜀(설치는 harness-install 3단계)")
            return 0  # 미설치 — no-op (R1)
        st = subprocess.run(
            # encoding 명시 — 로케일 기본 인코딩(cp949 등) 의존 디코딩 제거(tdd-gate
            # C15와 동일 클래스). status 출력은 ASCII지만 비의존을 규약으로 고정한다.
            [binary, "daemon", "status"], capture_output=True, timeout=10,
            encoding="utf-8", errors="replace",
        )
        if daemon_running(st.returncode, (st.stdout or "") + (st.stderr or "")):
            print("[세션 훅 상태] agentsview 데몬: 실행 중")
            return 0
        start_daemon(binary)
        print("[세션 훅 상태] agentsview 데몬: 미실행 상태여서 새로 기동함")
    except Exception:
        pass  # fail-open (R4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
