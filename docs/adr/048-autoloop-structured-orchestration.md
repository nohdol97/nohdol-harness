# ADR 048: autoloop 구조화 오케스트레이션과 writer 격리

- **날짜**: 2026-08-19
- **변경 내용**: autoloop을 단일 구현 세션 반복에서 구조화 task DAG 기반 scheduler로 확장한다. read-only planner가 `orchestrate` verdict·budget·DAG를 만들고, driver가 검증한 ready set을 병렬 dispatch하며, concurrent writer를 task별 worktree에 격리하고 dashboard가 같은 artifact를 투영한다.
- **대상**: `.agents/skills/autoloop/SKILL.md`, `.agents/skills/autoloop/scripts/{driver.py,driver_test.py,dashboard.py,dashboard_test.py}`, `.agents/skills/README.ko.md`, `docs/specs/{2026-07-19-autoloop-driver.md,2026-08-03-autoloop-engine-harness-load-symmetry.md,2026-08-19-autoloop-dashboard.md,2026-08-19-autoloop-orchestration-runtime.md}`, `docs/adr/{025-autoloop-driver.md,047-autoloop-observation-dashboard.md,048-autoloop-structured-orchestration.md}`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/{autoloop-orchestration-review,harness-ops-log.md}`
- **사유**: 기존 prompt prose는 decomposition·orchestrate·parallelism을 요청할 뿐 실행 여부를 판정하지 않았다. 실제 검토에서 모순 prompt가 통과했고, iteration당 session 하나·loop worktree 하나·loop aggregate dashboard만 관찰됐다. 성공 조건을 모델 재량이 아니라 driver가 검증·소비하는 artifact로 내리면 지원 엔진과 모델 행동에 무관하게 같은 gate가 선다.

## 결정

1. `orchestration.json`을 autoloop scheduling 정본으로 둔다. carryover 문장은 설명용이며 완료·dispatch gate가 아니다.
2. 첫 mutation 전에 read-only planner가 일반 `orchestrate` 계약을 구조화 출력하고 driver가 spec criterion coverage·dependency·cycle을 검증한다.
3. ready task는 agent budget 범위에서 같은 wave에 병렬 실행한다. dependency와 명시된 budget만 직렬화 근거가 될 수 있고, fallback reason을 기록한다.
4. writer 수와 wave 크기에 관계없이 모든 writer마다 detached child worktree를 만든다. 한 writer가 대상 checkout이나 다른 writer의 index·working tree·build artifact를 공유하지 않는다.
5. writer patch는 별도 integration worktree에서 먼저 합성하고 그곳에서 commit hook까지 통과시킨다. 대상 worktree는 사전 clean·HEAD 일치 확인 뒤 그 검증된 commit으로만 fast-forward한다. 합성·hook·승격 실패는 대상 index와 working tree를 건드리지 않고 `blocked`다.
6. child·integration worktree는 무인 삭제하지 않는다. fan-in과 cleanup 상태를 artifact에 남기고 대화형 verified cleanup에 넘긴다.
7. Codex의 `-C`는 대상 task worktree에 유지한다. 루트 하네스 자동 로드 대신 versioned bounded orchestrate contract를 prompt에 주입하고, user config를 무시하며 workspace-write network를 false로 고정한다. 다만 workspace-write가 로컬 파괴 명령을 기계적으로 막지 못하므로 Codex는 planner·read-only task·reviewer에만 쓰고, Codex로 지정된 writer는 Claude의 denylist 경계로 fallback한다.
8. Claude에도 같은 bounded contract를 주입한다. 엔진별 자동 로딩 차이는 추가 규칙의 존재가 아니라 동일 계약을 얻는 경로 차이로만 남긴다.
9. 각 agent 결과는 같은 wave의 다른 agent를 기다리지 않고 완료 즉시 `orchestration.json`과 `team-log.jsonl`에 저장한다. wave ID는 worktree 생성 전에 예약하고 모든 attempt artifact의 최댓값 다음으로 단조 증가한다. integration commit도 target fast-forward 전에 저장하며, 재기동은 commit·base·clean target HEAD를 대조해 이미 승격된 task를 복구하고 중단된 worktree는 cleanup audit에 보존한다.
10. `team-log.jsonl`은 append-only event audit, `orchestration.json`은 현재 graph projection, `run-status.json`은 현재 loop phase, `state.json`은 재기동 gate라는 네 역할을 분리한다.
11. dashboard는 task·agent·dependency·dispatch·fallback·integration·worktree·evidence를 읽기 전용으로 표시한다. 제어 endpoint는 계속 금지한다.
12. completion reviewer는 code/test만 아니라 orchestration artifact와 event record도 감사한다. green suite만으로 scheduler 계약을 PASS하지 않는다.

## 결과

- autoloop이 `orchestrate`를 사용했다는 사실이 verdict·budget·event로 관찰된다.
- 독립 task의 병렬 실행과 dependent task의 지연이 graph 상태로 재현된다.
- concurrent writer 충돌이 shared working tree 오염 대신 fan-in 경계의 명시적 `blocked`로 바뀐다.
- Codex는 대상 worktree 밖 쓰기 범위를 얻지 않으면서도 필수 오케스트레이션 계약을 받는다.
- 사용자는 dashboard에서 어떤 agent가 어느 task를 어느 worktree에서 수행 중인지 확인한다.

## 영향

`.agents/skills/autoloop/SKILL.md`, `.agents/skills/autoloop/scripts/driver.py`, `.agents/skills/autoloop/scripts/driver_test.py`, `.agents/skills/autoloop/scripts/dashboard.py`, `.agents/skills/autoloop/scripts/dashboard_test.py`, `.agents/skills/README.ko.md`, `docs/specs/2026-07-19-autoloop-driver.md`, `docs/specs/2026-08-03-autoloop-engine-harness-load-symmetry.md`, `docs/specs/2026-08-19-autoloop-dashboard.md`, `docs/specs/2026-08-19-autoloop-orchestration-runtime.md`, `docs/adr/025-autoloop-driver.md`, `docs/adr/047-autoloop-observation-dashboard.md`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/{autoloop-orchestration-review,harness-ops-log.md}`
