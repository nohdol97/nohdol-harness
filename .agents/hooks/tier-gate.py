#!/usr/bin/env python3
"""tier-gate — 서브에이전트 발행에서 §9 경량 모델 금지를 강제 (PreToolUse).

**판정 대상은 `model`을 지정했는가가 아니라 무엇을 지정했는가다**(ADR 040이
ADR 037의 방향을 뒤집었다). 미지정은 통과시키고, REGISTRY.md 「경량 모델」
절이 나열한 등급을 지정한 발행만 차단한다.

왜 뒤집었나 — 앞 방향이 막던 것과 여는 것이 비대칭이었다:

  · 미지정은 부모 세션 모델 상속이고, 세션은 상위·표준 둘 중 하나다.
    **상속은 경량에 닿을 수 없다** — 사용자 전역 정책이 절대 금지한 상태가
    상속 경로에서는 구조적으로 발생하지 않는다.
  · 지정을 강제하면 그 경로가 처음으로 열린다. 앞 방향은 값을 판정하지
    않기로 했으므로(ADR 037 결정표) 경량을 골라도 통과했다.
  · 실제로 그렇게 됐다(2026-08-03, 이 설치처): 훅이 수집 발행을 막고
    "9절 표를 읽고 골라 지정하라"고 지시했고, 세션은 지시를 성실히 따라
    **경량 모델로 재발행했다.** 사용자가 잡아냈다. 게이트가 유도한 위반이다.
  · 게다가 앞 방향은 자기 근거를 못 막았다 — ADR 037이 더 무겁다고 지목한
    "검증 25건이 표준 모델"은 design 티어에 표준 모델을 **지정**한 상태라
    지정 여부만 보는 게이트를 그대로 통과한다.

그래서 게이트는 비용 문제(explore가 상위 모델을 상속하는 과소모)를 문서
규칙에 돌려주고, 정확성 문제(경량 금지) 하나만 실행 계층에서 막는다.
과소모는 재작업을 부르지 않지만 검증의 false negative는 부른다.

**모델명은 이 코드에 없다**(ADR 005 탈모델명). 판정 입력은 REGISTRY.md
「경량 모델」 절이며, 절이 없으면 발화하지 않는다 — 설치처마다 CLI 라인업이
다르고 시간에 따라 바뀌지만 훅은 바뀌지 않아야 한다. 값 판정을 하면서도
탈모델명이 유지되는 것은 이름이 **데이터**에 있기 때문이다.

우회는 발행 프롬프트의 `[light-ok]` 표식이며, 사용자가 명시적으로
"빠르게/가볍게"를 요청한 뒤에만 붙인다(§9 경량 금지의 예외를 그대로 옮긴 것,
`[no-test]`·`[secret-ok]`와 같은 계열). **단 design 티어에는
닿지 않는다** — 전역 정책은 예외와 **별도로** 검증·리뷰·최종 확인의 경량
사용을 절대 금지하고, 에이전트 정의들도 예외 없이 그렇게 적혀 있다.

`inherit`에는 분기가 없다. 경량 목록에 없는 문자열이라 일반 경로에서 통과하며,
따로 처리하면 죽은 분기가 된다(초판에서는 차단 대상이라 분기가 필요했다).

한계: **티어 적합성은 여전히 보지 않는다.** design 티어에 표준 모델을 골라도
막히지 않으며, 그것은 §9를 읽는 세션의 몫이다. 이 훅이 막는 것은 전역 정책이
**절대 금지**로 못박은 한 등급뿐이다. 로스터 밖 타입, 판독 실패, 절 부재,
내부 예외는 전부 통과한다(fail-open — 비용·품질 규칙이지 3절 가드레일이
아니다).

추론 등급은 이 훅의 대상이 아니다 — Claude Code의 Agent 도구는 `effort`
파라미터를 노출하지 않으며(실측 2026-08-03: `tool_input` 키는 description·
prompt·subagent_type·model·run_in_background), 서브에이전트는 부모 세션의
등급을 상속한다.

스펙: docs/specs/2026-08-03-tier-gate-hook.md
결정: docs/adr/040-tier-gate-inversion-lightweight-ban.md (ADR 037을 대체)
회귀 테스트: .agents/hooks/tier-gate_test.py (수정 시 반드시 통과)
"""
import json
import os
import re
import sys

try:
    from _common import read_lightweight_models, utf8_stdio
except Exception:  # _common 유실·손상 시에도 훅은 살아야 한다(fail-open)
    def utf8_stdio():
        pass

    def read_lightweight_models(base):
        return set()  # 판정 입력 없음 — 차단하지 않는 방향

BLOCK_EXIT = 2  # PreToolUse: 도구 호출 차단 + stderr를 모델에게 전달
AGENT_TOOLS = ("Agent", "Task")  # 실측: tool_name은 "Agent"(matcher "Task"도 발화)
OVERRIDE = "[light-ok]"
# **우회가 닿지 않는 티어.** 사용자 전역 정책은 조항이 둘이다 — 경량 예외는
# "사용자가 명시적으로 빠르게/가볍게를 요청한 경우"이지만, 검증·리뷰·최종
# 확인은 그와 **별도로 '절대 금지'**다(false negative가 완료된 작업을
# 재작업시킨다). 표식을 티어 판정 앞에 두면 그 절대 금지가 한 단어로 풀린다
# (독립 검증 2026-08-04 F1 — `reviewer`+경량+표식이 실측으로 통과했다).
# 에이전트 정의도 예외 없이 적혀 있다: reviewer.md·integrator.md는 "never"·
# "absolutely forbidden"이라 하고 어떤 우회도 달지 않는다.
NO_OVERRIDE_TIERS = frozenset({"design"})
_TIER_RE = re.compile(r"^tier:\s*([A-Za-z_-]+)\s*$", re.MULTILINE)
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def matches(name, model):
    """경량 목록 항목이 모델 문자열에 **낱말 경계로** 나타나는가(소문자 가정).

    맨 부분 문자열이면 다른 벤더의 등급명을 오차단한다 — 목록에 `mini`를
    적으면 `gemini-2.5-pro`가 걸리고, 한 글자 항목은 사실상 전 발행을 막는다
    (독립 검증 2026-08-04 F2, 둘 다 실측). 모델 ID는 하이픈·점으로 끊기므로
    영숫자 경계만 요구하면 별칭(`haiku`)과 전체 ID(`claude-haiku-4-5-…`)를
    함께 잡으면서 낱말 내부의 우연한 일치는 배제된다.
    """
    return re.search(r"(?:^|[^a-z0-9])%s(?:[^a-z0-9]|$)" % re.escape(name),
                     model) is not None


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


def message(subagent_type, tier, model, hit, overridable):
    tail = (
        f"사용자가 명시적으로 \"빠르게/가볍게\"를 요청한 경우에만 발행 프롬프트에 "
        f"`{OVERRIDE}`를 넣어 다시 발행하세요."
        if overridable else
        f"**이 티어에는 우회가 없습니다** — `{OVERRIDE}`를 넣어도 통과하지 않습니다. "
        "경량 예외는 일반 작업에만 있고 검증·리뷰·최종 확인은 사용자가 요청해도 "
        "절대 금지이기 때문입니다."
    )
    return (
        f"[tier-gate] `{subagent_type}`({tier} 티어)를 경량 모델 `{model}`로 "
        f"발행하려 합니다 — REGISTRY.md 「경량 모델」 절이 `{hit}`을(를) 그 등급으로 "
        "기록해 두었습니다. 사용자 전역 정책은 경량 모델을 검증·리뷰·최종 확인에서 "
        "**절대 금지**하고(false negative가 완료된 작업을 재작업시킵니다), 루트 "
        "AGENTS.md 9절도 같은 금지를 못박습니다. **`model`을 빼고 다시 발행하면 "
        "부모 세션 모델을 상속하며, 그 경로는 경량에 닿지 않습니다** — 9절 표에서 "
        "이 티어의 기준을 읽고 상위·표준 중에서 고르거나, 지정하지 않는 것이 "
        f"기본값입니다. {tail}"
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
        if not model:
            return 0  # 미지정 = 상속. 상속은 경량에 닿지 않는 안전 기본값이다
        normalized = str(model).strip().lower()
        # 파일 판독은 여기서부터다. `model`을 지정하지 않은 발행이 압도적이므로
        # 매 발행마다 정의와 REGISTRY.md를 읽지는 않는다.
        base = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        subagent_type = tool_input.get("subagent_type")
        tier = read_tier(base, subagent_type)
        if not tier:
            return 0  # 티어 미선언·판독 실패는 9절 관장 밖(fail-open)
        hit = next((name for name in read_lightweight_models(base)
                    if matches(name, normalized)), None)
        if not hit:
            return 0  # 경량 목록에 없는 모델·절 부재 — 판정 대상이 아니다
        # **우회 판정은 티어를 안 뒤에 한다.** 앞에 두면 절대 금지 티어까지
        # 표식 한 줄로 열린다(독립 검증 F1).
        overridable = tier.strip().lower() not in NO_OVERRIDE_TIERS
        if overridable and OVERRIDE in str(tool_input.get("prompt") or ""):
            return 0  # 사용자 명시 요청 — 9절 경량 예외가 닿는 티어다
        print(message(subagent_type, tier, model, hit, overridable), file=sys.stderr)
        return BLOCK_EXIT
    except Exception:
        return 0  # fail-open — 게이트 자체의 결함이 작업을 막지 않는다


if __name__ == "__main__":
    sys.exit(main())
