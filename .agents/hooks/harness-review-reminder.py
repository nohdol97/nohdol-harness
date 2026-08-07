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
    # stdio UTF-8 재구성과 설치처 프로필 판독의 단일 원본
    # (스펙 2026-07-15-hooks-common-bootstrap). ADR 045로 dispatch-gate가 사라져
    # 프로필 판독기의 소비자는 이 훅 하나지만, 판독기는 「경량 모델」 절과 같은
    # 절 파서(`_section_items`)를 쓰므로 _common에 남는다 — 옮기면 그 파서가
    # 둘로 갈라져 이 파일이 없애려던 fix 연쇄가 되돌아온다.
    from _common import CORPORATE, read_profile, utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    CORPORATE = "사내"

    def utf8_stdio():
        pass

    def read_profile(base):
        return None  # 미상 — 일일 점검을 억제하지 않는 방향

WEEKLY_DAYS = 7
DAILY_DAYS = 1
WEEKLY_MARKER = os.path.join("_workspace", ".harness-review-last")
DAILY_MARKER = os.path.join("_workspace", ".harness-review-daily-last")

# 경과일의 '오늘'은 한국 표준시(KST, UTC+9 — DST 없음) 기준이다. 컨테이너가
# UTC면 일일/주간 경계가 사용자 타임존과 하루 어긋난다(2026-07-16 사용자 지적).
KST = datetime.timezone(datetime.timedelta(hours=9))


def today_kst(now=None):
    """KST 기준 오늘. aware datetime을 주면 그 시각의 KST 날짜(테스트 결정성 — C9)."""
    if now is None:
        now = datetime.datetime.now(KST)
    return now.astimezone(KST).date()


def days_since(marker_content, today):
    """마커 내용(YYYY-MM-DD)으로 경과일 계산. 파싱 불가·빈 값은 None(기록 없음)."""
    try:
        last = datetime.date.fromisoformat((marker_content or "").strip())
    except ValueError:
        return None
    return (today - last).days


def decide_mode(weekly_days, daily_days, profile=None):
    """경과일 → 실행 모드(R3): 'full' > 'daily' > None(침묵). 기록 없음은 경과로 취급."""
    if weekly_days is None or weekly_days >= WEEKLY_DAYS:
        return "full"
    if daily_days is None or daily_days >= DAILY_DAYS:
        # R8 — 사내 설치처는 추적 하네스 파일의 수정·커밋·푸시가 금지(§5·ADR 012)라
        # 일일이 찾은 확장 신호 ①~③을 그 기계에서 적용할 수 없다. 주간은 남긴다:
        # 무결성 점검(심볼릭 링크·Codex 어댑터 드리프트)은 하네스를 고치지 않아도
        # 즉시 값이 있다. 프로필 미상은 억제하지 않는다 — 억제 방향으로 fail하면
        # 개인 설치처에서 판독이 한 번 어긋난 순간 일일 점검이 영구 침묵한다(R2와 같은 논리).
        if profile == CORPORATE:
            return None
        return "daily"
    return None


def build_message(mode, weekly_days, daily_days):
    if mode == "full":
        since = "기록이 없습니다" if weekly_days is None else f"{weekly_days}일이 지났습니다"
        return (
            f"[harness-review 리마인더] 주간 전체 점검 — 마지막 전체 점검 {since}. "
            "이 세션의 첫 응답에서 harness-review 점검 서브에이전트를 explorer "
            "타입으로(general-purpose 아님) **`model`을 explore 티어 기준으로 "
            "지정해**(루트 9절 표 — 미지정은 세션 모델 상속이라 점검이 상위 "
            "모델로 과소모됩니다) 백그라운드 즉시 발행하세요"
            "(스킬 '실행 방식' 절 — 메인 루프가 직접 점검하지 않는다). "
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
            "서브에이전트를 explorer 타입으로(general-purpose 아님) "
            "**`model`을 explore 티어 기준으로 지정해**(루트 9절 표 — 미지정은 "
            "세션 모델 상속이라 점검이 상위 모델로 과소모됩니다) 백그라운드 "
            "즉시 발행하세요(스킬 '실행 방식' 절, "
            "수축·효율 신호와 무결성 점검은 주간의 몫). "
            "사용자 요청은 병행 처리하고, 완료되면 결과를 채팅으로 보고하세요. "
            "일일 마커(_workspace/.harness-review-daily-last)와 운영 로그"
            "(_workspace/harness-ops-log.md) 갱신은 서브에이전트가 수행합니다."
        )
    # 기한 전(둘 다 최신) — 점검할 게 없으면 침묵한다(무출력).
    # 사용자 요청(2026-07-16): "오늘은 이미 했다"는 상태 줄은 매 세션 노이즈다.
    # 가시성은 점검이 필요할 때(full·daily)만 남기고, 설치 검증은 harness-install의 몫.
    return None


def read_marker(base, relpath):
    path = os.path.join(base, relpath)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        # 부재·읽기 실패(권한 등)·손상 모두 "기록 없음"(R2) — 실패 방향은 침묵이
        # 아니라 점검 유도다. 예외가 main까지 새면 fail-open이 삼켜 리마인더가
        # 영구 침묵한다. `except OSError`로는 UTF-8이 아닌 마커의
        # UnicodeDecodeError를 놓쳤다(독립 검증 2026-08-03 F6 — 재현 확인).
        return None


def main():
    try:
        utf8_stdio()
        base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        today = today_kst()
        weekly_days = days_since(read_marker(base, WEEKLY_MARKER), today)
        daily_days = days_since(read_marker(base, DAILY_MARKER), today)
        mode = decide_mode(weekly_days, daily_days, read_profile(base))
        msg = build_message(mode, weekly_days, daily_days)
        if msg:
            print(msg)
    except Exception:
        pass  # fail-open (R4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
