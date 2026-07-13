---
name: release
description: "Post-merge release workflow - verify the merged state, draft a deploy runbook (doc-writer template), execute each mutating step only with explicit user confirmation (root guardrail 3), verify the deployment, then close the work-tracker issue. Branches per project type: web/backend via k8s GitOps, Flutter app via store submission. Use when the user says 배포해줘, 릴리스, 배포 준비, deploy this, release. Re-run keywords - release, deploy, rollout, 배포, 릴리스, 롤백."
---

# release — 머지 이후 배포·릴리스 워크플로우

## 왜 이 스킬인가

branch-workflow는 PR 생성에서 끝난다 — 머지(사용자) 이후의 배포·검증·마무리는 절차가 없어 세션마다 즉흥으로 처리됐다. 배포는 3절 가드레일의 핵심 대상(실수의 반경이 실행 중인 시스템)이므로, 즉흥 처리가 가장 위험한 단계가 절차 없이 남아 있으면 안 된다. 외부 스킬(gstack land-and-deploy 등)은 이 하네스의 가드레일(dev 포함 예외 없는 확인)·k8s 규약(컨텍스트 명시, 선언적 우선)을 모른다 — CLAUDE.md 스킬 우선순위에 따라 배포는 이 스킬이 관할하고, 외부 도구는 검증 단계의 보조로만 쓴다.

## Phase 0 — 사전 조건 (반드시 먼저)

1. **대상 식별**: REGISTRY.md에서 프로젝트를 식별하고 하네스(`.agents/projects/<이름>/AGENTS.md`)를 읽는다 — 프로젝트별 배포 규약(환경 이름·승인 절차)이 있으면 그것이 우선한다.
2. **머지 상태 확인**: 배포 대상 변경이 main에 머지되어 있는지 확인한다. 미머지 PR이면 중단하고 branch-workflow 마무리 절차(머지는 사용자)를 안내한다 — 브랜치에서 직접 배포하지 않는다.
3. **검증 상태 확인**: 테스트·빌드 통과와 리뷰 판정(team-review 통과 여부)을 확인한다. 실패 상태로 배포를 시작하지 않는다.

## Phase 1 — 배포 계획 (런북 초안)

**doc-writer 런북 템플릿**(사전 조건/절차/검증/롤백)으로 이번 배포의 계획을 작성해 사용자에게 먼저 보인다. 규모가 크면 infra-specialist에게 위임한다(orchestrate 판정). 프로젝트 타입별 분기:

| 타입 | 절차 골격 |
|---|---|
| 웹·백엔드 (k8s) | 이미지 태그 확정 → 매니페스트 갱신(선언적 우선 — `kubectl edit/patch` 금지) → GitOps 반영 → 롤아웃 관찰. 모든 kubectl에 `--context`·`-n` 명시 |
| 앱 (Flutter 등) | 버전·빌드 넘버 범프 → 릴리스 빌드 → 스토어 제출(제출 자체가 외부 발행 — 사용자 확인) → 심사 추적은 work-tracker 이슈로 |
| 기타 | 프로젝트 하네스의 배포 절차. 없으면 사용자 인터뷰로 확정하고 하위 AGENTS.md에 기록 제안 |

**롤백 절차 없는 계획은 계획이 아니다** — 런북 템플릿의 롤백 절이 비어 있으면 Phase 2로 넘어가지 않는다(불가하면 "롤백 불가 — 대안" 명시).

## Phase 2 — 실행 (⚠️ 단계별 사용자 확인)

- **변경 계열 명령(`apply`·배포 트리거·스토어 제출·마이그레이션)은 실행 직전 단계마다 사용자 확인**을 받는다 — dev 환경 포함 예외 없음(3절, 2026-07-12 확정). 일괄 승인으로 묶지 않는다: 앞 단계의 결과가 뒤 단계의 전제를 바꿀 수 있다.
- 각 단계의 실행 명령과 실제 출력을 기록한다(`_workspace/<작업명>/phase2_{실행 주체}_release-log.md` — 4절 네이밍 규약, 실행 주체는 leader 또는 infra-specialist) — 장애 시 troubleshooter의 입력이 된다.
- 단계 실패 시 즉시 중단하고 런북의 롤백 절차를 **사용자 확인 후** 실행한다. 실패 상태에서 다음 단계를 강행하지 않는다.

## Phase 3 — 배포 후 검증

- 런북의 검증 절을 실행한다: 헬스체크, 핵심 사용자 플로우, 로그의 신규 에러 유무.
- 웹이면 외부 도구(gstack browse·canary)를 **이 단계의 보조 도구로** 활용할 수 있다 — 관할은 이 스킬, 도구는 수단(CLAUDE.md 스킬 우선순위 원칙).
- 검증 실패 시 결과를 보고하고 롤백 여부를 사용자에게 묻는다 — 자동 롤백하지 않는다(롤백도 변경이다).

## Phase 4 — 마무리

1. work-tracker 등록 작업이면 이슈에 배포 결과 코멘트 후 종료(또는 앱 심사 추적으로 전환).
2. 릴리스 노트·태그·CHANGELOG는 프로젝트 규약을 따른다(없으면 생성을 제안만 — 무단 도입 금지).
3. 배포 요약(무엇을·어디에·검증 결과·롤백 여부)을 사용자에게 보고한다.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 배포 절차 | 세션마다 즉흥 — 가장 위험한 단계가 무절차 | 런북 초안 → 단계별 확인 → 검증 고정 |
| 가드레일 | 외부 스킬(land-and-deploy)로 새면 확인 규칙 무시 | 변경 단계마다 사용자 확인, dev 포함 예외 없음 |
| 롤백 | 장애 후 즉석에서 궁리 | 배포 전에 롤백 절차 확정 (없으면 실행 불가) |
| 추적 | 배포 기록이 어디에도 없음 | 실행 로그 + work-tracker 이슈로 영속 |
