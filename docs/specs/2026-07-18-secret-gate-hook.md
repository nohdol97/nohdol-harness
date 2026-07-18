# 스펙: secret-gate 훅 — 3절 시크릿 기록 금지의 커밋 게이트

- 날짜: 2026-07-18 / 상태: 구현됨
- 관련: docs/adr/023-secret-gate-hook.md, 루트 AGENTS.md 3절(시크릿·자격증명 기록 금지), 8절(훅 승격 원칙), docs/specs/2026-07-13-tdd-gate-hook.md(전례 — shim·fail-open·exit 65 규약 공유)

## 배경

루트 AGENTS.md 3절 "시크릿·자격증명은 하네스 파일과 `_workspace/`에 절대 기록하지 않는다"는 문서 규칙이라 강제력이 없다 — 모델·사람이 실수하면 자격증명이 그대로 커밋되고, 푸시되는 순간 원격 이력에 영구히 남는다(사후 제거는 force push + 키 폐기가 필요한 고비용 사고). 8절 승격 원칙("기계적 차단이 가능하면 훅으로 승격")에 따라 커밋 시점 게이트를 신설한다(loop-engineering gate.yaml 착안, 사용자 승인 2026-07-18). tdd-gate와 같은 git commit-msg 계층을 재사용해 도구 무관(Claude Code·Codex·수동 커밋)으로 걸리게 한다.

## 목표

- 스테이징된 diff의 **추가 줄**에 고신뢰 자격증명 패턴(프로바이더 형식 키·개인키 블록)이 있으면 커밋 시점에 차단한다.
- **모든 저장소에 적용** — tdd-gate와 달리 루트 하네스·`dev/` 예외가 없다. 이유: 시크릿은 어느 git 이력에 들어가도 사고이고, 3절 금지는 하네스 파일을 명시적으로 포함한다.
- 오탐(문서 예시 키·테스트 픽스처)은 **사용자 확인 후** 커밋 메시지 `[secret-ok]`로 통과시킨다 — 메시지에 승인 흔적이 남는 유일한 우회 경로(tdd-gate `[no-test]` 전례).
- 훅 자체의 오류가 커밋을 막지 않는다(fail-open — tdd-gate R4와 동일).

## 비목표

- **범용 고엔트로피·일반 대입문 탐지**(`password = "..."` 류): 오탐률이 높아 `[secret-ok]` 남용을 학습시키고 게이트를 죽인다(tdd-gate R3의 false block 교훈). 전수 탐지는 gitleaks 등 전용 도구의 몫 — 이 게이트는 형식이 확정적인 패턴만 본다.
- 이미 커밋된 이력의 스캔·정화(사후 대응은 별도 절차).
- `--no-verify` 우회 차단(git 내장 — 3절 문서 규칙과 리뷰가 운반).
- JWT 탐지(테스트 픽스처로 흔해 오탐 우세 — 제외).

## 요구사항

- R1: **git commit-msg 훅** — `secret-gate.py --commit-msg <메시지 파일>`로 진입, 기존 `.agents/githooks/commit-msg` shim이 tdd-gate에 이어 실행한다(각 게이트의 exit 65만 차단으로 전파, 그 외 비0 rc는 fail-open — tdd-gate R6 규약 동일). 판정 대상은 `diff --cached -U0 --diff-filter=ACMR`의 **추가 줄(`+` 시작, `+++` 헤더 제외)**만 — 삭제 줄의 시크릿 제거 커밋을 막으면 안 된다.
- R2: 탐지 패턴(고신뢰 형식 확정 패턴만): ① 개인키 블록 `-----BEGIN …PRIVATE KEY` ② AWS Access Key ID `(AKIA|ASIA)[0-9A-Z]{16}` ③ GitHub 토큰 `gh[pousr]_[A-Za-z0-9]{36,}`·`github_pat_[A-Za-z0-9_]{22,}` ④ Slack `xox[baprs]-[0-9A-Za-z-]{10,}` ⑤ Google API `AIza[0-9A-Za-z_-]{35}` ⑥ Stripe `[sr]k_(live|test)_[0-9a-zA-Z]{20,}` ⑦ OpenAI/Anthropic 계열 `sk-[A-Za-z0-9_-]{20,}`. 패턴 추가·제거는 이 스펙 개정으로만 한다.
- R3: 예외(통과) — ① 메시지 파일에 `[secret-ok]` 포함(사용자 확인 전제) ② merge/cherry-pick/revert/rebase 진행 상태(sequencer 마커 — 이미 게이트를 지난 커밋의 재조합, tdd-gate R2 ⑤ 동일). **최초 커밋은 예외가 아니다** — `diff --cached`는 HEAD 없이도 빈 트리 대비로 동작하며, 첫 커밋이야말로 `.env`가 딸려 들어가는 전형적 시점이다.
- R4: fail-open — 메시지 파일 없음, git 실패, 저장소 아님, 예외, 알 수 없는 인자 → 전부 exit 0. 시작 시 stdio를 UTF-8(errors=replace)로 재구성한다(tdd-gate R4의 cp949 장애 교훈 공유). 의도적 차단은 exit 65 전용(인터프리터 실패 코드 1·2와 구분 — tdd-gate R1 근거 동일).
- R5: 차단 시 stderr에 파일명·패턴 종류·해당 줄 번호 힌트와 조치(① 시크릿 제거 후 재커밋 ② 오탐이면 사용자 확인 후 `[secret-ok]`)를 안내한다. **시크릿 값 자체는 출력하지 않는다**(마스킹 — 터미널 로그도 기록면이다).
- R6: 회귀 테스트 `.agents/githooks/secret-gate_test.py` — 훅 수정 시 반드시 통과(tdd-gate R7 동일).

## 인터페이스 / 설계 개요

- 등록: 기존 전역 `core.hooksPath` → `.agents/githooks/`를 그대로 사용 — **신규 머신 설정 불필요**(shim에 게이트 하나가 추가될 뿐). shim은 게이트 파일 부재 시 통과(R4).
- 입력: argv `--commit-msg <메시지 파일>`, cwd = 워크트리 루트. 출력: exit 0(통과) / exit 65 + stderr 안내(차단).
- 부수 효과 없음 — git 조회 명령만 실행.
- **알려진 한계**: ① 형식 없는 시크릿(평문 비밀번호, 사내 규격 토큰)은 잡지 못한다(비목표 — 문서 규칙·리뷰 몫). ② `[secret-ok]`가 메시지에 있으면 그 커밋의 다른 진짜 시크릿도 통과한다(태그는 커밋 단위 — 부분 승인 없음, tdd-gate `[no-test]`와 동일한 한계). ③ `++`로 시작하는 추가 줄은 diff 원문에서 `+++`가 되어 파일 헤더로 파싱되므로 그 줄의 스캔이 누락된다(fail-open 방향의 희귀 케이스 — 리뷰어 F3, 2026-07-18).

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1·R2): AWS 키 형식이 든 줄을 스테이징 → exit 65, stderr에 파일명·패턴 종류(값은 마스킹).
- [x] C2 (R1): 시크릿 없는 diff → exit 0.
- [x] C3 (R3): 메시지에 `[secret-ok]` → exit 0.
- [x] C4 (R2): 개인키 블록(`BEGIN OPENSSH PRIVATE KEY` 헤더 — 이 문서에서 대시 접두를 생략한 이유: 원형 표기는 게이트 자신에게 걸려 이 스펙의 커밋이 차단된다) → exit 65.
- [x] C5 (R1): 시크릿이 **삭제 줄에만** 있음 → exit 0 (제거 커밋 통과).
- [x] C6 (R3): 최초 커밋(HEAD 없음)에 시크릿 → exit 65 (예외 아님).
- [x] C7 (R4): 메시지 파일 없음 → exit 0.
- [x] C8 (R3): MERGE_HEAD 진행 상태 → exit 0.
- [x] C9 (R2): GitHub 토큰(`ghp_…`)·Slack(`xoxb-…`) → exit 65.
- [x] C10 (R4): 바이너리 파일 스테이징 → exit 0 (크래시 없음).
- [x] C11 (R1·R6): shim 통합 — `core.hooksPath` 경유 `git commit` 시 시크릿 커밋이 실제 차단되고, `[secret-ok]` 메시지로는 통과한다.
- [x] C12 (R5): 차단 stderr에 시크릿 원문이 포함되지 않는다.
