# ADR 047: autoloop 관측 상태와 로컬 대시보드 분리

- **날짜**: 2026-08-19
- **변경 내용**: autoloop 드라이버가 현재 런의 관측 상태를 `run-status.json`에 원자 기록하고, 별도 Python 표준 라이브러리 서버가 기존 작업 산출물과 함께 읽어 loopback 전용 대시보드로 제공한다. autoloop의 동사는 `start/dashboard/status/stop` 네 가지가 된다.
- **대상**: `.agents/skills/autoloop/SKILL.md`, `.agents/skills/autoloop/scripts/{driver.py,driver_test.py,dashboard.py,dashboard_test.py}`, `.agents/skills/README.ko.md`, `docs/specs/{2026-07-19-autoloop-driver.md,2026-08-19-autoloop-dashboard.md}`, `docs/adr/025-autoloop-driver.md`, `docs/README.md`, `_workspace/harness-ops-log.md`
- **사유**: 기존 `state.json`은 재기동 시 게이트를 이어받는 내부 체크포인트다. 화면이 필요한 최신 단계·남은 항목을 이 파일에서 추론하면 판정용 `prev_open`을 표시값으로 오독하고, 표시 요구가 게이트 스키마를 끌고 다니게 된다. 관측 상태를 분리하면 대시보드 고장이 루프 판정을 바꾸지 않으며, 기존 작업 디렉터리도 변환 없이 읽을 수 있다.

## 결정

1. `state.json`은 정체·예산·피드백을 이어받는 게이트 정본으로 유지한다.
2. `run-status.json`은 현재 런의 PID·단계·반복·종료 사유를 담는 표시 전용 스냅샷이다. 기록 실패는 경고만 남기고 루프 종료 사유를 바꾸지 않는다.
3. 남은 항목과 테스트 결과는 최신 `iters/iter-N.json`을 표시 정본으로 삼는다.
4. 대시보드는 Python 3 표준 라이브러리만 사용하고 `127.0.0.1`에만 바인딩한다. 외부 공개와 변경 API는 제공하지 않는다.
5. 에이전트 출력과 로그는 신뢰하지 않는 데이터다. API는 JSON으로 전달하고 브라우저는 DOM `textContent`로만 표시한다.
6. `run-status.json`이 없는 과거 작업은 `launch.log` 종료 줄과 PID 생존 여부로 보수적으로 표시한다. `driver.pid` 파일의 존재만으로 실행 중이라고 판단하지 않는다.
7. loopback 바인딩만으로 브라우저의 로컬 접근 경계를 주장하지 않는다. 비-loopback `Host`를 거부하고 상태·로그·반복 파일의 심볼릭 링크도 거부한다.
8. 목록은 최신 반복 하나만, 상세는 최근 200개만 읽는다. 자동 갱신은 일시정지할 수 있고 카드 포커스를 복원한다.
9. 누적 비용의 측정 범위를 체크포인트에 이어받고 반복별로도 기록한다. 미측정 이력이 있는 작업을 `$0.00` 또는 완전 측정으로 표시하지 않는다.

## 결과

- 사용자는 여러 autoloop 작업의 현재 단계와 최신 검증 증거를 한 화면에서 비교할 수 있다.
- 대시보드는 제어면이 아니므로 기존 STOP·승인·파괴 작업 가드레일을 우회할 경로가 생기지 않는다.
- 일반 orchestrate 팀 통합과 작업 제어는 별도 결정 전까지 범위 밖이다.

## 영향

`.agents/skills/autoloop/SKILL.md`, `.agents/skills/autoloop/scripts/driver.py`, `.agents/skills/autoloop/scripts/driver_test.py`, `.agents/skills/autoloop/scripts/dashboard.py`, `.agents/skills/autoloop/scripts/dashboard_test.py`, `.agents/skills/README.ko.md`, `docs/specs/2026-07-19-autoloop-driver.md`, `docs/specs/2026-08-19-autoloop-dashboard.md`, `docs/adr/025-autoloop-driver.md`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/harness-ops-log.md`
