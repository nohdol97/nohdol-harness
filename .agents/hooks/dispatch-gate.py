#!/usr/bin/env python3
"""dispatch-gate — 사내 프로필에서 서브에이전트 발행을 차단 (PreToolUse).

발행 1회의 실측 비용은 검증 기준 약 100k 토큰과 수 분이다(metaskill 「검증
비례성」이 인용하는 2026-07-17 세션 reviewer 6회 평균). 개인 설치처에서는
타당하지만 사내 설치처에서는 감당되지 않는다. **초판(ADR 038)은 그 비용을
검증 축에만 물었고, 사용자가 2026-08-04에 축을 넓혔다** — "orchestrate,
agents 호출도 사내에서는 안되게 막아줘, 비용이 너무 많이 들어". 그래서 이제
프로필이 `사내`면 **역할을 가리지 않고** 발행 자체를 발행 시점에 끊는다.

**규칙 분기만으로 처리하지 않는 이유는 ADR 037이 이미 실측했다** — 9절 티어 표는
선언 이래 적용된 적이 없었고 원인은 발행 지점에 장치가 없었다는 것 하나였다.
발행 때마다 판정해야 하는 의무를 문서에만 두면 같은 결과가 난다.

**유일한 예외는 `infra-specialist`다(사용자 결정 2026-08-04).** 이 축만은 비용이
아니라 블라스트 반경이 판정 기준이라 남긴다 — 7절 5항이 k8s·IaC 변경을 이 역할로
보내는 이유가 admission 선확인이고, 그것 없이 만든 값은 리소스 생성 시점에 터진다.
즉 여기서 통과하는 것은 "싸서"가 아니라 **끊었을 때 더 비싼 유일한 축이라서**다.

**우회 표식은 없다(사용자 결정 2026-08-04: "사내에선 예외 없음").** 초판의
`[review-ok]`는 함께 폐기했다 — 가장 비싼 `reviewer`에만 탈출구가 남고 나머지
역할에는 없는 상태가 비용 논리의 역방향이기 때문이다. 사내에서 발행이 필요하면
이 훅의 등록을 걷는 것이 유일한 경로이며, 그것은 기록이 남는 행위다.

**`subagent_type`이 없어도 막는다.** 타입 미지정 발행은 기본 에이전트로 떨어질 뿐
비용은 그대로다 — 초판이 미지정을 통과시킨 것은 판정 축이 "어느 역할인가"였기
때문이고, 지금 축은 "발행인가"다. 같은 이유로 로스터 밖 타입(`general-purpose`
등)도 막는다: 초판과 `tier-gate`가 공유하던 구멍이 이 축에서는 닫힌다.

**fail-open의 방향이 tier-gate와 반대다.** 저기서는 판독 실패가 통과(=게이트가
약해짐)지만, 여기서는 통과가 곧 "발행이 돌아간다"이다. 개인 설치처의 동작을
한 바이트도 바꾸지 않는 것이 이 훅의 비목표이므로, `사내`로 확정될 때만 막는다.

스펙: docs/specs/2026-08-04-dispatch-gate-hook.md
결정: docs/adr/042-corporate-profile-dispatch-block.md (ADR 038 확장)
회귀 테스트: .agents/hooks/dispatch-gate_test.py (수정 시 반드시 통과)
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
        return None  # 미상 — 차단하지 않는 방향(발행이 돌아간다)

BLOCK_EXIT = 2  # PreToolUse: 도구 호출 차단 + stderr를 모델에게 전달
# Claude 계열은 Agent/Task, Codex는 spawn_agent를 보낸다. 설정 매처와 이
# 집합이 어긋나면 훅 프로세스는 실행돼도 아래 판정 직전에 조용히 통과한다.
AGENT_TOOLS = ("Agent", "Task", "spawn_agent")
AGENT_TYPE_FIELDS = {
    "Agent": "subagent_type",
    "Task": "subagent_type",
    "spawn_agent": "agent_type",
}

# 통과하는 단 하나의 역할. 값이 하나여도 집합으로 두는 것은 판정을 이름 비교
# 한 곳에 모아 두기 위해서다(초판 VERIFY_AGENTS와 같은 자리, 뜻은 반대).
EXEMPT_AGENTS = frozenset({"infra-specialist"})


def message(subagent_type):
    role = subagent_type or "(타입 미지정)"
    return (
        f"[dispatch-gate] 설치처 프로필이 `사내`라 서브에이전트 발행(`{role}`)이 "
        "꺼져 있습니다(ADR 042 — 발행 비용이 사내에서는 감당되지 않는다는 사용자 "
        "판정 2026-08-04). **우회 표식은 없습니다.** 메인 루프가 직접 수행하세요: "
        "수집·구현·진단·검증을 순차로 하고, 산출물에 13절 2항 증거 4종(명령·관측 "
        "출력·기준 충족 근거·미검증 범위)과 함께 **발행이 프로필로 차단돼 팬아웃 "
        "없이 수행했다**는 한 줄을 남기세요 — 그 줄이 없으면 산출물이 병렬 검증을 "
        "거친 것처럼 읽힙니다. `orchestrate` 판정은 이 프로필에서 항상 「직접 수행」"
        "으로 수렴합니다. k8s·IaC 저작만 `infra-specialist`로 통과합니다(7절 5항 "
        "admission 선확인)."
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
        subagent_type = tool_input.get(AGENT_TYPE_FIELDS[data["tool_name"]])
        if not isinstance(subagent_type, str):
            subagent_type = ""  # 미지정도 발행이다 — 면제 비교만 통과시키지 않는다
        if subagent_type.strip().lower() in EXEMPT_AGENTS:
            return 0  # 7절 5항 — 비용이 아니라 블라스트 반경으로 판정하는 축
        # 프로필 판독은 마지막에 한다. 개인 설치처의 발행이 압도적이므로
        # 위 조건을 넘긴 뒤에야 REGISTRY.md를 읽는다.
        base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        if read_profile(base) != CORPORATE:
            return 0  # 개인·미상·부재·판독 실패 — 전부 통과
        print(message(subagent_type), file=sys.stderr)
        return BLOCK_EXIT
    except Exception:
        return 0  # fail-open — 게이트 자체의 결함이 작업을 막지 않는다


if __name__ == "__main__":
    sys.exit(main())
