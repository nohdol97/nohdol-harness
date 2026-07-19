# 스펙: Codex 네이티브 custom-agent 어댑터

- 날짜: 2026-07-19 / 상태: 구현됨 (C5 인증 후 실발행 확인 대기)
- 관련: `AGENTS.md` 9~11절, `docs/adr/027-codex-agent-adapters.md`

## 배경

루트의 표준 팀원 7종은 `.agents/agents/*.md`에 정의되어 Claude Code와 하네스 스킬이 읽지만, Codex의 네이티브 custom agent 로더는 프로젝트의 `.codex/agents/*.toml`만 읽는다. 따라서 현재 Codex는 skill과 `AGENTS.md`는 네이티브로 발견하면서도 `architect`·`reviewer` 등 하네스 역할을 이름 기반 custom agent로 직접 로드하지 못한다.

## 목표

- 표준 팀원 7종을 Codex가 프로젝트 범위 custom agent로 발견한다.
- 역할 계약의 단일 원본은 계속 `.agents/agents/*.md`에 둔다.
- Codex 어댑터가 특정 모델명이나 중복 역할 본문을 소유하지 않게 한다.

## 비목표

- 기존 Markdown 에이전트 정의를 TOML로 이전하지 않는다.
- 구체 모델명·추론 강도·sandbox 설정을 어댑터에 고정하지 않는다.
- Claude Code의 `tools` 화이트리스트를 Codex TOML이 기계적으로 재현한다고 주장하지 않는다. Codex에서는 부모 세션의 도구·sandbox와 Markdown 역할 계약이 적용된다.
- 표준 팀원의 역할·경계·티어 자체는 변경하지 않는다.

## 요구사항

- **R1**: `.agents/agents/<이름>.md`마다 `.codex/agents/<이름>.toml`이 정확히 하나 존재하고, 불필요한 추가 어댑터는 없어야 한다. `.gitignore`는 `.codex/agents/*.toml`만 공용 추적 예외로 열어야 한다.
- **R2**: 각 TOML은 Codex 필수 필드 `name`·`description`·`developer_instructions`만 가지며, `name`과 `description`은 대응 Markdown frontmatter와 일치해야 한다.
- **R3**: `developer_instructions`는 현재 작업 디렉터리부터 상위 디렉터리를 탐색해 `.agents/agents/<이름>.md`를 찾고, 작업 전에 전문을 읽어 역할 계약으로 적용하도록 지시해야 한다. 계약을 찾지 못하면 역할을 추측하지 않고 누락을 보고해야 한다.
- **R4**: 어댑터에는 `model`·`model_reasoning_effort`·`sandbox_mode`·`mcp_servers`·`skills.config`를 넣지 않는다. 모델 선택은 `AGENTS.md` 9절 티어 표, 권한은 부모 세션과 3절 가드레일을 따른다.
- **R5**: `AGENTS.md`·`README.md`·ADR·MOC·변경 이력은 `.codex/agents/`가 형식 어댑터이며 `.agents/agents/`가 단일 원본임을 동일하게 설명해야 한다.

## 인터페이스 / 설계 개요

각 어댑터는 Codex가 요구하는 최소 TOML 스키마만 제공한다. 역할 본문은 복사하지 않고 다음 흐름으로 연결한다.

`Codex custom-agent 로더 → .codex/agents/<이름>.toml → 상위 탐색 → .agents/agents/<이름>.md 전문 로드`

이 구조에서 TOML은 로더 호환 계층이고 Markdown은 CLI 공용 역할 계약이다.

## 완료 기준 (테스트 가능한 형태)

- [x] **C1 (R1)**: Markdown과 TOML의 파일 stem 집합을 비교하면 정확히 일치하고, `git check-ignore`에서 7개 TOML이 무시되지 않는다.
- [x] **C2 (R2)**: Python 표준 라이브러리 `tomllib`으로 7개 TOML을 파싱하면 모두 성공하고, 세 필수 필드가 존재하며 `name`·`description`이 Markdown frontmatter와 일치한다.
- [x] **C3 (R3·R4)**: 각 `developer_instructions`가 대응 계약 경로와 전문 선로드·누락 보고를 포함하고, 금지된 고정 설정 키는 한 파일에도 없다.
- [x] **C4 (R5)**: 무결성 점검과 문서 MOC 검사가 통과하고, README·AGENTS.md·ADR·변경 이력이 같은 구조를 설명한다.
- [ ] **C5 (R1~R4)**: 새 Codex 프로세스의 모델 입력에 custom agent 7종이 collaboration agent type으로 노출된다.

> C5 런타임 확인: 새 read-only·ephemeral `codex exec`는 thread 시작까지 도달했으나 로컬 ChatGPT 토큰 만료(`token_expired`·`refresh_token_reused`)로 모델 호출 전에 중단됐다. 비인증 `codex debug prompt-input`의 프로젝트 로드와 설치 바이너리의 3필드 agent-role 스키마, reviewer 독립 검증은 통과했다. 사용자 재로그인 후 실제 7종 열거·spawn을 재실행하면 남은 런타임 표면이 닫힌다.

## 미해결 질문

없음. 역할 원본 유지와 모델명 비고정은 기존 9~11절 규칙으로 결정되어 있다.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-19 | 초안 작성 후 사용자 승인 요청을 근거로 확정 | 전체 | Codex에서 기존 표준 팀원 7종을 네이티브 custom agent로 사용하기 위함 |
| 2026-07-19 | 어댑터 7종·드리프트 검사 구현, C1~C4 통과·C5 인증 후 확인 대기로 상태 갱신 | 전체 | 회귀 24/24·저장소 무결성 36 pass·reviewer PASS, 로컬 인증 만료는 저장소 정확성 비차단 판정 |
