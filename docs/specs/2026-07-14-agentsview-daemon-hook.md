# 스펙: agentsview-daemon 훅 — 세션 시작 시 동기화 데몬 자동 기동

- 날짜: 2026-07-14 / 상태: 구현됨
- 관련: 루트 AGENTS.md 변경 이력(2026-07-14 agentsview 연동), harness-install 3단계, docs/specs/2026-07-13-tdd-gate-hook.md(훅 규격 선례)

## 배경

agentsview의 세션 인덱싱(로컬 SQLite 동기화)은 데몬이 떠 있어야 지속된다. 데몬 기동을 사용자가 기억해야 하면 재부팅·새 머신에서 조용히 끊기고, harness-review의 신호 실측이 오래된 데이터로 돌아간다. 세션이 열릴 때마다 실행 계층이 기동을 보장하면 동기화는 "알아서" 된다(사용자 요청, 2026-07-14).

## 목표

- Claude Code 세션 시작 시 agentsview 데몬이 떠 있음을 보장한다 — 수동 `daemon start`·`sync` 불필요.
- 미설치·실패·타임아웃 등 어떤 경우에도 세션 시작을 방해하지 않는다(fail-open).

## 비목표

- agentsview 설치 자체(harness-install 3단계의 몫).
- Codex 세션 보장(훅은 Claude Code 계층 — tdd-gate와 동일 제약. 데몬은 한번 뜨면 상주하므로 Claude 세션이 기동한 데몬을 Codex 세션도 누린다).
- OS 부팅 시 자동 시작(launchd/systemd/서비스 등록) — 세션 시작 훅으로 충분하고, OS별 서비스 관리는 유지 비용이 더 크다.

## 요구사항

- R1: SessionStart 훅으로 실행되어, `agentsview` 바이너리가 PATH에 없으면 아무것도 하지 않고 exit 0.
- R2: `agentsview daemon status`로 실행 여부를 판정하고(정상 종료코드 + 출력에 running 계열 표기, "not running"은 미실행), 실행 중이면 아무것도 하지 않는다.
- R3: 미실행이면 `agentsview daemon start`를 **분리(detached)** 실행한다 — 훅 프로세스가 데몬을 기다리지 않는다. POSIX는 새 세션, Windows는 DETACHED_PROCESS.
- R4: fail-open — status 타임아웃(10초)·예외·기동 실패 전부 exit 0. stdout/stderr로 세션 컨텍스트를 오염시키지 않는다(무출력).
- R5: 회귀 테스트가 `.agents/hooks/agentsview-daemon_test.py`로 영속되어야 하며, 훅 수정 시 통과해야 한다.

## 인터페이스 / 설계 개요

- 등록: 루트 `.claude/settings.json` → SessionStart, command는 **인터프리터 탐색 체인** `for p in python3 python py; do command -v "$p" >/dev/null 2>&1 && exec "$p" "$CLAUDE_PROJECT_DIR/.agents/hooks/agentsview-daemon.py"; done; exit 0` — `.py` 직접 실행은 Windows(파일 연결·PATHEXT 부재)에서 인터프리터 진입 전에 실패한다. 인터프리터 부재 시 exit 0(fail-open).
- 입력: 사용하지 않음(stdin JSON 무시 — 판정에 불필요). 출력: 항상 exit 0, 무출력.
- 부수 효과: 데몬 프로세스 기동뿐. 데이터는 agentsview 기본값대로 로컬(`~/.agentsview/`)에만 쓰인다.

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1): 바이너리 부재 → start 미호출, exit 0.
- [x] C2 (R2): status가 running 보고 → start 미호출, exit 0.
- [x] C3 (R2·R3): status 비정상/미실행 보고 → start 1회 호출, exit 0. rc 0 + "not running" 출력도 미실행으로 판정.
- [x] C4 (R4): status 예외(타임아웃 등) → exit 0.
- [x] C5 (R5): `python3 .agents/hooks/agentsview-daemon_test.py` 전 케이스 통과.

## 미해결 질문

없음.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-14 | 초안 작성 및 구현 | 전체 | 사용자 요청 — 동기화 수동 기동 제거. 13절 1항(스펙 먼저) |
| 2026-07-14 | 등록 command를 인터프리터 탐색 체인(python3→python→py, 부재 시 exit 0)으로 변경 | 등록(설계 개요), .claude/settings.json | Windows 설치처 장애 보고 — `.py` 직접 실행이 파일 연결·PATHEXT 부재로 OS 수준 실패 |
