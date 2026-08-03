#!/usr/bin/env python3
"""review-gate — 사내 프로필에서 검증 목적 발행을 차단 (PreToolUse).

검증 발행 1회의 실측 비용은 약 100k 토큰과 수 분이다(metaskill 「검증 비례성」이
인용하는 2026-07-17 세션 reviewer 6회 평균). 개인 설치처에서는 타당하지만 사내
설치처에서는 감당되지 않는다(사용자 판정 2026-08-03). 그래서 프로필이 `사내`면
검증 목적 서브에이전트 발행을 발행 시점에 끊는다.

**규칙 분기만으로 처리하지 않는 이유는 ADR 037이 이미 실측했다** — 9절 티어 표는
선언 이래 적용된 적이 없었고 원인은 발행 지점에 장치가 없었다는 것 하나였다.
발행 때마다 판정해야 하는 의무를 문서에만 두면 같은 결과가 난다.

**fail-open의 방향이 tier-gate와 반대다.** 저기서는 판독 실패가 통과(=게이트가
약해짐)지만, 여기서는 통과가 곧 "검증이 돌아간다"이다. 미상·부재·예외가 검증을
없애는 쪽으로 떨어지면 안 되므로, 이 훅은 `사내`로 확정될 때만 막는다.

우회는 프롬프트의 `[review-ok]` 표식이며 **사용자가 명시적으로 리뷰를 요청한
뒤에만** 붙인다(8절 「사내에서 자동 실행 off, 명시 요청은 실행」과 같은 형태,
`[no-test]`·`[secret-ok]`와 같은 계열). 표식을 넣는 주체가 게이트 대상이라
기계적 보증은 아니다 — 값은 우회가 기록으로 남는다는 점이다.

한계: 규칙이 끄는 범위보다 훅이 좁다. `infra-specialist` 리뷰 모드와 **리뷰
리포트를 모으는 `integrator`**는 같은 타입이 비리뷰 용도로도 쓰여
`subagent_type`만으로 구분되지 않으므로 규칙만으로 관장한다 — 타입으로 막으면
`project-status` Phase 2(상태 아티팩트 fan-in)가 사내에서 통째로 죽고, 그
발행에는 정당한 우회가 없다(`[review-ok]`는 사용자가 리뷰를 요청했다는 표식이라
아무도 요청하지 않은 발행에 달면 표식의 값이 사라진다. 독립 검증 2인 동시 지적).
로스터 밖 타입(`general-purpose` 등)으로 리뷰를 시키면 통과한다(tier-gate와 같은
구멍). 즉 이 훅이 잡는 것은 **가장 흔하고 가장 비싼 한 경로**이지 규칙 전부가
아니며, 나머지는 규칙을 읽는 세션의 몫이다.

스펙: docs/specs/2026-08-03-review-gate-hook.md
결정: docs/adr/038-corporate-profile-verification-exemption.md
회귀 테스트: .agents/hooks/review-gate_test.py (수정 시 반드시 통과)
"""
import json
import os
import sys

try:
    from _common import CORPORATE, read_profile, utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    CORPORATE = "사내"

    def utf8_stdio():
        pass

    def read_profile(base):
        return None  # 미상 — 차단하지 않는 방향(검증이 돌아간다)

BLOCK_EXIT = 2  # PreToolUse: 도구 호출 차단 + stderr를 모델에게 전달
AGENT_TOOLS = ("Agent", "Task")  # 실측: tool_name은 "Agent"(matcher "Task"도 발화)

# **검증 말고는 쓰이는 곳이 없는 역할만 건다.** 실제로 그런 타입은 reviewer
# 하나다 — team-review의 Solo와 관점 팬아웃이 둘 다 이것을 재사용하므로 리뷰
# 경로의 비용 대부분이 여기 모인다. integrator는 넣지 않는다: 리뷰 리포트
# fan-in도 하지만 `project-status` Phase 2와 orchestrate 표준 골조 ⑤처럼
# 검증과 무관한 fan-in에도 쓰여, 타입으로 막으면 그 경로들이 사내에서 죽는다.
# implementer·explorer 등 빌드 측도 대상이 아니다 — 사용자가 지목한 비용 축이
# 검증이고, 구현 위임까지 끊으면 orchestrate의 3파일 위임 규칙이 무너진다.
VERIFY_AGENTS = frozenset({"reviewer"})
OVERRIDE = "[review-ok]"


def message(subagent_type):
    return (
        f"[review-gate] 설치처 프로필이 `사내`라 검증 목적 발행(`{subagent_type}`)이 "
        "꺼져 있습니다(ADR 038 — 검증 1회 약 100k 토큰·수 분이 사내에서는 감당되지 "
        "않는다는 사용자 판정). 대신 메인 루프가 스펙 완료 기준에 대고 직접 검증하고, "
        "산출물에 13절 2항 증거 4종(명령·관측 출력·기준 충족 근거·미검증 범위)과 함께 "
        "**독립 검증이 프로필 면제로 생략됐다**는 한 줄을 남기세요 — 그 줄이 없으면 "
        "산출물이 검증된 것처럼 읽힙니다. 사용자가 명시적으로 리뷰를 요청한 경우에는 "
        f"발행 프롬프트에 `{OVERRIDE}`를 넣어 다시 발행하세요."
    )


def main():
    try:
        utf8_stdio()
        try:
            data = json.loads(sys.stdin.read() or "{}")
        except Exception:
            return 0  # 형식 불명 입력은 통과(fail-open)
        if not isinstance(data, dict):
            return 0
        if data.get("tool_name") not in AGENT_TOOLS:
            return 0
        tool_input = data.get("tool_input")
        if not isinstance(tool_input, dict):
            return 0
        subagent_type = tool_input.get("subagent_type")
        if not isinstance(subagent_type, str):
            return 0
        if subagent_type.strip().lower() not in VERIFY_AGENTS:
            return 0  # 빌드 측·로스터 밖은 이 게이트 관장 밖
        if OVERRIDE in str(tool_input.get("prompt") or ""):
            return 0  # 사용자 명시 요청 — 비용을 그 자리에서 승인한 상태다
        # 프로필 판독은 마지막에 한다. 위 조건을 못 넘긴 발행이 압도적이므로
        # REGISTRY.md를 매 발행마다 읽지 않는다.
        base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        if read_profile(base) != CORPORATE:
            return 0  # 개인·미상·부재·판독 실패 — 전부 통과
        print(message(subagent_type), file=sys.stderr)
        return BLOCK_EXIT
    except Exception:
        return 0  # fail-open — 게이트 자체의 결함이 검증을 없애지 않는다


if __name__ == "__main__":
    sys.exit(main())
