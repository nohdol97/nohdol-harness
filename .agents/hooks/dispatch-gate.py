#!/usr/bin/env python3
"""Block native Claude/Codex subagents on corporate profiles (ADR 042).

Infra authoring remains the sole native exception. Corporate hosts perform work
directly under ADR 055. This hook does not trust runtime environment markers
or add a native override token.
Spec: docs/specs/2026-08-04-dispatch-gate-hook.md
Regression: .agents/hooks/dispatch-gate_test.py
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
        f"[dispatch-gate] 사내 프로필의 native 서브에이전트 발행(`{role}`)은 "
        "차단됩니다(ADR 042·055). 우회 표식은 없습니다. "
        "호스트가 수집·설계·구현·테스트·검토를 직접 수행하세요. "
        "SDD/TDD와 실제 검증 근거를 유지하고 별도 독립 reviewer 세션이 "
        "없었음을 밝히세요. 사내 추적 하네스 수정·반출 제한은 유지합니다. "
        "native 예외는 infra-specialist의 k8s·IaC 작성뿐입니다."
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
