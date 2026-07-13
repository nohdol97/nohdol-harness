---
name: project-status
description: Summarize the status of all registered projects in one report. Reads REGISTRY.md, fans out explorer agents per project (git state, recent activity, harness presence, stale registry rows), and integrates findings into a single must-know report. Use when the user says 프로젝트 상태, 전체 현황, 상태 요약, what changed across projects, or before planning cross-project work. Re-run keywords - status, overview, 현황, 상태 요약.
---

# project-status — 전체 프로젝트 현황 리포트

## 왜 이 스킬인가

멀티 프로젝트 관리 하네스에서 "지금 전체가 어떤 상태인가"는 가장 자주 필요한 질문이지만, 매번 즉흥으로 조사하면 프로젝트마다 보는 항목이 달라져 비교가 불가능하다. 이 스킬은 **같은 항목을 같은 방식으로** 수집해 한 장의 리포트로 만든다. 크로스 프로젝트 작업을 계획하기 전의 사전 정찰로도 쓴다.

## 절차

### Phase 0 — 사전 조건

- REGISTRY.md를 읽는다. **없으면 중단하고 harness-install을 안내한다**(설치 미완료).
- 레지스트리가 비어 있으면 "등록 프로젝트 없음"을 보고하고 끝낸다.
- `_workspace/project-status-<날짜>/`를 작업 디렉토리로 잡고, orchestrate의 **team-log 이벤트 계약**에 따라 이벤트를 기록한다(B 모드 포함).

### Phase 1 — 병렬 수집 (**실행 모드.** 서브에이전트)

레지스트리 행마다 explorer를 병렬 배치한다(orchestrate B 모드, 상한 10~20 — **전원을 한 턴에 동시 발행**, B모드 동시 발행 규약). 각 explorer의 고정 수집 항목:

1. git 상태: 독립 저장소 여부, 브랜치, 미커밋 변경, 최근 커밋 3건
2. 하네스: 루트 `.agents/projects/<이름>/AGENTS.md` 존재 여부와 지연 생성된 `skills/`·`agents/` 목록 (루트 AGENTS.md 12절 — 하네스는 프로젝트 디렉토리가 아니라 중앙에 있다). `project/<이름>/` 안에 하네스 파일이 있으면 우회 신호로 보고
3. 레지스트리 대조: 실제 디렉토리 구성이 레지스트리 행(스택·하위 구성)과 일치하는지
4. 특이사항: 근거 있는 것만 (빌드 산출물 비대, 방치 흔적 등)

출력: `phase1_explorer-<프로젝트명>_status.md`

### Phase 2 — 통합 (**실행 모드.** integrator 단독)

integrator가 게이트 원칙대로 통합하되, 이 스킬의 최종 리포트는 상태 보고이므로 섹션을 다음으로 고정한다:

- **주의 필요**: 미커밋 변경 방치, 레지스트리 불일치, 하네스 없음 등 근거 있는 이슈
- **프로젝트별 요약 표**: 이름 / git 상태 / 최근 활동 / 하네스 / 레지스트리 일치
- **권고**: metaskill·harness-review 연계 제안 (레지스트리 갱신, 하네스 생성 등)

### 최종 응답

사용자에게는 주의 필요 건수와 항목, 요약 표, 전체 리포트 경로만 보고한다.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 일관성 | 프로젝트마다 다른 항목 조사 → 비교 불가 | 고정 4항목 수집으로 비교 가능 |
| 신선도 | 레지스트리와 현실의 불일치가 조용히 누적 | 매 실행마다 레지스트리 대조 |
| 시간 | 프로젝트 수만큼 순차 조사 | explorer 병렬 팬아웃 |
