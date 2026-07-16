# ADR 015 — TDD 게이트 git 계층 단일화 (PreToolUse 계층 제거)

> 경로 주의: 본문의 `.agents/hooks/tdd-gate.py`는 이 결정 직후 `.agents/githooks/`로 이동했다(2026-07-14, docs/harness-changelog.md — hooks/는 Claude 세션 훅 전용으로 정리).

- **날짜**: 2026-07-14
- **변경 내용**: tdd-gate의 Claude Code PreToolUse 계층(`.claude/settings.json` 등록 + stdin JSON 명령 파싱 ~90줄)을 제거하고 git commit-msg 계층(ADR 014)만 남긴다. 회귀 테스트·스펙을 git 계층 기준으로 재편(R1~R7, C1~C14)하고, 미등록 머신 감시를 harness-review 주간 무결성 점검에 편입한다.
- **대상**: `.claude/settings.json`(PreToolUse 블록 삭제), `.agents/hooks/tdd-gate.py`(단일 모드화)·`tdd-gate_test.py`(재편), `docs/specs/2026-07-13-tdd-gate-hook.md`(전면 개정), `.agents/skills/harness-review/SKILL.md`(무결성 점검 항목 추가), AGENTS.md 13절 4항
- **사유**: 사용자 결정(2026-07-14) — "정리를 안 하면 헷갈린다." 같은 게이트가 두 진입점·두 판정 경로(명령 파싱 vs 인덱스 조회)를 가지면 스펙·테스트·유지보수가 이중이 되고, ADR 014가 남긴 중복의 가치(전파 보증·`--no-verify` 방어)보다 혼란 비용이 크다고 판단했다. **이 ADR은 ADR 014의 "이관이 아니라 계층 추가(PreToolUse 유지)" 결정을 대체한다** — 나머지 014 결정(commit-msg 선택, 전역 hooksPath, 체인 shim, 예외, `--no-verify` 수용, 설치처별 등록)은 유지된다.

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| PreToolUse 계층 제거 | settings.json 등록과 stdin JSON·명령 파싱(따옴표/cd 체인/전역 옵션 해석) 코드를 삭제 | 명령 파싱은 셸 문법 근사라 본질적으로 불완전(과거 F2·F3·F9 오탐 이력)한 반면, git 계층은 훅 시점의 실제 인덱스를 조회해 파싱 자체가 불필요하다. 남길 가치였던 `-a` 처리도 GIT_INDEX_FILE 상속으로 대체 검증(C11c) |
| 타 설치처 이행 경로 | 최신 코드 pull 후 **harness-install 재실행**(1단계가 hooksPath 등록) | 전역 git 설정은 저장소로 전파되지 않으므로 설치 절차가 등록 지점이다. settings.json의 PreToolUse 삭제는 pull 즉시 전파되므로, 등록 전까지 그 머신은 게이트 공백 상태 — 아래 감시로 보완 |
| 공백 감시: harness-review 주간 무결성 | `git config --global --get core.hooksPath` 확인 항목을 무결성 점검에 추가 | "pull은 했는데 harness-install을 안 돌린 머신"이 조용히 무방비가 되는 것이 단일화의 유일한 구조적 위험 — 주간 점검이 표면화한다 |
| `--no-verify` 방어 상실 수용 | PreToolUse는 명령 실행 전 개입이라 `--no-verify`도 차단했으나, git 계층 단일화로 이 방어는 사라진다 | 사용자 승인 트레이드오프. `--no-verify`는 명시적·의도적 우회라 커밋 이력 리뷰(team-review)와 13절 문서 규칙이 맡는다 |
| 구버전 등록 호환 | 스크립트는 `--commit-msg` 이외의 진입(구버전 settings.json이 stdin 모드로 호출)에 exit 0 | pull 순서에 따른 혼합 상태(구 settings + 신 스크립트)에서 세션이 깨지지 않게 fail-open |

## 검증

- **스펙**: `docs/specs/2026-07-13-tdd-gate-hook.md` — R1~R7·C1~C14로 전면 재편.
- **회귀 테스트**: `.agents/hooks/tdd-gate_test.py` 24케이스 전부 통과(2026-07-14) — `commit -am`의 GIT_INDEX_FILE 상속 실커밋 검증(C11c), shim 통합·체인·fail-open 포함.
