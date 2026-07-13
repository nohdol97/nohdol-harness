# CLAUDE.md

> **이 프로젝트의 모든 지침은 [AGENTS.md](AGENTS.md)를 읽어라.** AGENTS.md가 단일 원본이며, 이 파일은 포인터다.

## 하네스: 루트

- **목표**: 여러 하위 프로젝트(웹·앱·백엔드·k8s·AWS)를 담는 모노 워크스페이스의 공통 규칙·라우팅·오케스트레이션을 관리한다. 작업 전 반드시 루트 AGENTS.md와 대상 프로젝트의 AGENTS.md를 읽는다.
- **트리거**: **구현·수정·리팩토링 등 다단계 작업 지시 전반** 그리고 다중 프로젝트·팀 구성·병렬 작업 → `orchestrate`(Phase 0-1 팀 필요성 판정 — '직접 수행' 판정이면 즉시 반환하므로 가벼운 요청에도 부담 없음). 하네스 생성·개선·프로젝트 신설 → `metaskill`. **리뷰·검토·검증 요청("리뷰해줘", "코드 리뷰", "PR 검토") → `team-review`**(내장 review 대신 — 스펙 대비 판정·통합 게이트 포함). 문서·스펙·리포트·런북 작성 → `doc-writer`. 새 설치처 세팅·REGISTRY.md 부재 → `harness-install`. 세션을 넘는 작업의 등록·진행 기록·재개("작업 등록", "이어서 하자", "하던 작업 뭐였지") → `work-tracker`.
- **스킬 우선순위 (트리거 충돌 시)**: ① 요청이 특화 스킬 트리거에 맞으면 **특화 스킬이 orchestrate 게이트보다 우선**한다(리뷰→team-review, 문서→doc-writer, 하네스→metaskill 등) — 게이트는 특화 라우팅이 없는 구현·다단계 작업의 기본 경로다. ② 같은 트리거를 가진 **내장·플러그인·SuperClaude 스킬보다 하네스 스킬이 우선**한다 — 영어 요청도 동일: "implement/fix/build" → `orchestrate` 판정(sc:implement·investigate 아님), "debug/원인 조사" → `orchestrate` 판정 후 troubleshooter 배치(sc:troubleshoot·gstack investigate 아님), "설계/design" → orchestrate 판정 후 architect 배치(sc:design 아님), "deploy/배포/릴리스" → `release` 스킬 — 단계별 사용자 확인, infra-specialist 위임 가능(gstack land-and-deploy·setup-deploy·ship 아님), "create a PR"·"PR 만들어줘" → `branch-workflow`+doc-writer PR 템플릿(gstack ship 아님), "resume"·"이어서" → `work-tracker`(gstack checkpoint 아님), 리뷰 요청 → `team-review`(내장·gstack review 아님). 외부 스킬은 하네스 절차 안의 보조 도구로만 쓴다. 이유: 외부 스킬로 새는 라우팅은 하네스의 판정·템플릿·가드레일을 통째로 우회한다.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-12 | 초기 구성 | CLAUDE.md | 루트 하네스 구축, AGENTS.md 포인터 수립 |
| 2026-07-13 | 트리거 절에 team-review·doc-writer·harness-install 라우팅 추가 | CLAUDE.md | "리뷰해줘"가 내장 스킬·인라인 리뷰로 새는 실패 관찰 — 항상 로드되는 포인터에 라우팅 명시 |
| 2026-07-13 | 트리거 절에 work-tracker 라우팅 추가 | CLAUDE.md | 세션 영속 작업 추적 신설(14절, ADR 009) — 재개 요청이 라우팅되도록 포인터에 명시 |
| 2026-07-13 | orchestrate 트리거를 구현·다단계 작업 전반으로 확대 + 스킬 우선순위 절 신설(특화>게이트, 하네스>내장·플러그인·sc:*) | CLAUDE.md | orchestrate 범용 게이트화(ADR 010) — 판정 대상 요청이 스킬에 도달해야 하고, 트리거 확대로 생긴 내부 이중 매칭·외부 스킬 충돌(reviewer 검증 F3·F8~F10)은 항상 로드되는 포인터가 우선순위로 해소 |
| 2026-07-13 | 우선순위 매핑의 배포 항목을 release 스킬로 갱신 | CLAUDE.md | release 스킬 신설 — 배포 요청이 infra-specialist 단독 경유가 아니라 워크플로우(런북→확인→검증) 전체로 라우팅되어야 함 |
