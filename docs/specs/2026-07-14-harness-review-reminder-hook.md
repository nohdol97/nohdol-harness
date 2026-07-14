# 스펙: harness-review-reminder 훅 — 주간 점검 자동 트리거

- 날짜: 2026-07-14 / 상태: 구현됨
- 관련: 루트 AGENTS.md 8절(주 1회 관찰), harness-review SKILL.md, docs/specs/2026-07-14-agentsview-daemon-hook.md(훅 규격 선례)

## 배경

8절은 진화 트리거 3신호를 "주 1회 관찰"하는 운영 습관을 요구하지만, 실행이 사용자 기억("주간 점검"이라고 말하기)에 의존한다 — 기억 의존 습관은 몇 주 안에 증발한다(사용자 요청, 2026-07-14: cron화). OS cron + 헤드리스 실행 대신 **SessionStart 훅이 경과를 판정해 세션 컨텍스트에 실행 지시를 주입**하는 방식을 택한다. 이유: ① harness-review의 제안은 사용자 승인이 필수(무단 생성 금지)라 사람이 있는 세션에서 돌아야 하고 ② 신호 데이터(agentsview DB·REGISTRY.md·`_workspace/`)가 로컬 세션 환경에 있으며 ③ 무인 헤드리스 실행은 승인자 없이 토큰만 소모하고 ④ OS 3종(cron/launchd/작업 스케줄러) 등록은 유지 비용이 크다.

## 목표

- 마지막 점검 후 7일이 지나면, 다음 세션 시작 시 harness-review 실행 지시가 자동으로 컨텍스트에 주입된다 — 사용자가 기억할 필요가 없다.
- 점검이 7일 이내면 완전히 침묵한다.

## 비목표

- 무인(헤드리스) 자동 실행 — 제안 승인에 사람이 필요하다. 훅은 트리거만 하고 실행은 세션의 모델이 한다.
- Codex 세션 트리거(훅은 Claude Code 계층 — tdd-gate·agentsview-daemon과 동일 제약).
- 점검 자체의 수행(harness-review 스킬의 몫).

## 요구사항

- R1: 마커 파일 `_workspace/.harness-review-last`(내용: `YYYY-MM-DD` 한 줄)를 기준으로 경과일을 계산한다. 기준 디렉토리는 `CLAUDE_PROJECT_DIR`(부재 시 cwd).
- R2: 마커가 없거나 내용이 파싱 불가하면 "기록 없음"으로 간주하고 지시를 출력한다(첫 설치·유실 시 즉시 1회 점검 유도).
- R3: 경과 7일 이상이면 stdout으로 한 줄 지시를 출력한다 — harness-review 실행 지시 + 완료 시 마커 갱신 안내 포함. 7일 미만이면 무출력.
- R4: fail-open — 예외 발생 시 무출력 exit 0. 어떤 경우에도 exit 0(세션 시작을 막지 않는다).
- R5: 마커 갱신은 harness-review 스킬이 점검 완료 시 수행한다(이 훅은 읽기 전용).
- R6: 회귀 테스트가 `.agents/hooks/harness-review-reminder_test.py`로 영속되어야 한다.

## 인터페이스 / 설계 개요

- 등록: 루트 `.claude/settings.json` → SessionStart, command `"$CLAUDE_PROJECT_DIR"/.agents/hooks/harness-review-reminder.py` (agentsview-daemon과 병렬 등록).
- 입력: 없음(stdin 무시). 출력: 경과 시 stdout 한 줄(세션 컨텍스트로 주입됨), 아니면 무출력. 항상 exit 0.
- 부수 효과 없음 — 파일 읽기뿐(R5: 쓰기는 스킬이 담당).

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1·R3): 마커가 8일 전 날짜 → 지시 출력(경과일 포함), exit 0.
- [x] C2 (R3): 마커가 오늘·3일 전 → 무출력, exit 0.
- [x] C3 (R2): 마커 부재 → "기록 없음" 지시 출력, exit 0.
- [x] C4 (R2): 마커 내용이 날짜가 아님 → 지시 출력, exit 0.
- [x] C5 (R4): 기준 디렉토리 접근 예외 → 무출력, exit 0.
- [x] C6 (R6): `python3 .agents/hooks/harness-review-reminder_test.py` 전 케이스 통과.

## 미해결 질문

없음.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-14 | 초안 작성 및 구현 | 전체 | 사용자 요청(주간 점검 cron화) — 승인 필요성·로컬 데이터·토큰 비용 근거로 세션 트리거 방식 채택 |
