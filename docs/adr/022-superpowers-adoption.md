# ADR 022 — superpowers 규율 착안 3건 이식 (압박 테스트 + 신선한 증거 + 리뷰 수신 규율)

- **날짜**: 2026-07-17
- **변경 내용**: superpowers(github.com/obra/superpowers, MIT — 14스킬)를 분석하고 **규율 착안 3개를 문서로만 이식**한다. ① 압박 테스트(metaskill 스킬 공통 규칙 7 — 행동 규율 스킬은 baseline 실패를 서브에이전트로 관찰한 뒤 작성·준수 확인), ② 신선한 증거 규율(AGENTS.md 13절 2항 — 완료·통과 주장의 증거는 보고 직전 실행한 검증 출력뿐, 에이전트 success 보고는 독립 확인 후 인정), ③ 리뷰 수신 규율(implementer 4절 — 검증 전 수용 금지·불명확 시 전체 중단 후 질문·미수용 사유 회신). **플러그인 통설치와 나머지 11스킬은 채택하지 않는다.**
- **대상**: AGENTS.md 13절, `.agents/skills/metaskill/SKILL.md`, `.agents/agents/implementer.md`, docs/proposals/2026-07-17-superpowers-adoption.md
- **사유**: 사용자 요청(2026-07-17 — superpowers 등 외부 스킬 도입 검토 → 비교·이식 후보 선별 → "3개 다 적용"). superpowers는 같은 문제의식(자기 편향·완료 성급 선언·규칙 합리화)을 **산문 단련**으로 풀고, 이 하네스는 **구조**(orchestrate 게이트·tdd-gate git 훅·reviewer 독립 검증)로 푼다 — 구조가 강하므로 시스템 이식은 무의미하나, 구조가 못 잡는 잔여 공백 3개는 문장 수준 보강으로 메울 가치가 있다.

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| ① 압박 테스트 채택 | 모델의 기본 행동을 바꾸려는 규율 스킬·규칙은 정적 체크리스트로 끝내지 않고, 스킬 없이 실패하는 baseline을 서브에이전트로 먼저 관찰 → 그 합리화를 겨냥해 작성 → 준수 확인(13절 TDD의 문서 적용). 참조·절차형 스킬은 대상 아님 | metaskill 완료 판정은 정적 15항목뿐 — baseline 실패를 본 적 없는 규칙은 실제 위반 지점이 아니라 상상한 위반 지점을 막는다. 범위 한정은 16절 최소주의(규율이 노이즈가 되면 우회된다) |
| ② 신선한 증거 규율 채택 | 완료·통과 주장 = 보고 직전 실행한 검증 명령의 출력. 이전 실행 결과·추정("통과할 것")·부분 확인 불인정. 서브에이전트 success 보고는 diff·출력으로 독립 확인 후에만 완료 취급 | 13절은 "테스트 없이 완료 선언 금지"까지만 — 증거 신선도와 에이전트 보고 독립 확인이 미명시라 낡은 결과로 완료를 주장하는 경로가 열려 있었다. 단일 원본 13절 1문장 배치로 implementer·reviewer·orchestrate에 자동 전파 |
| ③ 리뷰 수신 규율 채택 | 수정 전 각 지적을 코드베이스 현실에 대조 검증(형식적 동의·즉시 수용 금지), 불명확 항목이 하나라도 있으면 부분 반영 없이 전체 중단 후 질문, 미수용 항목은 기술적 사유 회신 | implementer 4절 기존 뼈대("근거 확인·사유 회신")에 검증-선행과 전체-중단이 없었다 — 틀린 지적의 무비판 수용과 부분 이해 오구현이 열린 경로. 외부 리뷰(PR 코멘트)도 orchestrate → implementer 라우팅으로 같은 규율 적용 |
| 플러그인 통설치 기각 | superpowers를 설치하지 않는다(전역·프로젝트 모두) | 14스킬 트리거가 하네스 라우팅(orchestrate·troubleshooter·team-review·§13)과 전면 충돌 — CLAUDE.md 우선순위 절이 차단하는 유출 경로. brainstorming HARD-GATE(전수 설계 강제)는 Phase 0 비례 대응과 정면 충돌. 프로젝트 설치는 §11 위반(심링크 경유 커밋) |
| 나머지 11스킬 기각 | writing-plans·executing-plans·subagent-driven-development·dispatching-parallel-agents(→orchestrate·architect 상회), systematic-debugging(→troubleshooter 동일 원칙), TDD(→13절+git 훅이 더 강한 계층), requesting-code-review(→team-review 상회), finishing-a-development-branch(→branch-workflow), using-git-worktrees(→네이티브 격리), brainstorming·using-superpowers | 전 항목 하네스 대응물이 동등 이상 — 상세 대조는 제안서 2.2·4절 |
| 문서로만 이식 | 훅·플러그인·코드 없이 규칙 문서 3곳에 문장 수준 반영 | 규칙의 유일 운반체는 문서다(12절). ponytail(ADR 017)·claude-mem(ADR 018)과 같은 원칙 — 배송 기계가 아니라 착안만 옮긴다 |

## 검증

- **분석·기각 상세**: `docs/proposals/2026-07-17-superpowers-adoption.md` (채택 3건 + brainstorming의 SKILL.md 원문을 직접 조회해 대조한 분석 — 제안서 본문은 그 요약).
- **적용 diff 독립 검증**: reviewer 에이전트 검증 통과 후 커밋(루트 하네스 품질 방침).
