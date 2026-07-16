# 스펙: 훅 공통 부트스트랩 모듈(`_common.py`)

- 날짜: 2026-07-15 / 상태: 구현됨
- 관련: docs/specs/2026-07-13-tdd-gate-hook.md, 2026-07-14-agentsview-daemon-hook.md, 2026-07-14-harness-review-reminder-hook.md / harness-review 일일 점검 제안(2026-07-15, 신호 ②)

## 배경

훅 3종(tdd-gate·agentsview-daemon·harness-review-reminder)이 stdio UTF-8 재구성 로직을 각자 복제해 갖고 있었다. 2026-07-14 cp949 장애 수정(df509e4)이 **같은 수정을 3개 파일에 반복 적용**해야 했던 것이 증거다 — 공통 로직이 훅마다 복제되면 한 번의 결함이 N배 수정 비용으로 증폭되고, 하나만 고치고 나머지를 빠뜨리는 부분 수정 위험이 생긴다(일일 점검 2026-07-15, 신호 ② fix 3연쇄).

## 목표

- 훅 공통 부트스트랩(현재는 stdio UTF-8 재구성)의 **단일 원본**을 `.agents/hooks/_common.py`에 둔다. 훅 4종(2026-07-16 worklog-reminder 편입)은 이를 import해 쓴다.
- 공통 모듈이 유실·손상돼도 훅은 죽지 않는다(fail-open 유지) — 훅은 세션 시작·커밋을 막지 않는 것이 최우선 계약이다.

## 비목표

- 인터프리터 판별의 파이썬화 — 인터프리터 탐색은 `.claude/settings.json`의 셸 체인 몫이다(파이썬 진입 전 문제라 파이썬으로 풀 수 없다).
- 훅별 고유 로직(마커 계산, 데몬 판정 정규식, 커밋 파싱)의 공통화 — 공유되지 않는 것을 모으면 결합만 생긴다.
- 패키지화(`__init__.py`, pip 설치) — 훅은 단일 파일 스크립트 계층을 유지한다.

## 요구사항

- R1: `_common.py`는 `utf8_stdio()`를 제공한다 — stdout·stderr를 UTF-8(errors=replace)로 재구성, 재구성 불가 스트림은 무시. 동작은 기존 훅 내장 구현과 동일(각 훅 스펙의 cp949 완료 기준이 회귀 기준).
- R2: 훅 4종은 내장 정의를 제거하고 `_common`에서 import한다(worklog-reminder는 2026-07-16 신설과 함께 편입). 세션 훅 3종(agentsview-daemon·harness-review-reminder·worklog-reminder)은 같은 디렉토리라 스크립트 직접 실행(`sys.path[0]`=훅 디렉토리)만으로 충분하고, git 훅 계층의 `githooks/tdd-gate.py`(ADR 015)와 각 테스트 스위트(`_common_test.py`·`githooks/tdd-gate_test.py`)는 hooks/ 디렉토리가 sys.path[0]이 아니므로 **파일 위치 기준 sys.path 삽입** 후 import한다.
- R3: import는 fail-open이어야 한다 — `_common.py` 부재·손상 시 no-op 폴백으로 대체하고 훅 본연의 동작은 계속한다(cp949 보호만 상실, 세션·커밋은 막지 않음).
- R4: 훅 4종의 기존 회귀 테스트(cp949 케이스 포함)가 수정 없이 전부 통과한다 — 동작 불변 리팩토링임의 증명.
- R5: 회귀 테스트가 `.agents/hooks/_common_test.py`로 영속되어야 한다.

## 인터페이스 / 설계 개요

- `.agents/hooks/_common.py` — `utf8_stdio()` 단일 함수. 훅이 아니므로 `.claude/settings.json`에 등록하지 않는다.
- 각 훅 상단: `try: from _common import utf8_stdio / except Exception: def utf8_stdio(): pass` (R3 폴백).
- 훅 스펙 공통 완료 기준(재발 방지, 일일 점검 제안 2-2): 신규·수정 훅 스펙은 **크로스 플랫폼 체크리스트**를 완료 기준에 포함한다 — ① cp949(한글 Windows) 인코딩 케이스 ② 인터프리터 부재·Store 스텁(등록 command 계층) ③ 외부 CLI 출력 판정은 실측 문구 fixture(긍정·부정문 모두). 템플릿 원본: doc-writer `references/templates.md` 스펙 절.

## 완료 기준 (테스트 가능한 형태)

- [x] C1 (R1): cp949 TextIOWrapper를 stdout으로 두고 `utf8_stdio()` 호출 후 em dash 포함 문자열을 print하면 UTF-8 바이트로 실제 출력된다.
- [x] C2 (R1): reconfigure 불가 스트림(StringIO)에서 `utf8_stdio()`가 예외 없이 통과한다.
- [x] C3 (R2): 훅 4종이 로드 시 `_common.utf8_stdio`와 동일 객체를 사용한다(복제본 아님 — worklog-reminder 포함, 2026-07-16 감사 HOOK-F5로 편입).
- [x] C4 (R3): `_common` import가 차단된 상태로 훅을 로드해도 로드가 성공하고 `utf8_stdio()` 호출이 예외를 던지지 않는다.
- [x] C5 (R4): 훅 4종 기존 테스트 전 케이스 통과(`harness-review-reminder_test.py` 18, `agentsview-daemon_test.py` 14, `tdd-gate_test.py` 25 — C15는 2026-07-15 로케일 수정에서 추가, tdd-gate 스펙 소관).

## 미해결 질문

없음.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-07-15 | 초안 작성 및 구현 | 전체 | 일일 점검 신호 ②(cp949 수정이 훅 3종 반복 적용된 fix 연쇄) — 공통 로직 단일 원본화, 사용자 승인 |
| 2026-07-16 | worklog-reminder를 단일 원본 보증 범위에 편입 — HOOK_FILES 4종화, 문서 수치 갱신 | R2·R4, C3·C5, _common.py, _common_test.py | 하네스 전체 감사 HOOK-F5 — 4번째 훅이 보증 밖에 있어 복제 발산이 재발할 지점. 사용자 승인 |
| 2026-07-15 | tdd-gate의 git 계층 이동(main ADR 014·015)과 병합 — R2를 세션 훅 동일 디렉토리 / githooks 교차 디렉토리(sys.path 삽입)로 개정 | R2, 훅 경로 | main 선반영 개편과의 충돌 해소 — 의도(단일 원본)를 새 구조로 번역 |
| 2026-07-15 | 문서 정합 정정 — C5의 tdd-gate 테스트 수 24→25(C15 추가 반영), R2에 테스트 스위트 importer 명시, `_common.py` docstring을 세션 훅/git 훅/테스트 importer 구분으로 정확화 | C5, R2, _common.py docstring | 문서화 누락 정리(사용자 요청) — 로케일 수정 이후 낡은 수치·불완전 서술 |
