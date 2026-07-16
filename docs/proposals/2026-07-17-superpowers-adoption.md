# 설계 제안: superpowers의 규율 착안을 이 하네스에 적용

- **상태**: 채택됨 (2026-07-17, 착안 3개 문서 이식 — 플러그인 통설치 기각) — 결정 근거 docs/adr/022
- **날짜**: 2026-07-17
- **분석 대상**: https://github.com/obra/superpowers (14스킬, 2026-07-17 main 기준)
- **적용 대상**: 이 루트 하네스(nohdol-harness)

## 1. 배경

superpowers는 "코딩 에이전트를 위한 완결된 소프트웨어 개발 방법론" 플러그인이다 — TDD·체계적 디버깅·설계 선행·증거 기반 검증 4원칙을 14개 조합형 스킬로 배송한다. "이 프로젝트에 넣으면 좋을까"라는 사용자 질문에서 출발해, 통설치 대신 하네스 대응물과 스킬 단위로 대조한 결과다(ponytail ADR 017·claude-mem ADR 018과 같은 채택 절차).

## 2. superpowers 분석

### 2.1 구성 (14스킬)
- **워크플로**: brainstorming → writing-plans → executing-plans → subagent-driven-development → requesting/receiving-code-review → finishing-a-development-branch (7단계 선형 파이프라인)
- **규율**: test-driven-development, systematic-debugging, verification-before-completion
- **보조**: dispatching-parallel-agents, using-git-worktrees
- **메타**: writing-skills, using-superpowers
- **집행 방식**: 세션 시작 훅으로 게이트웨이 스킬(using-superpowers) 전문 주입 — **강제는 전부 산문(프롬프트 수준)**

### 2.2 이 하네스와의 대조 (통설치를 기각한 이유)
- **집행 계층**: superpowers의 TDD·검증은 모델 준수 의존(그래서 스킬 절반이 합리화 방지 표). 이 하네스는 tdd-gate를 **git 훅**(도구 무관, 회귀 테스트 29건)에 둔다 — 더 강한 계층을 이미 보유.
- **비례 대응**: brainstorming의 HARD-GATE는 "todo 리스트·설정 변경 포함 모든 작업에 설계 승인"을 강제하는 고정 비용 파이프라인. 이 하네스는 orchestrate Phase 0(직접/단독/쌍/팀)·team-review 규모 스케일링으로 비용을 작업 크기에 비례시킨다 — 통설치는 이 판정을 우회시킨다.
- **트리거 충돌**: 14스킬의 트리거(implement·debug·review·TDD·plan)가 하네스 라우팅(orchestrate·troubleshooter·team-review·§13)과 전면 겹친다 — CLAUDE.md 스킬 우선순위 절이 차단하는 바로 그 유출 경로.
- **커버리지**: 멀티 프로젝트 라우팅(REGISTRY.md)·인프라 안전(admission pre-flight·파괴적 작업 확인)·자기 수축(신호 ④)·세션 영속(work-tracker)은 superpowers에 없음.
- **superpowers가 앞서는 지점**: 개별 스킬의 "합리화 내성" 글쓰기 — 규칙이 모델 압박에서 살아남도록 변명-반박 쌍·금지 문구·red flag를 열거하는 단련도. 이식 후보는 전부 여기서 나왔다.

## 3. 채택 설계 (문서 이식만 — 인프라·플러그인 없이)

### ① writing-skills의 압박 테스트 — 채택 → metaskill 스킬 공통 규칙 7
스킬 작성을 TDD로: **스킬 없이 서브에이전트가 실패하는 압박 시나리오(baseline·RED)를 먼저 관찰** → 관찰된 합리화 문구를 겨냥해 작성 → 같은 시나리오에서 준수 확인(GREEN) → 새 합리화 발견 시 구멍 막기.
- 공백: metaskill 완료 판정은 15항목 **정적** 체크리스트뿐 — "이 규칙이 실제 행동을 바꾸는가"를 행동으로 확인하는 단계가 없다.
- 범위 한정: **행동 규율 스킬·규칙**(게이트·금지·강제 절차)에만 필수 — 참조·절차형 스킬(명령 모음·템플릿)은 압박에 저항할 '행동'이 없어 대상이 아니다(16절 최소주의 — 규율이 노이즈가 되면 우회된다).

### ② verification-before-completion의 신선한 증거 규율 — 채택 → AGENTS.md 13절 2항 보강
완료·통과 주장의 증거는 **보고 직전에 실행한 검증 명령의 출력**뿐 — 이전 실행 결과·"통과할 것" 류 추정·부분 확인은 증거가 아니다. 서브에이전트의 success 보고도 diff·출력으로 독립 확인 후에만 완료 취급.
- 공백: §13은 "테스트 없이 완료 선언 금지"까지만 — 증거의 **신선도**와 에이전트 보고의 독립 확인이 미명시라, 낡은 실행 결과로 완료를 주장하는 경로가 열려 있었다.
- 배치: 단일 원본 §13에 1문장 — implementer(변경 요약에 검증 결과)·reviewer(증거 필수)·orchestrate(검증 필수 규칙)가 이미 이 원칙을 참조하는 구조라 전파는 자동이다.

### ③ receiving-code-review의 수신 규율 — 채택 → implementer 4절 보강
리뷰 피드백은 감정 수행이 아니라 기술 평가다: ⓐ 수정 전 각 지적을 코드베이스 현실에 대조해 검증(형식적 동의·검증 없는 즉시 수용 금지) ⓑ 불명확 항목이 하나라도 있으면 부분 반영 없이 **전체 중단 후 질문**(항목 간 연관 — 부분 이해는 오구현) ⓒ 미수용 항목은 기술적 사유 회신.
- 공백: implementer 4절에 뼈대("근거 확인 후 수정, 미수용 사유 회신")는 있었으나 ⓐ의 검증-선행 원칙과 ⓑ의 전체 중단 규칙이 없었다. 사용자가 가져오는 외부 리뷰(PR 코멘트)도 orchestrate 게이트를 거쳐 implementer로 라우팅되므로 같은 규율이 적용된다.

## 4. 비목표 (기각한 것과 이유)

- **플러그인 통설치 — 기각.** 2.2의 트리거 충돌·비례 대응 상실. 외부 스킬의 프로젝트 설치는 §11 위반(`.claude/`는 심링크 — 설치물이 추적 저장소에 커밋됨)이기도 하다.
- **brainstorming — 기각.** 전수 설계 강제(HARD-GATE)가 Phase 0 비례 대응과 정면 충돌. 설계 선행 자체는 §13 SDD + architect가 이미 담당.
- **writing-plans·executing-plans·subagent-driven-development·dispatching-parallel-agents — 기각.** orchestrate(작업 큐 depends_on·P2P·하이브리드)와 architect가 상회. superpowers 쪽은 선형 디스패처.
- **systematic-debugging — 기각.** troubleshooter가 동일 원칙("no fix without root cause")을 이미 명문화.
- **test-driven-development — 기각.** §13 + tdd-gate git 훅이 더 강한 집행 계층. 그쪽 산문 강제를 들여올 이유 없음.
- **requesting-code-review — 기각.** team-review(관점 팬아웃 + integrator 게이트)가 상회(그쪽은 리뷰어 1명 호출).
- **finishing-a-development-branch — 기각.** branch-workflow가 동일 절차.
- **using-git-worktrees — 기각.** Claude Code 네이티브 worktree 격리(Agent isolation)로 충분.
- **using-superpowers — 기각.** 그쪽 스킬 체계 전용 메타, 무관.
- **합리화 방지 표의 전면 도입 — 기각.** 문체 기법으로는 유효하나 모든 규칙에 붙이면 비대만 키운다 — 모델 압박이 큰 고위험 규칙(가드레일 3절·tdd-gate류)에 필요해질 때 선택 적용(이번 ①~③ 문안에는 핵심 반박만 압축 반영).

## 5. 근거의 무게 (정직한 평가)

superpowers와 이 하네스는 같은 문제의식(모델의 자기 편향·완료 성급 선언·규칙 합리화)을 다른 계층에서 푼다 — 전자는 산문 단련, 후자는 구조(게이트·훅·독립 검증). 구조가 있는 쪽이 강하므로 시스템 이식은 무의미하고, 채택한 3개는 모두 **구조가 못 잡는 잔여 공백**(행동 검증 부재·증거 신선도·수신 태도)을 문장 몇 개로 메우는 저비용 보강이다. 셋 중 ①이 가장 실질적이다 — 하네스의 규칙 대부분이 "작성 후 정적 검증"에서 끝나는데, baseline 실패를 본 적 없는 규칙은 상상한 위반 지점을 막는다.

> 출처: 압박 테스트·신선한 증거·리뷰 수신 규율은 superpowers(github.com/obra/superpowers, MIT)에서 이식했다. 결정 근거·기각 항목은 docs/adr/022.
