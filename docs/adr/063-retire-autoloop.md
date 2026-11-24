# ADR 063 — autoloop 스킬 폐기

- **날짜**: 2026-11-24
- **상태**: 활성
- **관련**: [ADR 025](025-autoloop-driver.md)·[ADR 047](047-autoloop-observation-dashboard.md)·[ADR 048](048-autoloop-structured-orchestration.md)·[ADR 049](049-autoloop-dashboard-operator-experience.md)·[ADR 050](050-autoloop-plan-repair-and-scope-aware-waves.md)(**이 ADR이 전부 대체**), 스펙 `2026-07-19-autoloop-driver`·`2026-08-03-autoloop-engine-harness-load-symmetry`·`2026-08-19-autoloop-dashboard`·`2026-08-19-autoloop-orchestration-runtime`·`2026-08-19-autoloop-dashboard-operator-ux`(폐기)

## 변경 내용

1. **`.agents/skills/autoloop/` 전체를 삭제했다.** 발사대 스킬, `scripts/`(드라이버·대시보드 서버와 그 시험), `dashboard-ui/`(React 원본·빌드 산출물·시험)가 모두 포함된다. 추적 파일은 22개다. 추적되지 않던 `node_modules/`·`__pycache__/`도 함께 지웠다(다시 만들 수 있는 설치 산출물이다).
2. **라우팅과 규칙에서 autoloop을 뺐다.** `CLAUDE.md` 라우팅 줄, `AGENTS.md` §3(외부 텍스트 봉투의 예시)·§11(Pi 예외·사내 호스트 문단)·§13-4(자기 검증 대상 예시), `orchestrate`(헤드리스 실행 예시·후속 세션 조건 1), `inflight-survey.md`, doc-writer 템플릿의 배포처 절, 스킬 한글 카탈로그, 시험 2건(`token-efficiency-contract_test.py`의 스킬 목록, `pi-profile-contract_test.py`의 Pi 정책 문구 기대값)을 고쳤다. ADR 026·052·053에는 autoloop 조항 부분 대체 표시를 달았다.
3. **`_workspace/autoloop/<작업>/` 정리 예외는 남긴다**(§4). 이 설치처에 지난 실행의 상태 디렉터리가 남아 있고, 예외를 지우면 다음 정리가 사용자 확인 없이 그것을 지울 수 있다. 그 데이터를 지울지는 사용자가 정한다.
4. 이 ADR이 기록하는 근거로 남는 과거 사례 인용(`metaskill` 재작업 신호의 2026-07-26 실측, `diagram` 규칙의 스펙 예시)은 그대로 둔다. 사실을 기록한 것이고, 기능을 안내하지 않는다.

## 사유

**사용자 결정**(2026-11-24): "autoloop 기능은 하네스에서 제거해줘. 미지원이야." 지원하지 않는 기능을 라우팅에 남겨 두면, 무인 실행 요청이 실행할 수 없는 절차로 가고 규칙 본문이 없는 장치를 계속 가정하게 된다.

## 영향

- **무인 멀티세션 실행 경로가 없어진다.** 여러 세션에 걸치는 작업은 `work-tracker`(추적)나 `/carryover`(같은 기기 인계)로 잇는다. 컨텍스트가 찬 세션이 후속 세션을 여는 Paseo 경로(`session-handoff.py`)는 별개라 유지한다.
- **되돌리기**: 이 ADR을 대체하는 ADR과 이 커밋의 revert. 삭제된 파일은 git 이력에 남아 있다.
