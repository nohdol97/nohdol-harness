# ADR 050: autoloop 계획 자동 수정과 파일 범위 기반 wave 직렬화

- **날짜**: 2026-08-20
- **변경 내용**: 첫 planner DAG가 구조 검증에 실패하면 오류를 포함해 read-only planner를 한 번만 다시 실행한다. 쓰기 task는 `file_scope`를 선언하고 겹치는 writer를 다른 wave로 직렬화하며 실제 patch가 선언 범위를 벗어나면 fan-in 전에 차단한다.
- **대상**: `.agents/skills/autoloop/{SKILL.md,scripts/driver.py,scripts/driver_test.py}`, `.agents/skills/README.ko.md`, `docs/specs/2026-08-19-autoloop-orchestration-runtime.md`, `docs/adr/{048-autoloop-structured-orchestration.md,050-autoloop-plan-repair-and-scope-aware-waves.md}`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/harness-ops-log.md`
- **사유**: CareOS autoloop에서 criterion 없는 planner task가 mutation 전 검증에 걸렸고, 재기동 뒤 같은 `src/server.js`와 `test/http-journey.test.js`를 수정한 두 writer가 같은 wave에 배치되어 fan-in에서 충돌했다. 기존 검증과 worktree 격리는 손상을 막았지만 사용자를 두 번 호출했다. 실패를 더 안전하게 막는 데서 끝내지 않고, mutation 전 자동 수정과 실제 충돌 전 직렬화로 사용자 개입 자체를 줄인다.

## 결정

1. planner의 첫 구조 오류는 사용자 차단이 아니라 한 번의 bounded read-only 재계획 입력이 된다. 정확한 오류 목록과 criterion ID를 전달하고 두 번째 실패에서만 `blocked`한다.
2. 재계획은 최대 한 번이다. 무한 계획 루프와 비용 상한 우회를 만들지 않는다.
3. 모든 쓰기 task는 저장소 상대 정확 경로 또는 `디렉터리/**` 형식의 `file_scope`를 선언한다. 읽기 task는 빈 범위를 허용한다.
   이 필드가 없던 계약과 새 계약을 같은 이름으로 취급하지 않도록 bounded contract를 `autoloop-orchestrate-v2`로 올리고, v1의 활성 계획은 자동 병렬 재개하지 않는다.
4. ready writer의 scope가 겹치면 plan 순서상 뒤 task를 다음 wave로 보낸다. read task와 비중첩 writer는 agent budget 안에서 병렬성을 유지한다.
5. 실제 patch 경로가 선언 scope 밖이면 writer 결과를 실패로 기록하고 integration worktree 생성 전에 멈춘다. 선언을 낙관적으로 좁혀 병렬성을 얻는 우회를 허용하지 않는다.
6. 기존 fan-in 충돌 차단은 마지막 안전망으로 유지한다. scope 직렬화는 그 gate를 완화하거나 자동 merge로 대체하지 않는다.

## 결과

- planner의 사소한 구조 누락은 mutation 없이 스스로 한 번 수정된다.
- 같은 큰 파일을 고치는 독립 기능은 각자 직전 통합 commit을 base로 받아 patch 충돌 가능성이 줄어든다.
- 병렬성은 agent 수만이 아니라 실제 쓰기 소유권으로 제한되고, 직렬화 이유가 dashboard artifact에 남는다.
- 잘못 선언한 scope는 조용한 경계 확장이 아니라 명시적 task 실패가 된다.

## 영향

`.agents/skills/autoloop/SKILL.md`, `.agents/skills/autoloop/scripts/driver.py`, `.agents/skills/autoloop/scripts/driver_test.py`, `.agents/skills/README.ko.md`, `docs/specs/2026-08-19-autoloop-orchestration-runtime.md`, `docs/adr/048-autoloop-structured-orchestration.md`, `docs/adr/050-autoloop-plan-repair-and-scope-aware-waves.md`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/harness-ops-log.md`
