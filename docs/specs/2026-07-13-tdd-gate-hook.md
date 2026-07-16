# 스펙: tdd-gate 훅 — 13절 TDD 커밋 게이트

- 날짜: 2026-07-13 / 상태: 구현됨
- 관련: docs/adr/008-tdd-gate-hook.md, docs/adr/014-tdd-gate-git-hook-layer.md, docs/adr/015-tdd-gate-single-git-layer.md, 루트 AGENTS.md 13절 4항

## 배경

루트 AGENTS.md 13절(SDD+TDD)은 문서 규칙이라 강제력이 없다 — 모델이 잊으면 테스트 없는 "구현 완료"가 그대로 커밋된다. 커밋 시점에 실행 계층에서 차단하는 게이트가 필요하다(사용자 승인, 2026-07-13). 처음에는 Claude Code PreToolUse 훅으로 구현했으나(ADR 008), Codex 등 다른 도구에 걸리지 않는 비대칭을 해소하며 git commit-msg 계층을 추가했고(ADR 014), 이중 계층의 혼란 비용을 이유로 git 계층으로 단일화했다(ADR 015 — 사용자 결정, 2026-07-14).

## 목표

- 하위 프로젝트 저장소에서 코드 파일이 테스트 변경 없이 커밋되는 것을 커밋 시점에 차단한다.
- **도구 무관 강제**: Claude Code·Codex CLI·수동 커밋 등 커밋 주체와 무관하게 같은 게이트가 걸린다(git commit-msg 계층).
- 정상 커밋과 13절 적용 제외 대상(문서, 루트 하네스 저장소, `dev/`)은 간섭 없이 통과한다.
- 훅 자체의 오류가 커밋을 막지 않는다(fail-open).

## 비목표

- 테스트의 **품질·통과 여부** 검증(그건 `team-review`·CI의 몫 — 이 게이트는 존재만 본다).
- `--no-verify` 우회 차단(git 내장 옵션 — 제거 불가. 13절 문서 규칙과 리뷰가 운반한다).
- 훅 미등록 머신의 강제(전역 git 설정은 저장소로 전파되지 않는다 — 등록은 harness-install 1단계, 미등록 감시는 harness-review 주간 무결성 점검).

## 요구사항

- R1: **git commit-msg 훅** — `tdd-gate.py --commit-msg <메시지 파일>`로 진입한다. cwd(git이 워크트리 루트로 보장)에서 저장소를 판정하고, 커밋 대상은 `diff --cached --name-only --diff-filter=ACMR`만 본다(`git commit -a`도 훅 시점에는 GIT_INDEX_FILE 상속으로 반영됨 — 명령 파싱 불필요). 커밋 대상에 코드 파일(CODE_EXTS)이 있는데 테스트 파일 변경이 없으면 **의도적 차단 전용 코드 exit 65**로 차단하고 13절 조치를 stderr로 안내한다. 차단 코드가 65인 이유: 인터프리터 자체 실패 코드(SyntaxError rc 1, 파일 열기 실패 rc 2)와 겹치면 shim이 게이트 손상을 차단으로 오인해 머신 전역 커밋이 막힌다(R4 위반 — 2026-07-16 감사 재현).
- R2: 예외(통과) — ① 루트 하네스 저장소 자신 ② `dev/` 아래 저장소 ③ 최초 커밋(HEAD 없음) ④ 메시지 파일에 `[no-test]` 포함(동작 불변 수정, **사용자 확인 전제** — 커밋 메시지에 흔적이 남는 유일한 승인 우회 경로) ⑤ merge/cherry-pick/revert/rebase 진행 상태(git-dir의 MERGE_HEAD·CHERRY_PICK_HEAD·REVERT_HEAD·rebase-merge·rebase-apply — 이미 게이트를 지난 커밋의 재조합이며, 특히 `git pull` 머지 커밋의 거짓 차단을 막는다).
- R3: 테스트 파일 판정 — 테스트 디렉토리 세그먼트(test/tests/__tests__/spec/specs/e2e/testing/integration_test/androidTest/unitTest), 파일명 규약(`test_*`/`spec_*` 접두, `*_test`/`*_tests`/`*_spec` 접미, `*.test.*`/`*.spec.*`), 또는 **정확 파일명 allowlist**(`tests.py` — Django 앱 기본, `conftest.py` — pytest 픽스처). allowlist는 정확 일치만이다(`contest.py`는 코드) — `latest`·`backtest` 등 구분자 없는 포함 문자열은 여전히 테스트로 취급하지 않는다. 이유: 주류 관행의 false block은 `[no-test]`·`--no-verify` 남용을 학습시켜 게이트 자체를 죽인다(2026-07-16 감사 — models.py+tests.py 차단 재현).
- R4: fail-open — 메시지 파일 없음, git 실패, 저장소 아님, 예외 발생, 알 수 없는 인자 진입 시 전부 exit 0. 시작 시 stdio를 **UTF-8(errors=replace)로 재구성**한다 — 한글 Windows 콘솔(cp949)은 차단 안내의 em dash를 인코딩하지 못해 write가 예외를 던지고, fail-open이 그것을 삼켜 **차단해야 할 커밋이 통과**한다(2026-07-14 장애 — 게이트 무력화).
- R5: CODE_EXTS는 앱 코드 확장자 중심으로 한다. `.sh`/`.sql`/`.tf` 등 스크립트·마이그레이션·IaC는 제외한다(테스트 관행이 낮아 게이트 마찰 > 가치 — 범위 결정은 ADR 008에 기록).
- R6: **전역 등록·체인** — 추적 디렉토리 `.agents/githooks/`의 `commit-msg` shim이 게이트 스크립트 존재 확인(부재 시 통과 — R4) 후 인터프리터 탐색 체인(python3→python→py, 실행 확인 `-c ""` — Windows Store 스텁 배제)으로 게이트를 실행하고, **게이트의 의도적 차단(exit 65)만 커밋 차단으로 전파**하며(그 외 비0 rc는 게이트 오류 — fail-open으로 체인 진행, R4), 통과 시 저장소 로컬 `.git/hooks/commit-msg`로 체인한다. `pre-commit`·`prepare-commit-msg`·`post-commit`·`pre-push`·`post-checkout`·`post-merge`는 체인 전용 shim을 둔다(전역 hooksPath가 로컬 훅을 가리는 부작용 방지 — git-lfs가 쓰는 4종 포함. 열거되지 않은 훅 종류는 체인되지 않으며, 필요 시 shim을 추가한다). 로컬 훅 탐색은 `rev-parse --git-dir` 기준이어야 한다 — `--git-path hooks/`는 core.hooksPath를 따라 자기 자신을 돌려줘 무한 재귀한다. 등록은 설치처별 설정 `git config --global core.hooksPath <루트>/.agents/githooks`로 하며 harness-install 1단계가 수행하고, 미등록은 harness-review 주간 무결성 점검이 잡는다.
- R7: 회귀 테스트가 `.agents/githooks/tdd-gate_test.py`로 영속되어야 하며, 훅 수정 시 이 테스트를 통과해야 한다.
- **알려진 한계**: ① `--amend`는 훅 시점에 감지할 수 없어, 테스트가 이미 든 커밋에 코드 수정만 추가 스테이징하면 차단된다(HEAD 대비 `diff --cached`만 보므로). 테스트를 함께 스테이징하거나 `[no-test]`로 통과시킨다. ② sequencer 마커 파일 위조는 무추적 바이패스가 되지만 `--no-verify` 수용과 등가의 한계로 수용한다. ③ **rename-only 커밋 false block**: 내용 불변의 코드 파일 이름 변경도 `--diff-filter=ACMR`의 R에 걸려 차단된다 — `[no-test]`로 통과시킨다(rename 유사도 판정 추가는 마찰 재발 시 스펙 개정으로 검토). ④ **rebase edit 중 신규 커밋 게이트 skip**: rebase-merge/rebase-apply 마커가 있는 동안은 `rebase -i`의 edit 정지 지점에서 만든 **새** 커밋도 통과한다(재조합 가정 R2 ⑤의 한계) — 리뷰(team-review)가 담당한다. (③④ 2026-07-16 감사에서 기재)

## 인터페이스 / 설계 개요

- 등록: 전역 `core.hooksPath` → `.agents/githooks/` (머신별, harness-install 1단계). 훅 유형이 `pre-commit`이 아니라 **`commit-msg`**인 이유: 승인 우회 마커 `[no-test]`가 커밋 메시지에 있는데 pre-commit 시점에는 메시지를 볼 수 없고, commit-msg는 메시지 파일을 인자로 받으면서 비0 종료로 커밋을 중단시킬 수 있다.
- 입력: argv `--commit-msg <메시지 파일>`, cwd = 워크트리 루트. 출력: exit 0(통과) / exit 65 + stderr 안내(차단 — shim이 git에는 exit 1로 전달).
- 부수 효과 없음 — git 조회 명령만 실행한다.
- 히스토리: PreToolUse(Bash) 계층과 stdin JSON 명령 파싱(따옴표·cd 체인·전역 옵션 해석)은 ADR 015로 제거됐다 — 당시 요구사항·완료 기준은 이 문서의 git 이력(R1~R8·C1~C23, 2026-07-14 이전 리비전)과 ADR 008·014에 남아 있다.

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1): 코드만 스테이징 → exit 65, stderr에 파일 목록과 조치 안내.
- [x] C2 (R1): 코드+테스트 동시 스테이징 → exit 0.
- [x] C3 (R1): 문서만 스테이징 → exit 0.
- [x] C4 (R2): 메시지 파일에 `[no-test]` → exit 0.
- [x] C5 (R2): MERGE_HEAD(머지)·CHERRY_PICK_HEAD(체리픽) 진행 상태 → exit 0.
- [x] C6 (R2): 루트 하네스 저장소 / `dev/` 저장소 → exit 0.
- [x] C7 (R2): 최초 커밋(HEAD 없음) → exit 0.
- [x] C8 (R4): 메시지 파일 없음 → fail-open exit 0.
- [x] C9 (R3): `tests/` 하위 파일은 테스트로 인정(exit 0), `latest.py` 단독 커밋은 코드로 판정(exit 65). **allowlist**: `app/tests.py`·`conftest.py`는 코드와 동시 커밋 시 테스트로 인정(exit 0), `contest.py` 단독은 차단(exit 65 — 정확 일치만).
- [x] C10 (R4): cp949 stdio(PYTHONIOENCODING=cp949)에서 코드만 커밋 → 여전히 exit 65 + 차단 안내 출력(게이트 무력화 없음).
- [x] C11 (R1·R6): shim 통합 — `core.hooksPath=.agents/githooks`로 실제 `git commit` 실행 시 코드만 커밋은 차단(+안내 출력), 코드+테스트 커밋은 성공, tracked 수정 `commit -am`도 차단(GIT_INDEX_FILE 상속 검증).
- [x] C12 (R6): shim 체인 — 게이트 통과 후 저장소 로컬 `.git/hooks/commit-msg`가 실행됨.
- [x] C13 (R6): shim — 게이트 스크립트 부재(하네스 이동·삭제) 시 커밋 통과(fail-open — 머신 전역 커밋 차단 방지).
- [x] C13b (R4·R6): shim — 게이트 스크립트 **손상**(SyntaxError → 인터프리터 rc 1) 시 커밋 통과. 모든 비0 rc를 차단으로 전파하면 손상 시 머신 전역 커밋(게이트 수정 커밋 포함)이 막힌다(2026-07-16 감사 HOOK-F1 재현 → exit 65 전용 코드로 수정).
- [x] C14 (R4): 알 수 없는 진입 — 구버전 PreToolUse 방식(무인자 + stdin JSON)·인자 누락 호출 → exit 0(혼합 상태 호환 — ADR 015).
- [x] C15 (R2·R4): 비UTF-8 로케일(한글 Windows cp949·C 로케일) + 한글 파일명 스테이징 → 차단 유지(exit 65). 2중 방어: git 경로 출력을 `core.quotepath=false`(8진수 이스케이프가 확장자 판정을 깨는 것 방지) + `encoding="utf-8"` 명시(로케일 의존 디코딩 제거 — UnicodeDecodeError를 fail-open이 삼켜 게이트 무력화 방지)로 받는다. 파일시스템이 한글 파일명을 못 담는 환경에서는 SKIP을 명시 출력한다.

## 미해결 질문

없음.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-13 | 초안 작성 및 구현 반영 (reviewer 1차 검증 F5 — 스펙 부재 지적으로 소급 작성, F1~F4·F6 수정 사항 반영) | 전체 | 13절 1항 — 스펙 없는 구현은 완료 판정 기준이 없다 |
| 2026-07-13 | R2·C5에 서브커맨드 위치 감지 요건 추가 | R2, C5 | reviewer 2차 검증 F9 — 무따옴표 인자 속 commit 단어 거짓 차단 수정 반영 |
| 2026-07-14 | 등록 command를 인터프리터 탐색 체인(python3→python→py, 부재 시 exit 0)으로 변경 | 등록(설계 개요), .claude/settings.json | Windows 설치처 장애 보고 — `.py` 직접 실행이 파일 연결·PATHEXT 부재로 OS 수준 실패, 훅이 한 번도 실행되지 않음 |
| 2026-07-14 | 인터프리터 판별을 존재 확인(command -v)에서 실행 확인(-c "")으로 강화 | 등록, .claude/settings.json | Windows 재발 보고 — Store App Execution Alias 스텁이 존재 확인을 통과해 exec 후 exit 49로 실패 |
| 2026-07-14 | stdio UTF-8 재구성, cp949 완료 기준 신설 | 인터페이스, 완료 기준 | 한글 Windows 장애 보고 — cp949 stderr에서 차단 안내의 em dash가 UnicodeEncodeError → fail-open이 차단을 삼켜 게이트 무력화 |
| 2026-07-14 | git commit-msg 계층 추가(구 R9·R10, C14~C23) — `.agents/githooks/` shim + 전역 core.hooksPath, 비목표의 "Codex 세션 강제"를 목표로 승격 | 목표, 비목표, 요구사항, .agents/githooks/, tdd-gate.py, harness-install | 사용자 요청 — Codex 등 도구 무관 강제. ADR 008의 "Claude Code 한정" 결정을 ADR 014가 대체 |
| 2026-07-14 | **git 계층 단일화** — PreToolUse 등록·stdin JSON 명령 파싱 계층 제거, 요구사항 R1~R7·완료 기준 C1~C14로 전면 재편, 미등록 감시를 harness-review 주간 무결성에 편입 | 전체 | 사용자 결정 — 이중 계층의 혼란 비용 > 중복 가치, 타 설치처는 최신 코드 기반 harness-install 재실행으로 등록. ADR 014의 "계층 추가(PreToolUse 유지)" 결정을 ADR 015가 대체 |
| 2026-07-14 | 스크립트·테스트를 `.agents/hooks/` → `.agents/githooks/`로 이동 | tdd-gate.py, tdd-gate_test.py, commit-msg shim, 문서 경로 전반 | 사용자 결정 — 단일화 후 hooks/는 Claude 세션 훅 전용이 됐으므로, git이 부르는 게이트는 진입 shim과 같은 곳에 둔다(git은 훅 이름과 일치하는 파일만 실행하므로 .py 동거 무해) |
| 2026-07-15 | utf8_stdio를 `.agents/hooks/_common.py` import로 전환 — 교차 디렉토리라 파일 위치 기준 sys.path 삽입, 유실 시 no-op 폴백 | tdd-gate.py | 일일 점검 신호 ②(공통 로직 복제로 fix 3연쇄) — 스펙 2026-07-15-hooks-common-bootstrap |
| 2026-07-15 | 서브프로세스 출력 로케일 비의존화 + C15 신설 — git() 호출에 `core.quotepath=false`·`encoding="utf-8"` 명시, 테스트 하니스 subprocess.run 5곳 encoding 명시·스위트 stdio UTF-8 재구성(_common 공유) | git(), C15, tdd-gate_test.py | 대기 큐 보고(2026-07-15, 한글 Windows harness-install 재점검) — 미지정 text=True가 cp949 로케일에서 자식 출력 디코딩 크래시(스위트 C1 이후 진행 불가). 조사 중 추가 발견: quotepath 기본값이 한글 파일명 확장자 판정을 깨 로케일 무관하게 게이트 통과(실버그) — 크로스 플랫폼 체크리스트(스펙 템플릿) ③ 실측 검증의 적용 사례 |
| 2026-07-16 | 차단 exit 코드 2→65 전용화 + shim은 65만 차단 전파(C13b 신설), R3에 정확 파일명 allowlist(`tests.py`·`conftest.py`, C9 확장), 알려진 한계 ③rename-only·④rebase-edit 기재 | R1·R3·R6, C1·C9·C10·C13b·C15, tdd-gate.py, commit-msg shim, tdd-gate_test.py | 하네스 전체 감사(2026-07-16) — HOOK-F1(게이트 손상 시 머신 전역 커밋 차단, 재현) High, HOOK-F2(Django/pytest 관례 false block, 재현) Med, HOOK-F9 문서 갭. 사용자 승인 |
