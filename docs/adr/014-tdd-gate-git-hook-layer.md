# ADR 014 — TDD 게이트의 git 훅 계층 추가 (도구 무관 강제)

> ⚠️ 이 중 "이관이 아니라 계층 추가(PreToolUse 유지)" 결정은 **ADR 015로 대체**되었다 — git 계층 단일화, PreToolUse 등록·명령 파싱 제거. 나머지 결정(commit-msg 선택, 전역 hooksPath, 체인 shim, 예외, `--no-verify` 수용, 설치처별 등록)은 유효하다.

- **날짜**: 2026-07-14
- **변경 내용**: `.agents/githooks/`(추적)를 신설하고 전역 `core.hooksPath`로 등록해, `tdd-gate.py`가 git commit-msg 훅으로도 실행되게 한다. 이로써 게이트가 Claude Code 세션(PreToolUse)뿐 아니라 **Codex CLI·수동 커밋 등 모든 도구**의 커밋에 걸린다.
- **대상**: `.agents/githooks/`(신설·추적 — commit-msg 게이트 shim + pre-commit·prepare-commit-msg·post-commit·pre-push 체인 shim), `.agents/hooks/tdd-gate.py`(이중 모드 리팩토링)·`tdd-gate_test.py`(C14~C21), `docs/specs/2026-07-13-tdd-gate-hook.md`(R9·R10), harness-install 1단계, AGENTS.md 13절 4항
- **사유**: 사용자 관찰(2026-07-14) — Codex 세션은 `.claude/settings.json` 훅을 읽지 않아 13절 TDD 게이트가 걸리지 않는다. ADR 008은 이를 "Claude Code 한정, 규칙은 문서가 운반"으로 수용했으나, 같은 규칙의 강제력이 도구에 따라 달라지는 비대칭은 게이트 우회 경로가 된다. **이 ADR은 ADR 008의 "Claude Code 한정" 결정을 대체(supersede)한다** — 나머지 008 결정(차단 지점, fail-open, 예외 경로, 스크립트 위치 등)은 유지된다.

## 결정

| 결정 | 내용 | 근거 |
|---|---|---|
| 이관이 아니라 **계층 추가** | PreToolUse 훅을 제거하지 않고 git 계층을 더한다 | ① settings.json은 추적되어 모든 설치처에 자동 전파되지만 전역 git 설정은 전파되지 않는다 — 제거하면 hooksPath 미등록 설치처(Windows·사내)의 게이트가 조용히 꺼진다. ② PreToolUse는 명령 실행 전에 개입하므로 `--no-verify`까지 잡는다. 이중 실행은 무해하다(읽기 전용 판정) |
| 훅 종류: **commit-msg** (pre-commit 아님) | 게이트를 commit-msg 훅으로 건다 | 유일한 승인 우회 경로 `[no-test]`가 커밋 메시지에 있다 — pre-commit 시점에는 메시지를 볼 수 없고, commit-msg는 메시지 파일을 인자로 받으면서 비0 종료로 커밋을 중단시킬 수 있다 |
| 전달: **전역 core.hooksPath** (저장소별 설치 아님) | `git config --global core.hooksPath <루트>/.agents/githooks` | 저장소별 설치(.git/hooks 복사)는 신규 클론·Codex가 만든 저장소가 무방비다. 전역 등록은 현재·미래의 모든 저장소를 즉시 덮는다. 이 설치처의 저장소 3개 전부 로컬 훅·husky·pre-commit 프레임워크 미사용을 확인(2026-07-14)해 가림 부작용이 없다 |
| 로컬 훅 **체인 shim** | commit-msg는 게이트 스크립트 존재 확인(부재 시 통과 — fail-open) 후 게이트를 실행하고 로컬 `.git/hooks/commit-msg`로 체인. pre-commit·prepare-commit-msg·post-commit·pre-push·post-checkout·post-merge 6종은 체인 전용 shim | 전역 hooksPath는 저장소 로컬 훅을 완전히 가린다 — pre-commit 프레임워크·git-lfs(post-checkout·post-commit·post-merge·pre-push 사용)를 도입해도 조용히 죽지 않게 한다. **열거되지 않은 훅 종류는 체인되지 않는다** — 필요해지면 shim을 추가한다. 로컬 훅 탐색은 `rev-parse --git-dir` 기준(`--git-path hooks/`는 hooksPath를 따라 자기 자신을 돌려줘 무한 재귀) |
| husky류 저장소는 게이트 미적용 수용 | 로컬 `core.hooksPath`(husky 등)는 전역을 덮어쓴다 | git 설정 우선순위상 불가피. 그런 저장소는 자체 훅 체계가 있고, 규칙 원본은 13절 문서다(ADR 006 "규칙의 운반체는 문서") |
| merge·sequencer 커밋 통과 | MERGE_HEAD·CHERRY_PICK_HEAD·REVERT_HEAD·rebase 진행 상태면 판정 없이 통과 | 이미 게이트를 지난 커밋의 재조합이다. 특히 `git pull` 머지 커밋을 차단하면 일상 동기화가 막힌다 — PreToolUse 계층에는 없던 진입 경로라 git 계층에만 필요한 예외. 마커 파일 위조는 무추적 바이패스가 되지만 `--no-verify` 수용과 등가의 한계로 수용한다 |
| `--amend` 거짓 차단 수용 | 테스트가 이미 든 커밋에 코드만 추가 스테이징 후 amend하면 차단된다 | commit-msg 훅 시점에는 amend를 감지할 수단이 없고, HEAD 대비 `diff --cached`만 본다(PreToolUse 모드도 동일한 기존 한계 — 회귀 아님). 테스트 동반 스테이징 또는 `[no-test]`로 통과시킨다(스펙 R9 명문화) |
| `--no-verify` 우회 수용 | git 계층에서는 차단 불가·비목표로 명시 | git 내장 옵션이라 제거할 수 없다. Claude 세션은 PreToolUse가 실행 전에 개입해 방어하고, 그 외 도구의 `--no-verify`는 13절 문서 규칙과 리뷰(team-review)가 맡는다 |
| 등록은 설치처별 (harness-install 1단계) | 전역 git 설정은 저장소로 전파되지 않으므로 설치 절차에 편입 | REGISTRY.md처럼 "클론만으로 완성되지 않는" 설치처별 배선이다. 기존 값이 있으면 덮어쓰지 않고 사용자 확인(기존 훅 체계 충돌 방지) |

## 검증

- **스펙**: `docs/specs/2026-07-13-tdd-gate-hook.md` — R9(git 모드)·R10(전역 등록·체인), 완료 기준 C14~C21.
- **회귀 테스트**: `.agents/hooks/tdd-gate_test.py` 37케이스 전부 통과(2026-07-14) — git 모드 판정(C14~C19), shim 통합(실제 `git commit` 차단/통과, C20), 로컬 훅 체인(C21) 포함.
- **실전 검증**: hooksPath 등록 후 임시 저장소에서 테스트 없는 코드 커밋 → 차단·커밋 미생성 확인(2026-07-14).
