#!/usr/bin/env python3
"""harness-review-reminder — 주간 점검 자동 트리거 (SessionStart).

마지막 harness-review로부터 7일이 지났으면 세션 시작 컨텍스트에 실행 지시를
주입한다. 실행 자체는 세션의 모델이 한다 — 점검 제안은 사용자 승인이 필요해
무인 실행이 아니라 사람이 있는 세션에서 돌아야 하기 때문이다.

마커(`_workspace/.harness-review-last`)는 harness-review 스킬이 점검 완료 시
갱신한다. 이 훅은 읽기 전용이며 어떤 실패도 세션을 막지 않는다(fail-open).

스펙: docs/specs/2026-07-14-harness-review-reminder-hook.md
회귀 테스트: .agents/hooks/harness-review-reminder_test.py (수정 시 반드시 통과)
"""
import datetime
import os
import sys

INTERVAL_DAYS = 7
MARKER_RELPATH = os.path.join("_workspace", ".harness-review-last")


def days_since(marker_content, today):
    """마커 내용(YYYY-MM-DD)으로 경과일 계산. 파싱 불가·빈 값은 None(기록 없음)."""
    try:
        last = datetime.date.fromisoformat((marker_content or "").strip())
    except ValueError:
        return None
    return (today - last).days


def build_message(days):
    """경과 상태 → 주입할 지시문. 출력 불필요면 None (R3)."""
    if days is None:
        return (
            "[harness-review 리마인더] 주간 점검 기록이 없습니다. "
            "harness-review 스킬을 지금 실행하고, 완료 시 "
            "_workspace/.harness-review-last에 오늘 날짜(YYYY-MM-DD)를 기록하세요."
        )
    if days >= INTERVAL_DAYS:
        return (
            f"[harness-review 리마인더] 마지막 주간 점검으로부터 {days}일이 지났습니다. "
            "harness-review 스킬을 지금 실행하고, 완료 시 "
            "_workspace/.harness-review-last를 오늘 날짜로 갱신하세요."
        )
    return None


def main():
    try:
        base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        marker = os.path.join(base, MARKER_RELPATH)
        content = None
        if os.path.isfile(marker):
            with open(marker, encoding="utf-8") as f:
                content = f.read()
        msg = build_message(days_since(content, datetime.date.today()))
        if msg:
            print(msg)
    except Exception:
        pass  # fail-open (R4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
