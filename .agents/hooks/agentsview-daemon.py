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
import shutil
import subprocess
import sys


def daemon_running(rc, output):
    """status 결과로 실행 여부 판정(R2) — 정상 종료 + running 표기, 'not running'은 미실행."""
    if rc != 0:
        return False
    low = (output or "").lower()
    return "running" in low and "not running" not in low


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
    # 예외 경로만 무출력 fail-open(R4).
    binary = shutil.which("agentsview")
    if not binary:
        print("[세션 훅 상태] agentsview 데몬: 미설치 — 건너뜀(설치는 harness-install 3단계)")
        return 0  # 미설치 — no-op (R1)
    try:
        st = subprocess.run(
            [binary, "daemon", "status"], capture_output=True, text=True, timeout=10
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
