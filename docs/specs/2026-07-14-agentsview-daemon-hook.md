# 스펙: agentsview-daemon 훅 — 세션 시작 시 동기화 데몬 자동 기동

- 날짜: 2026-07-14 / 상태: 구현됨
- 관련: docs/harness-changelog.md(2026-07-14 agentsview 연동 행 — 변경 이력은 ADR 021로 분리됨), harness-install 3단계, docs/specs/2026-07-13-tdd-gate-hook.md(훅 규격 선례)

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
- R2: `agentsview daemon status`로 실행 여부를 판정하고, 실행 중이면 아무것도 하지 않는다. 판정은 **부정문 우선 배제**여야 한다 — 정상 종료코드 + 부정문 부재("not running" / "No … is running."(v0.38.1 실측 정지 문구) / "stopped") + running 표기. 긍정 substring 단독 판정은 부정문까지 실행 중으로 오판해 재기동을 영원히 건너뛴다(2026-07-14 오판정 장애). 문구가 버전마다 달라 판정이 애매하면 미실행 쪽으로 기운다 — 중복 start 시도(무해)가 죽은 데몬 방치보다 낫다.
- R3: 미실행이면 `agentsview daemon start`를 **분리(detached)** 실행한다 — 훅 프로세스가 데몬을 기다리지 않는다. POSIX는 새 세션, Windows는 DETACHED_PROCESS.
- R4: fail-open — status 타임아웃(10초)·예외·기동 실패 전부 exit 0, 예외 경로는 무출력. **nominal 경로(미설치·이미 실행 중)도 침묵한다** — 매 세션 상태 줄은 노이즈다(2026-07-16 사용자 결정, 세션 훅 공통 원칙 "nominal은 침묵" — worklog 스펙·리마인더 스펙과 정렬. 2026-07-14의 "정상 경로 상태 한 줄" 가시화 결정을 재개정: 특히 agentsview 미설치 설치처는 그 줄이 영구 반복된다). 출력이 남는 유일한 경로는 **상태 전이(재기동) 한 줄**이다. **print를 포함한 main 전 구간이 try 안**이어야 하고, 시작 시 stdout/stderr를 **UTF-8(errors=replace)로 재구성**한다 — 한글 Windows 콘솔(cp949)은 기동 줄의 em dash를 인코딩하지 못해 print 자체가 예외를 던진다(2026-07-14 장애: try 밖 print가 크래시 → 매 세션 hook error).
- R5: 회귀 테스트가 `.agents/hooks/agentsview-daemon_test.py`로 영속되어야 하며, 훅 수정 시 통과해야 한다.

## 인터페이스 / 설계 개요

- 등록: 루트 `.claude/settings.json` → SessionStart, command는 **인터프리터 탐색 체인** `for p in python3 python py; do "$p" -c "" >/dev/null 2>&1 && exec "$p" "$CLAUDE_PROJECT_DIR/.agents/hooks/agentsview-daemon.py"; done; exit 0` — `.py` 직접 실행은 Windows(파일 연결·PATHEXT 부재)에서 인터프리터 진입 전에 실패하고, 존재 확인(`command -v`)만으로는 Windows Store App Execution Alias 스텁(PATH에 있지만 실행하면 "Python was not found" exit 49)을 통과시킨다 — 그래서 **실행 확인**(`-c ""`)으로 판별한다. 인터프리터 부재 시 exit 0(fail-open).
- 입력: 사용하지 않음(stdin JSON 무시 — 판정에 불필요). 출력: 항상 exit 0. 재기동 시에만 상태 한 줄, 그 외(미설치·실행 중·예외)는 무출력(R4).
- 부수 효과: 데몬 프로세스 기동뿐. 데이터는 agentsview 기본값대로 로컬(`~/.agentsview/`)에만 쓰인다.

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1·R4): 바이너리 부재 → start 미호출, **무출력**, exit 0.
- [x] C2 (R2·R4): status가 running 보고 → start 미호출, **무출력**, exit 0.
- [x] C3 (R2·R3·R4): status 비정상/미실행 보고 → start 1회 호출, "기동" 상태 한 줄, exit 0. rc 0 + "not running" 출력도 미실행으로 판정. **실제 CLI 정지 문구 "No agentsview daemon is running."(rc 0)도 미실행으로 판정해 재기동** — 픽스처는 실측 문구를 쓴다(가공 문구만 쓰면 이 케이스를 못 잡는다).
- [x] C4 (R4): status 예외(타임아웃 등) → exit 0.
- [x] C6 (R4): cp949 stdout(한글 Windows 콘솔)에서 재기동 → 크래시 없이 기동 한 줄 출력(UTF-8), exit 0. (구 문서의 중복 ID "C5" 2건을 C6·C7로 재부여 — 2026-07-16)
- [x] C7 (R5): `python3 .agents/hooks/agentsview-daemon_test.py` 전 케이스 통과.

## 미해결 질문

없음.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-14 | 초안 작성 및 구현 | 전체 | 사용자 요청 — 동기화 수동 기동 제거. 13절 1항(스펙 먼저) |
| 2026-07-14 | 등록 command를 인터프리터 탐색 체인(python3→python→py, 부재 시 exit 0)으로 변경 | 등록(설계 개요), .claude/settings.json | Windows 설치처 장애 보고 — `.py` 직접 실행이 파일 연결·PATHEXT 부재로 OS 수준 실패 |
| 2026-07-14 | 인터프리터 판별을 존재 확인(command -v)에서 실행 확인(-c "")으로 강화 | 등록, .claude/settings.json | Windows 재발 보고 — Store App Execution Alias 스텁이 존재 확인을 통과해 exec 후 exit 49로 실패 |
| 2026-07-14 | 정상 경로 무출력을 상태 한 줄 출력으로 개정(예외 경로만 무출력 유지) | R4, C1~C3 | 사용자 요청 — 훅 동작 여부가 채팅에 남아야 함. 전면 무출력은 정상과 미실행을 구분 불가 |
| 2026-07-14 | stdio UTF-8 재구성 + main 전 구간 try 포함, C5(cp949) 신설 | R4, C5 | 한글 Windows 장애 보고 — cp949 콘솔에서 상태 줄의 em dash가 UnicodeEncodeError, try 밖 print라 fail-open 미적용 크래시 |
| 2026-07-14 | 실행 판정을 부정문 우선 배제로 재작성, 실측 정지 문구 픽스처 추가 | R2, C3 | 오판정 장애 보고 — "No agentsview daemon is running."(v0.38.1)이 "running"을 포함해 죽은 데몬을 실행 중으로 오판, 재기동 무력화. 가공 픽스처가 실제 문구와 달라 회귀 테스트가 못 잡음 |
| 2026-07-15 | utf8_stdio를 `_common.py` import로 전환(유실 시 no-op 폴백) | 훅 구현 | 일일 점검 신호 ②(공통 로직 복제로 fix 3연쇄) — 스펙 2026-07-15-hooks-common-bootstrap. Codex 훅 계층 대기 관찰은 리마인더 스펙 미해결 질문에 일원 기록 |
| 2026-07-15 | status 서브프로세스에 `encoding="utf-8"` 명시(errors=replace) | 훅 구현 | tdd-gate C15와 동일 클래스(로케일 의존 자식 출력 디코딩) 일괄 점검 — 출력이 ASCII라 동작 변화는 없으나 비의존을 규약으로 고정 |
| 2026-07-16 | nominal(미설치·실행 중) 무출력 재개정 — 출력은 재기동 한 줄만(2026-07-14 상태 한 줄 결정 되돌림), 인터페이스 "무출력" 모순 문구 정합, 중복 완료 기준 ID C5→C6·C7 재부여, 관련 포인터를 harness-changelog.md로 갱신 | R4, C1·C2·C6·C7, 인터페이스, 훅·테스트 | 사용자 결정(2026-07-16, 하네스 전체 감사 HOOK-F4) — "이미 했다/미설치" 상태 줄이 매 세션 노이즈. 리마인더·worklog 훅과 같은 "nominal은 침묵" 원칙으로 정렬 |
