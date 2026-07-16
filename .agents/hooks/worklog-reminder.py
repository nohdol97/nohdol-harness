#!/usr/bin/env python3
"""worklog-reminder — 세션 경계 진행-기록 리마인더 (SessionStart).

claude-mem(github.com/thedotmack/claude-mem, Apache-2.0)의 '세션 경계에서
컨텍스트를 잃지 않는다'는 착안을 이 하네스의 무의존 방식으로 옮긴 것이다.
claude-mem은 SessionEnd/Stop 훅으로 세션 전체를 캡처·압축해 로컬 워커·벡터
DB에 쌓지만(상시 인프라), 이 하네스가 메우려는 공백은 '전수 기억'이 아니라
work-tracker 흐름 2(세션 종료 시 진행 로그)의 '실행이 기억에 의존'하는 지점
하나다(14절). SessionEnd/Stop 훅은 모델을 깨우지 못해 지시를 세션에 주입할 수
없으므로(harness-review-reminder와 같은 제약), 대신 **다음 세션 SessionStart에
로컬 git으로 이전 세션이 남긴 미커밋 작업을 감지**해 흐름 2/3을 환기한다 —
워커·DB·SessionEnd 훅 없이 같은 경계 보호를 얻는다.

읽기 전용·로컬 전용(네트워크 없음)·fail-open. 마커·상태를 쓰지 않는다.

스펙: docs/specs/2026-07-16-worklog-reminder-hook.md / 결정: docs/adr/018
회귀 테스트: .agents/hooks/worklog-reminder_test.py (수정 시 반드시 통과)
"""
import os
import subprocess
import sys

try:
    # stdio UTF-8 재구성의 단일 원본(스펙 2026-07-15-hooks-common-bootstrap).
    from _common import utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    def utf8_stdio():
        pass


def _git(args, cwd):
    # core.quotepath=false — 비ASCII 경로가 8진수 이스케이프로 감싸이는 것을 막는다
    # (tdd-gate와 동일 방어). encoding 명시로 로케일 의존 디코딩 오류도 피한다.
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args], cwd=cwd,
        capture_output=True, timeout=10, encoding="utf-8", errors="replace",
    )


def dirty_count(base):
    """추적 파일의 미커밋 변경 수(staged+unstaged). git 불가·비저장소는 None(침묵).

    미추적 파일은 제외한다(R2) — 새 산출물·빌드물·_workspace 잔여물의 노이즈가
    리마인더를 남발시키면 게이트가 무시된다. 신호는 '추적 중인 작업이 커밋되지
    않은 상태'다."""
    try:
        r = _git(["status", "--porcelain=v1", "--untracked-files=no"], base)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return len([ln for ln in r.stdout.splitlines() if ln.strip()])


def current_branch(base):
    """현재 브랜치명(detached·오류·비저장소는 None) — 메시지 맥락용."""
    try:
        r = _git(["branch", "--show-current"], base)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def build_message(branch, n):
    """미커밋 변경이 있으면 흐름 2/3 환기 메시지, 없으면 None(침묵 — R3)."""
    if not n:  # 0 또는 None
        return None
    where = f"브랜치 `{branch}`에 " if branch else ""
    return (
        f"[work-tracker 리마인더] {where}미커밋 변경 {n}개가 남아 있습니다 — "
        "이전 세션의 진행 중 작업일 수 있습니다. 이어서 하는 작업이면 work-tracker "
        "흐름 3(재개 — 열린 epic 이슈의 마지막 진행 로그 확인)으로, 마무리·중단하는 "
        "작업이면 흐름 2(진행 로그: 완료/다음/막힘)로 상태를 남기세요 — 멀티세션 "
        "작업만 해당하며, 한 세션에 끝나는 변경은 커밋/PR로 충분합니다. "
        "이 리마인더는 미커밋 변경이 감지될 때만 뜹니다."
    )


def main():
    try:
        utf8_stdio()
        base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        msg = build_message(current_branch(base), dirty_count(base))
        if msg:
            print(msg)
    except Exception:
        pass  # fail-open (R4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
