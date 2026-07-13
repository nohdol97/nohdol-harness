# ADR 011 — 표준 로스터 확장 (4종 → 7종: architect·troubleshooter·infra-specialist)

- **날짜**: 2026-07-13
- **변경 내용**: 표준 팀원 로스터에 architect(design — 스펙 초안·작업 분해·인터페이스 설계), troubleshooter(design — 근본 원인 조사, 수정 금지), infra-specialist(implement — k8s·AWS 매니페스트·IaC, 변경 명령은 사용자 확인)를 추가. orchestrate 로스터 표·하이브리드 스켈레톤 담당 표기, implementer의 "유일한 Edit 보유자" 서술을 "구현 계열(implementer·infra-specialist)"로 정정.
- **대상**: `.agents/agents/architect.md`·`troubleshooter.md`·`infra-specialist.md`(신설), `implementer.md`, orchestrate SKILL.md(로스터 표·스켈레톤), README
- **사유**: 사용자 승인(2026-07-13) — 인기 하네스(BMAD·Superpowers·Everything Claude Code·커뮤니티 로스터)의 에이전트 구성과 대조 검토 결과 채택. ADR 트리거 ④(구조적 결정) + 에이전트 수가 8개 기준선에 근접(7개).

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| architect 신설 | 하이브리드 스켈레톤 Phase ②(설계·합의)의 전담자. 스펙 초안(13절 SDD)·depends_on 분해·인터페이스 설계. Edit 미보유 | 5-Phase 스켈레톤 중 Phase ②만 전담 에이전트가 없었다(구조적 공백 — ADR 010의 후속). BMAD의 architect, 커뮤니티 planner에 대응 |
| troubleshooter 신설 | 재현→가설→검증→확정 원인 루프 전담. Iron Law(원인 확인 전 수정 금지)를 Edit 미보유로 도구 강제 | explorer(수집)와 reviewer(판정) 사이에 인과 확정의 주인이 없었다. Superpowers·gstack investigate의 조사 규율을 팀 조합 가능한 하네스 에이전트로 내재화 |
| infra-specialist 신설 | k8s·AWS 작성·진단·배포 계획. Edit 보유(매니페스트가 산출물), 변경 계열 명령은 예외 없이 사용자 확인 | 레지스트리에 인프라 프로젝트(ops 계열)가 있고 크로스 배포가 파이프라인 기본 패턴(references/k8s.md) — 도메인 특화의 선제 생성은 지연 원칙의 예외이나 사용자가 명시 승인 |
| Edit 보유 정책 정정 | "유일한 Edit 보유자(implementer)" → "구현 계열(implementer·infra-specialist)" | 매니페스트·IaC는 infra-specialist의 산출물 — 서술과 실제 tools가 어긋나면 로스터 표를 아무도 믿지 않게 된다 |
| 미채택: security-reviewer·test-writer·scribe | 각각 team-review 보안 관점(reviewer 재사용)·implementer TDD+tdd-gate 훅·doc-writer 스킬이 이미 커버 | 역할 중복 에이전트는 라우팅만 흐린다 — 관점은 프롬프트로, 형식은 스킬로 |
