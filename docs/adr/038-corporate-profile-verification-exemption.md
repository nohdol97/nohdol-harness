# ADR 038 — 사내 프로필의 검증 목적 발행 면제 (review-gate)

- **날짜**: 2026-08-03
- **상태**: **부분 대체(→042)** — **2026-08-07에 [ADR 045](045-corporate-profile-dispatch-restored.md)가 042와 함께 이 ADR도 폐기했다가 같은 날 [ADR 046](046-corporate-profile-dispatch-block-restored.md)이 철회해 둘 다 되살렸다**(비용 판정이 하루 안에 두 번 뒤집혔다). 아래 상태 설명은 그 왕복 이후에도 그대로 유효하다. — 차단 **범위**와 우회 표식은 [ADR 042](042-corporate-profile-dispatch-block.md)가 대체했다(검증 축 → 발행 축 전체, `[review-ok]` 폐기, 훅 개명 `review-gate.py`→`dispatch-gate.py`). **구조는 그대로 유효하다**: 발행 시점 강제, 프로필을 판정 입력으로 삼는 것, 메인 루프 대체 + 면제 명시 기록, 그 기록을 붙잡는 단계(PR 본문 `독립 검증` 줄·하네스 변경 이력 행), fail-open 방향. 아래 「변경 내용」 1·3·4항은 시점 기록이며 현재 규칙이 아니다.
- **관련**: AGENTS.md 5절(설치처 프로필)·8절(사내 일일 점검 off 선례)·13절, ADR 012(설치처 프로필과 대기 큐), ADR 037(발행 지점 강제의 선례), ADR 029·031(Codex 훅 파리티), 스펙 `2026-08-03-review-gate-hook`

## 변경 내용

1. 설치처 프로필이 `사내`일 때 **검증 목적 서브에이전트 발행을 끈다** — `reviewer`, `team-review` 관점 팬아웃, `infra-specialist` 리뷰 모드, 그리고 **리뷰 리포트를 모으는** `integrator`. 검증과 무관한 fan-in(`project-status` 2절의 상태 아티팩트 취합 등)은 대상이 아니다.
2. 빈자리는 **메인 루프의 자체 검증 + 명시 기록**이 메운다. 13절 2항의 증거 4종(명령·관측 출력·기준 충족 근거·미검증 범위)은 그대로 요구되며, 산출물에 **독립 검증이 프로필 면제로 생략됐다**는 한 줄을 남긴다. **그 기록을 붙잡는 단계를 함께 만든다** — PR 본문 템플릿의 `독립 검증` 줄이고, `branch-workflow` 마무리 5가 그 줄 없이 PR을 열지 않는다. **이 줄은 두 프로필 모두에 요구된다**(개인에서는 이미 일어난 검증을 적는 것뿐): 면제 쪽만 지우면 "줄이 없다 = 면제다"가 되어 조용한 생략과 다시 구분되지 않는다. 하위 프로젝트 PR에 새 차단 의무가 하나 붙는다는 뜻이므로 여기 명시한다.
3. **사용자가 명시적으로 리뷰를 요청하면 실행한다** — 8절의 "사내에서 일일 자동 실행은 off, 명시 요청은 실행"과 같은 형태다.
4. 발행 시점 강제는 PreToolUse 훅 `.agents/hooks/review-gate.py`가 맡되 **`reviewer` 타입 하나만 막는다.** 훅이 볼 수 있는 것은 타입이고 규칙이 끄는 것은 의도인데, 둘이 1:1인 타입이 그것뿐이기 때문이다(한계 절). 우회 표식은 `[review-ok]`이며, **사용자 요청이 있은 뒤에만** 붙인다(`[no-test]`·`[secret-ok]`와 같은 계열).
5. 개인 설치처의 동작은 바뀌지 않는다. 미상·판독 실패도 통과이므로 **fail-open 방향이 "검증이 돌아간다"** 쪽이다.

## 대상

`.agents/hooks/review-gate.py`(신설), `.agents/hooks/review-gate_test.py`(신설), `.agents/hooks/_common.py`, `.agents/hooks/_common_test.py`, `.agents/hooks/harness-review-reminder.py`, `.agents/hooks/harness-review-reminder_test.py`, `.agents/hooks/integrity-check.py`, `.agents/hooks/integrity-check_test.py`, `.claude/settings.json`, `.codex/config.toml`, `AGENTS.md`(§7-6·§9·§13), `AGENTS.ko.md`, `CLAUDE.md`, `.agents/skills/orchestrate/SKILL.md`, `.agents/skills/team-review/SKILL.md`, `.agents/skills/branch-workflow/SKILL.md`, `.agents/skills/metaskill/SKILL.md`, `.agents/skills/metaskill/references/patterns.md`, `.agents/skills/tool-eval/SKILL.md`, `.agents/skills/doc-writer/references/templates.md`, `.agents/skills/README.ko.md`, `.agents/agents/implementer.md`, `.agents/agents/infra-specialist.md`, `.agents/agents/README.ko.md`, `README.md`, `docs/README.md`, `docs/specs/2026-08-03-review-gate-hook.md`, `docs/harness-changelog.md`

> 목록은 `git diff --cached --name-only`로 뽑아 집합 대조했다(29건 중 이 파일 자신만 제외 — 공통 규칙 11의 유일한 면제). 초안은 `_common_test.py`를 손대지도 않은 채 올리고 `CLAUDE.md` 등 6건을 빠뜨려 독립 검증에 걸렸다.

## 사유

검증 발행 1회의 실측 비용은 **약 100k 토큰과 수 분**이다(metaskill 「검증 비례성」이 인용하는 2026-07-17 세션 reviewer 6회 평균). 개인 설치처에서는 이 값이 타당하지만 **사내 설치처에서는 감당되지 않는다**(사용자 판정 2026-08-03).

`orchestrate`가 "자기검증 금지는 13절 보증의 본질이며 불변"이라고 적어 둔 규칙을 이 ADR이 조건부로 만든다. 그 규칙이 틀려서가 아니라, **비용을 낼 수 없는 설치처에서는 그 규칙이 지켜지지 않고 지켜지지 않았다는 사실도 남지 않기 때문**이다. 명시적으로 끄고 기록을 요구하는 편이, 암묵적으로 건너뛰어 산출물이 검증된 것처럼 읽히는 상태보다 낫다.

**규칙 분기만으로 처리하지 않은 이유는 ADR 037이 이미 실측했다.** 9절 티어 표는 선언 이래 적용된 적이 없었고, 원인은 발행 지점에 장치가 없었다는 것 하나였다. 같은 형태의 의무(발행 때마다 판정해야 하는 규칙)를 문서에만 두면 같은 결과가 나온다. 반대로 발행 지점 처방은 이 하네스에서 실효가 확인된 위치다(2026-07-17 에이전트 타입 리마인더).

지식 소스 조회(7절 8항)에서 얻은 설계 축 하나 — **쓸모가 사라진 실행 하네스는 가만히 있지 않고 비용·지연을 계속 발생시킨다** — 는 "안 쓰면 그만"이라는 처리를 배제하는 방향으로만 반영했다. 출처가 미검증 영상이라 근거로는 쓰지 않는다.

## 결정

| 항목 | 결정 | 근거 |
|---|---|---|
| 발동 조건 | REGISTRY.md 「설치처 프로필」 = `사내` | 프로필의 단일 출처. 8절이 이미 같은 입력으로 분기한다 |
| 규칙의 차단 범위 | 검증 목적 발행 전부(reviewer·관점 팬아웃·리뷰 fan-in integrator·infra-specialist 리뷰 모드) | 비용은 design 티어 검증 발행 묶음에서 나온다. reviewer 하나만 끄면 나머지로 새어 절감이 안 된다(사용자 선택) |
| 훅의 차단 범위 | `reviewer` 타입 하나 | 훅은 타입만 볼 수 있다. `integrator`·`infra-specialist`는 검증 아닌 용도가 각각 있어, 타입으로 막으면 `project-status`가 사내에서 통째로 죽는다 — 규칙이 넓고 장치가 좁은 것은 감수하되 그 간극을 문서에 적는다 |
| 빌드 측 발행 | 대상 아님 | 사용자가 지목한 비용 축이 검증이다. implementer를 함께 끄면 orchestrate의 3파일 위임 규칙까지 무너진다 |
| 대체 수단 | 메인 루프 자체 검증 + 면제 명시 기록 | 독립성은 잃지만 증거는 남는다. 기록이 없으면 면제와 묵시적 생략이 사후에 구분되지 않는다 |
| 명시 요청 | 실행한다 | 비용을 사용자가 그 자리에서 승인한 상태다. 8절 선례와 같은 형태 |
| 강제 위치 | PreToolUse 훅 + 규칙 분기 | 규칙만으로는 발행 시점에 강제되지 않는다(ADR 037 실측) |
| 실패 방향 | fail-open = 검증이 돌아간다 | 판독 실패가 검증을 없애는 쪽으로 떨어지면 안 된다. tier-gate와 방향이 반대인 이유 |

## 한계

- **훅이 규칙보다 좁다 — 두 축은 규칙만으로 관장한다.** `infra-specialist` 리뷰 모드와 리뷰 fan-in `integrator`는 같은 타입이 비리뷰 용도로도 쓰여 `subagent_type`만으로 구분되지 않는다. 초안은 `integrator`를 타입 차단에 넣고 있었고 **독립 검증 2인이 각각 같은 결함으로 지적했다** — 사내에서 `project-status` 2절이 통째로 죽고 정당한 우회가 없었다. 훅 주석이 "integrator는 리뷰 리포트 fan-in 전용"이라 단언한 것은 그 스킬을 열지 않고 쓴 성격 규정이다(metaskill 공통 규칙 14ⓑ).
- **로스터 밖 타입(`general-purpose` 등)으로 리뷰를 시키면 통과한다.** tier-gate와 같은 구멍이며 같은 이유로 수용한다.
- **우회 표식은 게이트 대상이 쥐고 매칭도 느슨하다.** `[review-ok]`를 붙이는 주체가 세션 자신이고, 인라인된 diff 안의 같은 문자열도 통과시킨다. 기계적 보증이 아니라 **기록이 남는 우회**라는 점이 값이며, 실패 방향이 안전한 쪽(리뷰가 돌아간다)이라 수용한다.
- **차단 경로가 실환경에서 관측되지 않았다.** 이 설치처는 `개인`이라 회귀 테스트의 임시 REGISTRY.md로만 판정했다. 실사용 확인은 사내 설치처의 첫 사용 시점이다.
- **품질 저하는 감수한 비용이다.** 사내 산출물은 독립 검증 없이 PR로 간다. 이 ADR이 그 상태를 문서화하는 것이지 없애는 것이 아니다.
