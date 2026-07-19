# ADR 027 — Codex custom-agent 얇은 어댑터

- **날짜**: 2026-07-19
- **상태**: 활성
- **관련**: ADR 001·005·011·019·021, 스펙 `docs/specs/2026-07-19-codex-agent-adapters.md`

## 변경 내용

표준 팀원 7종의 역할 계약은 `.agents/agents/*.md`에 그대로 두고, Codex 프로젝트 범위 custom-agent 로더를 위한 `.codex/agents/*.toml` 7개를 추가한다. 각 TOML은 Codex 필수 필드 `name`·`description`·`developer_instructions`만 가지며, 대응 Markdown 계약을 현재 작업 디렉터리부터 상위로 찾아 작업 전에 전문 선로드한다.

어댑터의 `name`·`description`은 로더의 선택·표시 메타데이터라 불가피하게 중복되지만, 무결성 점검이 원본 frontmatter와 정확한 일치를 검사한다. 역할 본문·도구 목록·티어는 복제하지 않는다.

## 대상

- 원본: `.agents/agents/{architect,explorer,implementer,infra-specialist,integrator,reviewer,troubleshooter}.md`
- Codex 어댑터: `.codex/agents/*.toml`
- 추적 예외: `.gitignore`의 `.codex/agents/*.toml` allowlist
- 드리프트 검사: `.agents/hooks/integrity-check.py`와 회귀 테스트
- 규칙·생성 절차: `AGENTS.md` 5·10·11절, metaskill과 agent-rules, README

## 사유

Codex는 skill은 `.agents/skills/`에서 네이티브로 발견하지만, custom agent는 `.codex/agents/*.toml` 형식을 요구한다. 기존의 “`.agents/agents/` 공용 원본을 두 CLI가 같은 형식으로 직접 본다”는 가정만으로는 Codex 이름 기반 agent가 노출되지 않는다.

TOML에 역할 본문을 복사하면 Markdown과 두 번째 원본이 생기므로 부채가 된다. 반대로 어댑터가 Markdown을 선로드하면 형식 차이만 흡수하면서 역할 계약은 하나로 유지된다. `model`·`model_reasoning_effort`를 고정하지 않는 이유는 AGENTS.md 9절의 시점 독립 티어 매핑을 보존하기 위해서다. `sandbox_mode`도 부모 세션 권한을 덮어쓰지 않도록 생략한다.

## 한계

- `.agents/agents/*.md`의 `tools` 화이트리스트는 Claude Code 정의 형식이며 Codex TOML이 같은 방식으로 기계 강제하지 않는다. Codex에서는 부모 세션 도구·sandbox와 Markdown 역할 계약이 경계를 담당한다.
- Codex는 agent 파일 변경 후 새 세션에서 다시 로드한다. 현재 열린 세션의 agent type 목록은 즉시 갱신되지 않을 수 있다.
- Python 3.11 미만 설치처의 무결성 점검은 `tomllib` 부재로 TOML 내부 파싱을 SKIP하지만 파일 1:1은 계속 검사하고, 실제 Codex 로더가 구문을 검증한다.

## 검증

스펙 C1~C4에 따라 TOML 파싱·원본 메타데이터 일치·추가 키 부재·Git 추적·무결성 회귀 테스트를 확인했다. 회귀 24/24, 현 저장소 36 pass/0 fail/0 skip, reviewer 독립 검증 PASS다. C5 실제 7종 spawn은 로컬 Codex 인증 만료로 모델 호출 전에 중단되어 사용자 재로그인 후 런타임 확인으로 남긴다. 새 프로세스의 프로젝트 로드와 설치 바이너리 agent-role 스키마는 확인되어 저장소 정확성의 차단 사유는 아니다.
