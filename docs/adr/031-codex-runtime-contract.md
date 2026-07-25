# ADR 031 — Codex 런타임 계약 실측 정렬

- **날짜**: 2026-07-25
- **상태**: 활성
- **관련**: ADR 019·027·029, 스펙 `2026-07-25-codex-runtime-compatibility`

## 변경 내용

1. 루트 `AGENTS.md`를 32,000바이트 이하로 유지하고 integrity-check R14가 초과를 차단한다. 신뢰된 프로젝트에서는 `project_doc_max_bytes = 65536`을 보조 여유로 둔다.
2. Codex 세션 훅의 단일 등록 원본을 `.codex/hooks.json`에서 `.codex/config.toml`의 인라인 `hooks.<Event>` 테이블로 옮긴다.
3. 기능 키는 정식 `[features].hooks = true`를 사용하며, 프로젝트 설정과 훅 정의 해시 신뢰가 필요하다는 계약을 명시한다.
4. `.codex/agents/*.toml` 얇은 어댑터 7종은 Codex CLI 0.145.0에서 런타임 열거와 실제 spawn까지 확인된 계약으로 승격한다.

## 대상

`AGENTS.md`, `.codex/config.toml`, `.codex/hooks.json`(제거), `.agents/hooks/integrity-check.py`, harness-install·harness-review, 관련 ADR·스펙

## 사유

Codex CLI 0.145.0 실측에서 `.codex/hooks.json`은 `codex exec` 세션 훅을 실행하지 않았지만, 동일 명령을 `.codex/config.toml` 인라인 훅으로 정의하면 SessionStart stdout이 developer context에 포함되고 PreToolUse exit 2가 도구 실행을 차단했다. 기존 `codex_hooks`는 폐기 예정 별칭이며 프로젝트 설정은 저장소 신뢰 전에는 적용되지 않는다. 한편 기본 프로젝트 문서 한도는 32,768바이트라 38,526바이트였던 `AGENTS.md` 후반 규칙이 잘렸고, 기존 R14 40,000바이트는 이를 놓쳤다.

## 결정

| 항목 | 결정 | 근거 |
|---|---|---|
| 항상-온 문서 크기 | 단일 FAIL 기준 32,000바이트 | Codex 기본 32,768바이트보다 768바이트 여유. 효율 WARN 계층을 따로 만들 실익보다 단순한 호환성 게이트가 크다 |
| 방어 계층 | `AGENTS.md` 축소가 1차, 64KiB 프로젝트 설정이 2차 | 신선한 clone은 trust 전 프로젝트 설정을 적용하지 않으므로 설정만으로 절단을 막을 수 없다 |
| 훅 등록 | `.codex/config.toml` 인라인 정의만 추적 | 0.145.0 런타임에서 실제 로딩된 경로. 병렬 JSON 원본은 드리프트와 허위 보장을 만든다 |
| SessionStart 출력 | plain stdout/additional context는 모델 developer context, `systemMessage`는 UI·이벤트 표면 | 공식 훅 계약과 실제 prompt-input 관찰에 맞춘 역할 분리 |
| PreToolUse 차단 | exit 2 + stderr를 기계 차단으로 사용 | 0.145.0에서 `apply_patch` 실행 전 차단을 실측 |
| custom agent | 얇은 TOML 어댑터 계약 유지 | 7종 열거 및 격리 컨텍스트 reviewer spawn 성공. 역할 본문은 계속 Markdown 단일 원본 |

## 한계

- 훅 실측은 macOS와 Codex CLI 0.145.0 기준이다. Windows는 미검증이다.
- 프로젝트 설정 trust와 exact hook-definition hash trust는 별도이며 둘 다 완료돼야 실행된다. 설치 시 `/hooks`에서 정의를 검토·신뢰한다.
- 세션 훅은 편의·실행 계층이다. 필수 규칙의 유일한 운반자로 사용하지 않는다.
- custom agent의 full-history fork는 부모 agent type을 상속하므로 다른 역할 spawn은 격리 컨텍스트를 사용한다.

## 검증

- `codex debug prompt-input -c project_doc_max_bytes=32768`에서 `AGENTS.md` 마지막 절 확인
- custom agent 7종 런타임 스키마 열거 및 reviewer 격리 spawn 확인
- 프로젝트 인라인 SessionStart reminder의 developer context 포함 확인
- PostToolUse 진단 기록 뒤 PreToolUse exit 2 차단 확인
- integrity-check R14·R18 경계 및 설정 계약 회귀 테스트
