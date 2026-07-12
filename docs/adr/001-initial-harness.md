# ADR 001 — 루트 하네스 초기 구성

- **날짜**: 2026-07-12
- **변경 내용**: 멀티 프로젝트 루트 하네스 초기 구축 (루트 AGENTS.md, CLAUDE.md 포인터, orchestrate 스킬, metaskill 스킬, 공용 `.agents/` 디렉토리 + `.claude/` 심링크, `_workspace/` gitignore)
- **대상**: 루트 워크스페이스 전체
- **사유**: harness-bootstrap-prompt.md에 따라, 여러 하위 프로젝트(웹·앱·백엔드·k8s·AWS)의 하네스를 일관되게 관리할 루트 골격이 필요.

## 확정된 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| 단일 원본 | AGENTS.md가 single source of truth, CLAUDE.md는 포인터 | 타 LLM CLI(Codex) 호환. 두 파일에 규칙이 중복되면 반드시 어긋난다 |
| 멀티 CLI | Claude Code + Codex 병행. `.agents/` 원본 + `.claude/agents`, `.claude/skills` 심링크 | 사용자 확정(2026-07-12). 같은 파일을 두 CLI가 보게 함 |
| 메타스킬 통합 | 신규 생성/개선을 하나의 metaskill로 통합, AGENTS.md 존재 여부로 내부 분기 | 두 스킬로 나누면 트리거 판단이 이중화됨 |
| 이력 이원화 | 변경 이력 테이블(경량 로그, AGENTS.md 하단) + ADR(구조적 결정, docs/adr/) | 역할 분리 — 모든 변경을 ADR로 쓰면 ADR이 로그가 되어 아무도 읽지 않음 |
| 위임 깊이 | 계층적 위임 최대 2단계 (총괄→팀장→실무자) | 깊이 증가 시 지연이 기하급수적으로 증가 |
| 진화 트리거 수치화 | 반복 요청 3회 / 반복 실패 2회 / 우회 관찰 1회 | "반복되면"이라는 모호한 기준은 실행되지 않음 |
| `_workspace/` | 루트 단일, 전체 gitignore (team-log.jsonl 포함 미보존) | 사용자 확정(2026-07-12). 세션 산출물은 하네스가 아님 |
| 티어→모델 매핑 | design=Opus, implement=Sonnet, explore=Sonnet. Haiku 원칙 금지 | 사용자 전역 정책 — Haiku는 검증 단계 false negative 위험 |
| 가드레일 | 파괴적 작업 전부 사용자 확인, 예외 없음 (dev 포함) | 사용자 확정(2026-07-12) |
| 커밋 컨벤션 | Conventional Commits + 프로젝트 스코프 (예: `feat(web):`) | 모노 워크스페이스에서 프로젝트 구분 필요 |
| 초기 범위 | 루트 하네스만 생성 (하위 프로젝트 없음) | 레지스트리가 비어 있음. 완벽주의 금지 — 단순하게 시작 |
