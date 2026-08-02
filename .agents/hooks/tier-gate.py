#!/usr/bin/env python3
"""tier-gate — 서브에이전트 발행에 §9 티어 모델 지정을 강제 (PreToolUse).

루트 AGENTS.md 9절은 티어별 모델을 규정하지만 **적용은 발행 시점의 `model`
파라미터로만 이뤄진다** — 지정하지 않으면 서브에이전트가 부모 세션의 모델을
그대로 상속한다. 그래서 문서 규칙만으로는 세션 모델이 무엇이냐에 따라 판정이
뒤집혔다(실측 2026-08-03, 이 설치처 로컬 로그):

  · 07-22 이전: 세션이 표준 → explorer 표준(우연히 준수) + **검증 25건이
    표준 모델**(9절 위반이자 사용자 전역 정책의 절대 금지 — false negative)
  · 07-25 이후: 세션이 상위 → explorer 25/37이 최상위(위반) + reviewer는
    우연히 준수

즉 두 티어 모두 늘 세션 모델을 상속해 왔고 9절 표가 적용된 적이 없다. 이 훅은
그 원인 하나만 막는다: **티어가 선언된 에이전트를 `model` 없이 발행하면 차단**.

**무엇을 골랐는지는 판정하지 않는다**(ADR 005 탈모델명) — 모델명을 코드에 박으면
CLI 라인업이 바뀔 때마다 훅이 낡고, 9절이 유일한 매핑 원본이라는 규칙도 깨진다.
지정 자체가 상속을 끊으므로 통과시키고, 적절성은 9절을 읽는 세션이 판단한다.

추론 등급은 이 훅의 대상이 아니다 — Claude Code의 Agent 도구는 `effort`
파라미터를 노출하지 않으며(실측 2026-08-03: `tool_input` 키는 description·
prompt·subagent_type·model·run_in_background), 서브에이전트는 부모 세션의
등급을 상속한다.

한계: 판정 입력인 에이전트 정의를 기준 디렉토리에서 찾으므로, 기준이 어긋나면
fail-open으로 통과한다. 비용·품질 규칙이지 3절 가드레일이 아니므로 판독 실패로
작업을 막지 않는다(기존 훅 3종과 같은 방향).

스펙: docs/specs/2026-08-03-tier-gate-hook.md
회귀 테스트: .agents/hooks/tier-gate_test.py (수정 시 반드시 통과)
"""
import json
import os
import re
import sys

try:
    from _common import utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    def utf8_stdio():
        pass

BLOCK_EXIT = 2  # PreToolUse: 도구 호출 차단 + stderr를 모델에게 전달
AGENT_TOOLS = ("Agent", "Task")  # 실측: tool_name은 "Agent"(matcher "Task"도 발화)
_TIER_RE = re.compile(r"^tier:\s*([A-Za-z_-]+)\s*$", re.MULTILINE)
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def read_tier(base, subagent_type):
    """`.agents/agents/<name>.md` frontmatter의 tier. 없거나 못 읽으면 None.

    티어를 코드에 매핑하지 않고 에이전트 정의에서 읽는다 — 정의 파일이 티어
    선언의 원본이고(10절), 로스터가 늘어도 훅을 고칠 필요가 없다.
    """
    if not subagent_type or not _SAFE_NAME.match(subagent_type):
        return None  # 하네스 로스터 밖(general-purpose 등)·경로 조작 시도
    path = os.path.join(base, ".agents", "agents", subagent_type + ".md")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.read(4096)  # frontmatter만 필요하다
    except OSError:
        return None
    if not head.startswith("---"):
        return None
    end = head.find("\n---", 3)
    m = _TIER_RE.search(head[:end] if end > 0 else head)
    return m.group(1) if m else None


def message(subagent_type, tier):
    return (
        f"[tier-gate] `{subagent_type}`는 {tier} 티어인데 `model`을 지정하지 않았습니다. "
        "지정하지 않으면 서브에이전트가 부모 세션의 모델을 그대로 상속해 "
        "루트 AGENTS.md 9절 표가 적용되지 않습니다 — 세션 모델이 무엇이냐에 따라 "
        "검증이 저성능으로 내려가거나(전역 정책 절대 금지) 수집이 최상위 모델로 "
        "과소모됩니다. 9절 표에서 이 티어의 기준을 읽고 현재 CLI 라인업에서 골라 "
        "`model`을 지정한 뒤 다시 발행하세요."
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
        model = tool_input.get("model")
        # 값은 판정하지 않는다 — 지정 자체가 상속을 끊는다. 단 `inherit`는 예외다:
        # 모델명이 아니라 "상속하라"는 지시어라서 미지정과 결과가 같고, 그것을
        # 통과시키면 게이트가 막으려는 상태를 한 단어로 되살린다. 판정 기준은
        # 어느 모델인가가 아니라 상속을 끊었는가이므로 ADR 005와 충돌하지 않는다.
        if model and str(model).strip().lower() != "inherit":
            return 0
        subagent_type = tool_input.get("subagent_type")
        tier = read_tier(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd(),
                         subagent_type)
        if not tier:
            return 0  # 티어 미선언·판독 실패는 9절 관장 밖(fail-open)
        print(message(subagent_type, tier), file=sys.stderr)
        return BLOCK_EXIT
    except Exception:
        return 0  # fail-open — 게이트 자체의 결함이 작업을 막지 않는다


if __name__ == "__main__":
    sys.exit(main())
