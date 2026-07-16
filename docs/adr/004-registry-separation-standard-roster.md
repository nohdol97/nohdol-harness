# ADR 004 — 레지스트리 분리(REGISTRY.md)와 표준 팀원 로스터 완성

> ⚠️ 이 중 "REGISTRY.md를 git으로 추적한다"는 결정은 **ADR 005로 대체**되었다(미추적 전환 — 설치처별 데이터). 나머지 결정(레지스트리 분리 자체, implementer·integrator 신설, orchestrate 로스터 재사용·게이트 단일 원본 이관)은 유효하다.

- **날짜**: 2026-07-12
- **변경 내용**: ① 프로젝트 레지스트리를 AGENTS.md 1절에서 루트 `REGISTRY.md`로 분리 ② implementer·integrator 에이전트 신설로 표준 팀원 로스터 4종 완성 ③ orchestrate 스킬 개정 — 표준 로스터 재사용 우선 원칙, 통합 게이트 단일 원본을 integrator.md로 이관.
- **대상**: AGENTS.md 1·5·7절, REGISTRY.md(신설), .agents/agents/(2종 추가), orchestrate SKILL.md, metaskill·harness-review·scaffold·k8s 참조 갱신, README
- **사유**: 사용자 확정(2026-07-12) — AGENTS.md는 공용 규칙이고, 어떤 프로젝트를 두는지는 하네스를 설치한 워크스페이스마다 다르므로 설치 환경별 데이터를 분리해야 한다.

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| 레지스트리 분리 | 공용 규칙(AGENTS.md)과 설치 환경별 데이터(REGISTRY.md) 분리. 레지스트리 갱신 의무·라우팅 근거 지위는 REGISTRY.md로 이동 | 하네스를 다른 워크스페이스에 설치할 때 AGENTS.md는 그대로 쓰고 REGISTRY.md만 새로 쓰면 된다 |
| 경로 규약은 잔류 | `project/<이름>/`·독립 저장소·`dev/` 비대상 규약은 AGENTS.md 1절 유지 | 규약은 설치처와 무관한 공용 규칙이다 |
| REGISTRY.md 추적 | gitignore하지 않고 추적 (각 설치처 저장소가 자기 레지스트리를 가짐) | 라우팅 근거가 버전 관리 밖에 있으면 이력·복구 불가 |
| 표준 로스터 4종 | explorer(수집)·implementer(구현)·reviewer(검증)·integrator(통합) | 6개 오케스트레이션 패턴의 범용 역할을 전부 커버. 도메인 특화 전문가는 하위 프로젝트 하네스의 몫 |
| 재사용 우선 | orchestrate는 표준 에이전트 재사용을 기본으로 하고, 즉석 정의는 도메인 특화에 한정. 같은 즉석 역할 3회 반복 시 승격 제안 | 매번 즉석 정의하면 팀원마다 규칙이 달라져 실행 예측 불가 |
| 게이트 단일 원본 | 통합 게이트 5원칙의 원본을 orchestrate에서 integrator.md 2절로 이관, orchestrate는 포인터만 유지 | 두 곳에 전문이 있으면 개정 시 반드시 어긋난다 |
| integrator 최소 권한 | tools에 Bash·Edit 제외 (Read/Glob/Grep/Write만) | 통합은 읽고 리포트 하나를 쓰는 일. 표준 로스터 중 유일하게 Bash가 없는 최소 화이트리스트(explorer·reviewer는 조회용 Bash 보유, implementer는 Edit까지 보유) |
