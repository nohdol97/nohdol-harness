# 스펙: harness-review-reminder 훅 — 주간 점검 자동 트리거

- 날짜: 2026-07-14 / 상태: 구현됨
- 관련: 루트 AGENTS.md 8절(주 1회 관찰), harness-review SKILL.md, docs/specs/2026-07-14-agentsview-daemon-hook.md(훅 규격 선례)

## 배경

8절은 진화 트리거 3신호를 "주 1회 관찰"하는 운영 습관을 요구하지만, 실행이 사용자 기억("주간 점검"이라고 말하기)에 의존한다 — 기억 의존 습관은 몇 주 안에 증발한다(사용자 요청, 2026-07-14: cron화). OS cron + 헤드리스 실행 대신 **SessionStart 훅이 경과를 판정해 세션 컨텍스트에 실행 지시를 주입**하는 방식을 택한다. 이유: ① harness-review의 제안은 사용자 승인이 필수(무단 생성 금지)라 사람이 있는 세션에서 돌아야 하고 ② 신호 데이터(agentsview DB·REGISTRY.md·`_workspace/`)가 로컬 세션 환경에 있으며 ③ 무인 헤드리스 실행은 승인자 없이 토큰만 소모하고 ④ OS 3종(cron/launchd/작업 스케줄러) 등록은 유지 비용이 크다.

## 목표

- **2단 주기 자동 트리거** (2026-07-14 사용자 확정 — "일주일은 너무 길다"): ① 마지막 **전체 점검** 후 7일 경과 → 전체 모드(신호+무결성) 지시 주입. ② 전체는 7일 이내지만 마지막 점검 후 1일 경과 → **일일 경량 모드**(마지막 점검 이후의 확장 신호 ①~③ 스캔만 — ④ 수축·효율은 3주 관찰 창이 필요해 주간의 몫) 지시 주입.
- 둘 다 기한 내면 점검 지시 대신 **상태 한 줄**(마지막 점검 시점·기한 전 안내·운영 로그 위치)을 주입하고, 첫 응답에서 사용자에게 훅 상태를 한 줄로 알리게 한다 — 침묵은 "정상 동작"과 "훅 미실행"을 구분 불가능하게 만든다(2026-07-14 사용자 요청: 동작 여부가 채팅에 남아야 함).

## 비목표

- 무인(헤드리스) 자동 실행 — 제안 승인에 사람이 필요하다. 훅은 트리거만 하고 실행은 세션의 모델이 한다.
- Codex 세션 트리거(훅은 Claude Code 계층 — tdd-gate·agentsview-daemon과 동일 제약).
- 점검 자체의 수행(harness-review 스킬의 몫).

## 요구사항

- R1: 마커 2개 — 전체 `_workspace/.harness-review-last`, 일일 `_workspace/.harness-review-daily-last`(내용: `YYYY-MM-DD` 한 줄) — 로 각각 경과일을 계산한다. 기준 디렉토리는 `CLAUDE_PROJECT_DIR`(부재 시 cwd).
- R2: 마커가 없거나 내용이 파싱 불가하면 해당 주기의 "기록 없음"(경과)으로 간주한다(첫 설치·유실 시 즉시 점검 유도).
- R3: 모드 판정 — 전체 마커 7일 이상(또는 기록 없음)이면 **full**, 아니고 일일 마커 1일 이상(또는 기록 없음)이면 **daily**, 둘 다 아니면 **상태 한 줄**(점검 지시 아님 — 마지막 점검 시점, 기한 전 안내, `_workspace/harness-ops-log.md` 참조, 사용자 보고 지시). full·daily 지시에는 **첫 응답에서 점검 서브에이전트를 백그라운드로 즉시 발행**(harness-review 스킬 '실행 방식' 절 — 메인 루프 직접 수행 금지, 사용자 요청 병행 처리)과 완료 시 결과의 채팅 보고, 마커·운영 로그 갱신 주체(서브에이전트)와 확인 안내를 포함한다 — 훅은 모델을 깨우지 못하므로 지시는 첫 사용자 턴에서 소비되는데, 메인 루프 직접 수행은 첫 응답을 점검이 점유해 사용자 요청과 경합한다(2026-07-14 사용자 확정: 서브에이전트 위임).
- R4: fail-open — 예외 발생 시 무출력 exit 0. 어떤 경우에도 exit 0(세션 시작을 막지 않는다). 시작 시 stdout을 **UTF-8(errors=replace)로 재구성**한다 — 한글 Windows 콘솔(cp949)은 메시지의 em dash를 인코딩하지 못해 print가 예외를 던지고, fail-open이 그것을 삼켜 리마인더가 **무출력으로 조용히 죽는다**(2026-07-14 장애 — exit 0이라 발견도 안 됨).
- R5: 마커 갱신은 harness-review 스킬이 점검 완료 시 수행한다(전체 → 두 마커, 일일 → 일일 마커. 이 훅은 읽기 전용).
- R6: 회귀 테스트가 `.agents/hooks/harness-review-reminder_test.py`로 영속되어야 한다.

## 인터페이스 / 설계 개요

- 등록: 루트 `.claude/settings.json` → SessionStart, command는 **인터프리터 탐색 체인** `for p in python3 python py; do "$p" -c "" >/dev/null 2>&1 && exec "$p" "$CLAUDE_PROJECT_DIR/.agents/hooks/harness-review-reminder.py"; done; exit 0` (agentsview-daemon과 병렬 등록) — `.py` 직접 실행은 Windows(파일 연결·PATHEXT 부재)에서 인터프리터 진입 전에 실패하고, 존재 확인(`command -v`)만으로는 Windows Store App Execution Alias 스텁(PATH에 있지만 실행하면 "Python was not found" exit 49)을 통과시킨다 — 그래서 **실행 확인**(`-c ""`)으로 판별한다. 인터프리터 부재 시 exit 0(fail-open).
- 입력: 없음(stdin 무시). 출력: 경과 시 stdout 한 줄(세션 컨텍스트로 주입됨), 아니면 무출력. 항상 exit 0.
- 부수 효과 없음 — 파일 읽기뿐(R5: 쓰기는 스킬이 담당).

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1·R3): 전체 마커 8일 전(일일은 오늘) → **전체 모드** 지시 출력(경과일·두 마커 갱신 안내 포함), exit 0.
- [x] C2 (R3): 전체 마커 2일 전 + 일일 마커 1일 전 → **일일 경량 모드** 지시 출력, exit 0.
- [x] C3 (R2): 마커 둘 다 부재 → "기록이 없습니다" 전체 모드 지시, exit 0.
- [x] C4 (R3): 두 마커 모두 오늘 → 점검 지시 없는 **상태 한 줄** 출력("기한 전"·운영 로그 참조 포함, 0일은 "오늘" 표기), exit 0.
- [x] C5 (R2): 전체 마커 내용이 날짜가 아님 → 전체 모드 지시, exit 0.
- [x] C6 (R4): 기준 디렉토리 접근 예외 → 무출력, exit 0.
- [x] C7 (R6): `python3 .agents/hooks/harness-review-reminder_test.py` 전 케이스 통과.
- [x] C8 (R4): cp949 stdout(한글 Windows 콘솔) → 메시지가 UTF-8로 실제 출력됨(무출력 아님), exit 0.

## 미해결 질문

- **Codex 훅 계층 — 리마인더 부분 채택됨(2026-07-16, ADR 019)**: Codex CLI v0.114+가 동일 포맷(`hooks.EventName[].hooks[].command`)의 SessionStart 훅과 **stdout → developer context 주입**을 지원함을 확인해, 이 리마인더와 `worklog-reminder`를 `.codex/hooks.json`(추적)에 등록했다. 훅 스크립트는 이미 도구 무관(fail-open·stdout·`os.getcwd()` 폴백)이라 무변경. 활성화는 머신 로컬(`~/.codex/config.toml`의 `[features] codex_hooks = true`, harness-install 1단계)이고 **실험 기능·Windows 미지원**이라 macOS·Linux 한정이다. **남은 대기 관찰**: ① macOS Codex 세션에서 실제 주입되는지 실측 검증(원격 컨테이너엔 Codex 미설치 — harness-updates.md 대기 항목). ② `agentsview-daemon`은 agentsview가 Codex 세션을 관측하는지 미확인이라 Codex 병행에서 제외 — 확인 시 편입. tdd-gate는 git commit-msg 계층 단일화(ADR 014·015)로 이미 도구 무관.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-14 | 초안 작성 및 구현 | 전체 | 사용자 요청(주간 점검 cron화) — 승인 필요성·로컬 데이터·토큰 비용 근거로 세션 트리거 방식 채택 |
| 2026-07-14 | 2단 주기로 확장 — 일일 경량(1일, 3신호 스캔만) + 주간 전체(7일), 마커 2개·모드 판정 R3 개정 | 목표, R1~R3·R5, C1~C7 | 사용자 확정 — "일주일은 너무 길다, 비효율은 매일 점검" |
| 2026-07-14 | 등록 command를 인터프리터 탐색 체인(python3→python→py, 부재 시 exit 0)으로 변경 | 인터페이스(등록), .claude/settings.json | Windows 설치처 장애 보고 — `.py` 직접 실행이 파일 연결·PATHEXT 부재로 OS 수준 실패 |
| 2026-07-14 | 인터프리터 판별을 존재 확인(command -v)에서 실행 확인(-c "")으로 강화 | 등록, .claude/settings.json | Windows 재발 보고 — Store App Execution Alias 스텁이 존재 확인을 통과해 exec 후 exit 49로 실패 |
| 2026-07-14 | 기한 전 침묵을 상태 한 줄로 개정 + 지시 메시지에 운영 로그(harness-ops-log.md) 안내 추가 | 목표, R3, C4 | 사용자 요청 — 훅 동작 여부와 점검·개선 내역이 채팅에 남아야 함. 침묵은 정상과 미실행을 구분 불가 |
| 2026-07-14 | stdio UTF-8 재구성, C8(cp949) 신설 | R4, C8 | 한글 Windows 장애 보고 — cp949 콘솔에서 em dash가 UnicodeEncodeError, fail-open이 삼켜 리마인더가 무출력으로 죽음 |
| 2026-07-14 | 지시문에 첫 응답 우선 실행·미룸 시 명시적 확인 문구 추가 | R3, C1·C2 | 사용자 관찰 — 마커 부재인데 세션에서 점검 미실행. 훅 주입 지시가 사용자 요청과 경합할 때 밀리지 않도록 우선순위를 문구로 고정 |
| 2026-07-14 | 지시문을 서브에이전트 발행 방식으로 개정 — 백그라운드 점검 + 사용자 요청 병행, 마커·로그 갱신 주체는 서브에이전트 | R3, C1·C2 | 사용자 확정 — 메인 루프 직접 수행은 첫 응답을 점검이 점유. 실행 절차 단일 원본은 harness-review 스킬 '실행 방식' 절 |
| 2026-07-14 | 신호 체계 4신호 확장 반영 — 일일은 확장 ①~③, 수축·효율 ④는 주간 한정으로 문구 갱신 | 목표, daily 지시문 | 8절 개정(ADR 013) — 일일 비용을 늘리지 않으면서 신호 범위만 정확히 표기 |
| 2026-07-15 | utf8_stdio를 `_common.py` import로 전환(유실 시 no-op 폴백) + Codex 훅 계층 대기 관찰 항목 기록 | 훅 구현, 미해결 질문 | 일일 점검 신호 ②(공통 로직 복제로 fix 3연쇄) — 스펙 2026-07-15-hooks-common-bootstrap. Codex v0.114+ 훅 도입으로 비목표 전제 변동(실험·Windows 미지원이라 보류) |
| 2026-07-16 | Codex 훅 계층 리마인더 부분 채택 — 이 리마인더를 `.codex/hooks.json`에 등록(스크립트 무변경), 미해결 질문을 채택 상태로 갱신(agentsview-daemon·macOS 실측은 잔여) | 미해결 질문 | 사용자 요청(맥북 Codex 병행) — Codex SessionStart 포맷·stdout 주입 확인. docs/adr/019 |
