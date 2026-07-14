# 스펙: tdd-gate 훅 — 13절 TDD 커밋 게이트

- 날짜: 2026-07-13 / 상태: 구현됨
- 관련: docs/adr/008-tdd-gate-hook.md, 루트 AGENTS.md 13절 4항

## 배경

루트 AGENTS.md 13절(SDD+TDD)은 문서 규칙이라 강제력이 없다 — 모델이 잊으면 테스트 없는 "구현 완료"가 그대로 커밋된다. 커밋 시점에 실행 계층에서 차단하는 게이트가 필요하다(사용자 승인, 2026-07-13).

## 목표

- 하위 프로젝트 저장소에서 코드 파일이 테스트 변경 없이 커밋되는 것을 커밋 시점에 차단한다.
- 정상 커밋과 13절 적용 제외 대상(문서, 루트 하네스 저장소, `dev/`)은 간섭 없이 통과한다.
- 훅 자체의 오류가 커밋을 막지 않는다(fail-open).

## 비목표

- 테스트의 **품질·통과 여부** 검증(그건 `team-review`·CI의 몫 — 이 게이트는 존재만 본다).
- Codex 세션 강제(훅은 Claude Code 계층 — 규칙 자체는 13절 문서가 운반).
- 셸 파싱의 완전성(따옴표 이스케이프·중첩 서브셸 등 — fail-open으로 수용).

## 요구사항

- R1: PreToolUse(Bash) 훅으로 `git commit` 명령을 감지하고, 커밋 대상 파일에 코드 파일(CODE_EXTS)이 있는데 테스트 파일 변경이 없으면 exit 2로 차단하고 13절 조치를 stderr로 안내한다.
- R2: 커밋 대상 판정 — 기본은 스테이징(`diff --cached`), `-a`/`--all` 플래그면 tracked 수정분(`diff HEAD`)을 본다. 따옴표 안 텍스트(커밋 메시지 등)는 커밋 감지·플래그 감지에 오인되지 않아야 하고, 커밋 감지는 **서브커맨드 위치**의 `commit`만 인정한다(`git log --grep=commit` 등 인자 속 단어 제외 — git 전역 옵션 경유 `git -c k=v commit`은 인정).
- R3: 대상 저장소 해석 — 훅 입력 `cwd`를 기본으로, 명령의 `cd <path>` 체인(누적 적용)과 git **전역** `-C <path>`(subcommand 이전 위치만 — `git commit -C HEAD`의 `-C`는 메시지 재사용 플래그다)를 반영한다. 공백 경로(따옴표)와 서브디렉토리 cwd를 지원한다.
- R4: 예외(통과) — ① 루트 하네스 저장소 자신 ② `dev/` 아래 저장소 ③ 최초 커밋(HEAD 없음) ④ 커밋 명령에 `[no-test]` 포함(동작 불변 수정, **사용자 확인 전제** — 커밋 메시지에 흔적이 남는 유일한 우회 경로). 이 외의 우회 장치(환경변수 등 무추적 바이패스)는 두지 않는다.
- R5: 테스트 파일 판정 — 테스트 디렉토리 세그먼트(test/tests/__tests__/spec/specs/e2e/testing/integration_test/androidTest/unitTest) 또는 파일명 규약(`test_*`/`spec_*` 접두, `*_test`/`*_tests`/`*_spec` 접미, `*.test.*`/`*.spec.*`). `latest`·`backtest` 등 구분자 없는 포함 문자열은 테스트로 취급하지 않는다.
- R6: fail-open — JSON 파싱 실패, git 실패, 저장소 아님, 예외 발생 시 전부 exit 0.
- R7: CODE_EXTS는 앱 코드 확장자 중심으로 한다. `.sh`/`.sql`/`.tf` 등 스크립트·마이그레이션·IaC는 제외한다(테스트 관행이 낮아 게이트 마찰 > 가치 — 범위 결정은 ADR 008에 기록).
- R8: 회귀 테스트가 `.agents/hooks/tdd-gate_test.py`로 영속되어야 하며, 훅 수정 시 이 테스트를 통과해야 한다.

## 인터페이스 / 설계 개요

- 등록: 루트 `.claude/settings.json` → PreToolUse, matcher `Bash`, command는 **인터프리터 탐색 체인** `for p in python3 python py; do command -v "$p" >/dev/null 2>&1 && exec "$p" "$CLAUDE_PROJECT_DIR/.agents/hooks/tdd-gate.py"; done; exit 0` — `.py` 직접 실행은 Windows(파일 연결·PATHEXT 부재)에서 인터프리터 진입 전에 실패한다. 어떤 인터프리터도 없으면 exit 0(fail-open, 게이트 비활성).
- 입력: stdin JSON(`tool_name`, `tool_input.command`, `cwd`). 출력: exit 0(통과) / exit 2 + stderr 안내(차단).
- 부수 효과 없음 — git 조회 명령만 실행한다.

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1): 코드만 스테이징 후 commit → exit 2, stderr에 파일 목록과 조치 안내.
- [x] C2 (R1): 코드+테스트 동시 스테이징 → exit 0.
- [x] C3 (R2): 문서만 스테이징 → exit 0.
- [x] C4 (R2): tracked 코드 수정 후 `commit -am` → exit 2.
- [x] C5 (R2): `echo "git commit"`(따옴표 안)·`git log --grep=commit`(인자 속) 등 비커밋 명령 → exit 0. 전역 옵션 경유 `git -c k=v commit`은 감지 → exit 2.
- [x] C6 (R2): 커밋 메시지 안 `-a` 텍스트가 플래그로 오인되지 않음 → exit 0 (docs만 스테이징 시).
- [x] C7 (R3): `cd <repo> && git commit`, 다중 `cd` 체인, 공백 경로, 서브디렉토리 cwd에서 올바른 저장소 판정.
- [x] C8 (R3): 코드만 스테이징 + `git commit -C HEAD` → exit 2 (`-C HEAD`를 경로로 오인하지 않음).
- [x] C9 (R4): 루트 하네스 저장소 / `dev/` 저장소 / 최초 커밋 / `[no-test]` → 각각 exit 0.
- [x] C10 (R5): `tests/` 하위 파일은 테스트로 인정(exit 0), `latest.py` 단독 커밋은 코드로 판정(exit 2).
- [x] C11 (R6): 깨진 JSON 입력 → exit 0.
- [x] C12 (R8): `python3 .agents/hooks/tdd-gate_test.py` 전 케이스 통과.

## 미해결 질문

없음.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-13 | 초안 작성 및 구현 반영 (reviewer 1차 검증 F5 — 스펙 부재 지적으로 소급 작성, F1~F4·F6 수정 사항 반영) | 전체 | 13절 1항 — 스펙 없는 구현은 완료 판정 기준이 없다 |
| 2026-07-13 | R2·C5에 서브커맨드 위치 감지 요건 추가 | R2, C5 | reviewer 2차 검증 F9 — 무따옴표 인자 속 commit 단어 거짓 차단 수정 반영 |
| 2026-07-14 | 등록 command를 인터프리터 탐색 체인(python3→python→py, 부재 시 exit 0)으로 변경 | 등록(설계 개요), .claude/settings.json | Windows 설치처 장애 보고 — `.py` 직접 실행이 파일 연결·PATHEXT 부재로 OS 수준 실패, 훅이 한 번도 실행되지 않음 |
