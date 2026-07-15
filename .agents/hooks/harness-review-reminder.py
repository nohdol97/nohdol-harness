#!/usr/bin/env python3
"""harness-review-reminder — 일일·주간 점검 자동 트리거 (SessionStart).

2단 주기(R3): 주간 전체 점검(7일 — 수축·효율 신호와 무결성 포함)이 지났으면
전체 모드 지시를, 아니고 일일 경량 점검(1일 — 마지막 점검 이후의 확장 신호
①~③ 스캔만)이 지났으면 일일 모드 지시를 세션 시작 컨텍스트에 주입한다. 실행 자체는 세션의 모델이 한다 —
점검 제안은 사용자 승인이 필요해 무인 실행이 아니라 사람이 있는 세션에서
돌아야 하기 때문이다.

마커는 harness-review 스킬이 점검 완료 시 갱신한다(일일 → daily 마커,
전체 → 두 마커 모두). 이 훅은 읽기 전용이며 어떤 실패도 세션을 막지
않는다(fail-open).

스펙: docs/specs/2026-07-14-harness-review-reminder-hook.md
회귀 테스트: .agents/hooks/harness-review-reminder_test.py (수정 시 반드시 통과)
"""
import datetime
import os
import sys

try:
    # stdio UTF-8 재구성의 단일 원본(스펙 2026-07-15-hooks-common-bootstrap).
    from _common import utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    def utf8_stdio():
        pass

WEEKLY_DAYS = 7
DAILY_DAYS = 1
WEEKLY_MARKER = os.path.join("_workspace", ".harness-review-last")
DAILY_MARKER = os.path.join("_workspace", ".harness-review-daily-last")


def days_since(marker_content, today):
    """마커 내용(YYYY-MM-DD)으로 경과일 계산. 파싱 불가·빈 값은 None(기록 없음)."""
    try:
        last = datetime.date.fromisoformat((marker_content or "").strip())
    except ValueError:
        return None
    return (today - last).days


def decide_mode(weekly_days, daily_days):
    """경과일 → 실행 모드(R3): 'full' > 'daily' > None(침묵). 기록 없음은 경과로 취급."""
    if weekly_days is None or weekly_days >= WEEKLY_DAYS:
        return "full"
    if daily_days is None or daily_days >= DAILY_DAYS:
        return "daily"
    return None


def _ago(days):
    if days is None:
        return "기록 없음"
    return "오늘" if days == 0 else f"{days}일 전"


def build_message(mode, weekly_days, daily_days):
    if mode == "full":
        since = "기록이 없습니다" if weekly_days is None else f"{weekly_days}일이 지났습니다"
        return (
            f"[harness-review 리마인더] 주간 전체 점검 — 마지막 전체 점검 {since}. "
            "이 세션의 첫 응답에서 harness-review 점검 서브에이전트를 백그라운드로 "
            "즉시 발행하세요(스킬 '실행 방식' 절 — 메인 루프가 직접 점검하지 않는다). "
            "점검이 도는 동안 사용자 요청을 병행 처리하고, 완료되면 결과(신호·무결성·"
            "제안)를 채팅으로 보고하세요. 마커(_workspace/.harness-review-last·"
            ".harness-review-daily-last, 오늘 날짜 YYYY-MM-DD)와 운영 로그"
            "(_workspace/harness-ops-log.md) 갱신은 서브에이전트가 수행합니다 — "
            "완료 보고 시 갱신 여부를 확인하세요."
        )
    if mode == "daily":
        return (
            "[harness-review 리마인더] 일일 경량 점검 — 이 세션의 첫 응답에서 "
            "harness-review 일일 모드(마지막 점검 이후 확장 신호 ①~③ 스캔만) "
            "서브에이전트를 백그라운드로 즉시 발행하세요(스킬 '실행 방식' 절, "
            "수축·효율 신호와 무결성 점검은 주간의 몫). "
            "사용자 요청은 병행 처리하고, 완료되면 결과를 채팅으로 보고하세요. "
            "일일 마커(_workspace/.harness-review-daily-last)와 운영 로그"
            "(_workspace/harness-ops-log.md) 갱신은 서브에이전트가 수행합니다."
        )
    # 기한 전 — 점검 지시 대신 상태 한 줄(훅이 동작했다는 증거를 채팅에 남긴다).
    return (
        f"[세션 훅 상태] harness-review 리마인더 정상 동작 — 마지막 전체 점검 "
        f"{_ago(weekly_days)}·일일 점검 {_ago(daily_days)}, 기한 전이라 점검을 "
        "건너뜁니다(주기: 일일 1일·전체 7일). 첫 응답에서 사용자에게 세션 훅 상태를 "
        "한 줄로 알리세요. 지난 점검·개선 내역은 _workspace/harness-ops-log.md에 있습니다."
    )


def read_marker(base, relpath):
    path = os.path.join(base, relpath)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def main():
    try:
        utf8_stdio()
        base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        today = datetime.date.today()
        weekly_days = days_since(read_marker(base, WEEKLY_MARKER), today)
        daily_days = days_since(read_marker(base, DAILY_MARKER), today)
        msg = build_message(decide_mode(weekly_days, daily_days), weekly_days, daily_days)
        if msg:
            print(msg)
    except Exception:
        pass  # fail-open (R4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
