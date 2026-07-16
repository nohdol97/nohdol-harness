---
name: team-review
description: Review code diffs, PRs, specs, or harness changes with a size-scaled reviewer team - single reviewer agent for small diffs, perspective fan-out (correctness, security, tests-vs-spec, convention, performance) with an integrator severity gate for medium and large ones. Judges against the spec's completion criteria (SDD, root AGENTS.md section 13). Use when the user says 리뷰해줘, 코드 리뷰, PR 검토, 검증해줘, review this. Re-run keywords - review, team-review, 리뷰, 코드 리뷰, 검토, 검증.
---

# team-review — 규모 스케일링 팀 리뷰

## 왜 이 스킬인가

리뷰어 한 명은 자기 관점의 결함만 본다 — 정확성을 보는 눈은 시크릿 유출을 놓치고, 스타일을 보는 눈은 테스트 공백을 놓친다. 이 스킬은 리뷰를 **독립 관점들로 분해해 병렬로 보게 하고, 통합 게이트로 걸러서** 한 사람의 사각지대가 최종 판정에 남지 않게 한다. 단, 팀은 공짜가 아니다 — **작은 diff에 팀을 띄우는 것은 낭비**이므로 규모로 모드를 고른다.

## 판정 기준 (고정)

- **스펙 대비 판정**: 대상 작업에 스펙(`docs/specs/`)이 있으면 그 **완료 기준이 판정 기준**이다(루트 AGENTS.md 13절). 스펙이 없으면 그 사실 자체를 발견 사항으로 기록한다(13절 위반 — 사소한 수정이 아닌 한).
- **증거 없는 지적 제외**: 모든 발견은 위치(file:line)와 근거를 가진다 — integrator 게이트 5원칙(`.agents/agents/integrator.md` 2절)을 따른다.
- 리뷰어는 수정하지 않는다(reviewer 에이전트 원칙). 수정은 별도 구현 단계로.

## Phase 0 — 범위 산정과 모드 선택

대상(diff·PR·스펙 문서·하네스 변경)의 변경 파일 수와 위험도(가드레일 3절 해당 여부, 인프라·보안 관련)를 센 뒤:

| 모드 | 기준 | 구성 |
|---|---|---|
| **단독** | 변경 파일 ≤5, 위험도 낮음 | reviewer 에이전트 1명 (팀 오버헤드 > 가치) |
| **팀** | 변경 파일 6+ 또는 위험도 높음(인프라·보안·크로스 프로젝트) — 임계 단일 원본: orchestrate Phase 0-1 판정 표 | 아래 관점 팬아웃 + integrator |

경계가 애매하면 단독으로 시작하고, 단독 리뷰어가 "범위 초과"를 보고하면 팀으로 승격한다.

## 팀 모드 — 관점 팬아웃 (orchestrate 위임)

팀 역학(생성·큐·team-log·종료)은 **orchestrate 스킬의 B. 서브에이전트 모드**를 그대로 쓴다 — 리뷰어 간 통신이 불필요한 독립 병렬 수집이기 때문이다. 이 스킬이 정하는 것은 관점 축과 통합 기준뿐이다.

**관점 축** (대상에 맞는 것만 선발, 3~5개 — reviewer 에이전트를 관점별 프롬프트로 재사용):

| 관점 | 보는 것 |
|---|---|
| 정확성 | 로직 결함, 엣지 케이스, 스펙 요구사항(R번호) 대비 구현 누락 |
| 테스트 | 스펙 완료 기준(C번호)이 전부 테스트로 존재하는가, 실패 케이스 커버 (13절 TDD) |
| 보안 | 시크릿 평문, 입력 검증, 권한 — 가드레일 3절 위반 |
| 규약 | 하네스 규칙·커밋 컨벤션·문서 형식(doc-writer 템플릿) 준수 |
| 성능 | 명백한 비효율(N+1, 불필요 반복) — 추측성 최적화 제안 금지 |
| 단순성/과설계 | **비자명 로직 diff에만 선발** — 무엇을 지울 수 있나만 본다(정확성·보안·성능과 분리). 태그 5종: `stdlib`(표준 라이브러리 재구현), `native`(플랫폼·의존성 중복), `yagni`(단일 구현 추상화·미사용 설정), `delete`(죽은 코드·투기적 기능), `shrink`(더 짧게). 발견은 `L<line>: <tag> <what>. <replacement>.` 형식, 리포트 끝에 `net: -<N> lines possible`(없으면 `Lean already`). 판정 기준은 루트 AGENTS.md 16절 코드 최소주의 — 단, 16절 예외 영역(검증·에러 처리·보안·명시 요청 기능)은 삭제 대상이 아니다 |
| UX·접근성 | UI 변경 diff에만 선발 — 접근성(WCAG 대비, 터치 타깃 크기, 키보드 내비게이션, ARIA), 사용자 안전 장치(자동저장·실행취소·에러 복구 UX). 기준은 대상 프로젝트 하네스·사용자 전역 정책의 접근성 요구 |

각 리뷰어 프롬프트에 필수 포함: 대상 프로젝트 하네스(`.agents/projects/<이름>/AGENTS.md`) 읽기 지시, 스펙 경로, 출력 경로 `_workspace/<작업명>/phase1_reviewer-<관점>_report.md`(doc-writer 작업 리포트 템플릿 — **영어**, 루트 15절. integrator 최종 verdict와 사용자 보고는 한국어). 리뷰어·integrator는 **design 티어**이므로 Agent 호출 시 `model`을 9절 표에 따라 최고 성능 모델로 지정한다(orchestrate 티어 적용 규칙 — 미지정 시 세션 모델 상속으로 티어 정책이 무시된다).

**동시 발행 (필수)**: 관점 리뷰어들은 서로의 결과에 의존하지 않으므로 **전원을 한 응답(같은 턴)에 동시 발행**한다(orchestrate B모드 동시 발행 규약). 정확성 리뷰가 끝나기를 기다렸다가 테스트 리뷰를 시작하는 것은 직렬 퇴화이며 규약 위반이다 — 순차가 허용되는 유일한 지점은 모든 리뷰가 끝난 뒤의 integrator뿐이다(팬인은 본질적으로 리뷰 완료에 의존).

**통합**: integrator가 게이트 5원칙으로 병합 → `phase2_integrator_verdict.md`. 최종 보고는 orchestrate 고정 형식(must-fix 수·위치 / should-fix 수 / 리포트 경로).

## 단독 모드

reviewer 에이전트 1명이 위 관점 축을 체크리스트로 순회하고, 같은 리포트 형식으로 `_workspace/<작업명>/phase1_reviewer_report.md`에 저장한다. 게이트 원칙(증거 없는 지적 제외, 심각도 배치)은 동일 적용.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 사각지대 | 리뷰어 1명의 관점 편향이 최종 판정에 그대로 | 관점 분해 + 독립 병렬 + 게이트 |
| 판정 기준 | 취향·인상 기반 리뷰 | 스펙 완료 기준 대비 재현 가능 판정 |
| 비용 | 모든 리뷰에 같은 무게 | 규모 스케일링 — 소규모는 단독, 대규모만 팀 |
| 노이즈 | 증거 없는 지적 혼입 | 게이트에서 제외 |
