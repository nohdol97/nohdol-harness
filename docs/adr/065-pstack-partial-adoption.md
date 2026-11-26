# ADR 065 — pstack 부분 채택: 착안 3건 이식, 통설치 기각

- **날짜**: 2026-11-26
- **상태**: 활성
- **관련**: ADR 022(superpowers 부분 채택)·ADR 044(mattpocock 부분 채택), 같은 판정 구조의 선례. ADR 063(autoloop 폐기 — 반복 개선 루프 기각과 같은 축), 루트 AGENTS.md §3·§7·§9·§13, proposal `docs/proposals/2026-11-26-pstack-review.md`

## 변경 내용

1. **통설치를 기각한다.** 원본(`cursor/plugins` 마켓플레이스)·미러·이식판 어느 경로도 채택하지 않는다. 사유는 proposal §2 — `/poteto-mode`가 orchestrate·team-review 절차를 대체하고, `/setup-pstack`이 모델명을 고정한 상시 로드 규칙 파일을 쓴다. 선례와 달리 자동 호출은 최상위 스킬 59개 중 58개가 꺼져 있어 트리거 충돌 사유는 약하다는 점을 기록해 둔다.
2. **`team-review` Tests 관점에 변이 검사를 넣는다.** 완료 기준이 기대는 가드를 바꾼 diff에만 적용하며 Solo 모드에도 적용한다. agent-rules ⑨에 새로 적은 방법으로 만든 작업 트리 임시 사본(커밋 안 된 변경 포함)에서 가드를 무력화해 테스트가 빨개지는지, 변이가 의도한 줄을 맞혔는지, 기준의 절마다 어느 변이가 답하는지 확인한다. 새 관점·새 reviewer 호출은 만들지 않는다. ⑨ 사본 안의 변이는 reviewer 쓰기 범위의 유일한 예외로 적고, orchestrate 병렬 쓰기 격리 규칙에는 "⑨ 사본으로 한정한 변이는 `isolation: worktree`가 필요 없다"를 더한다.
3. **`reviewer` §2에 소비 경로 기준의 위험 해소 규칙을 넣는다.** 바뀐 것의 소비 지점 열거, 안전 근거 사실 하나와 그 증거 단계 명시. 별도 항목으로, diff 안팎의 상태 변경 분기 중 가드 없는 것이 있으면 그럴듯함으로 심각도를 낮추지 않음. `team-review` Solo 5항의 범위에 "바뀐 것을 쓰는 곳의 표적 검색"을 더한다.
4. **`implementer` §5와 `troubleshooter` §2에 공유 전제 검증을 넣는다.** 한 번 고친 뒤 같은 실패·같은 부류 지적이 다시 나오면, 다음 시도 전에 그 전제를 적어 직접 검증한다. 재시도 라운드는 늘리지 않는다. troubleshooter는 같은 결함 패턴의 다른 지점도 찾는다.

## 대상

`.agents/skills/team-review/SKILL.md`, `.agents/skills/orchestrate/SKILL.md`(병렬 쓰기 격리), `.agents/skills/metaskill/references/agent-rules.md`(⑨ 사본 방법), `.agents/agents/reviewer.md`, `.agents/agents/implementer.md`, `.agents/agents/troubleshooter.md`, `.agents/agents/README.ko.md`, `.agents/skills/README.ko.md`, `docs/proposals/2026-11-26-pstack-review.md`, `docs/README.md`, `docs/harness-changelog.md`, `_workspace/harness-ops-log.md`(비추적)

## 사유

**사용자 요청**(2026-11-26): "적용 가능한게 있는지 검토해" → 후보 9건 가운데 사용자가 "권장하는 것만 다 적용해"로 3건을 골랐다.

**왜 이 셋인가.** 후보 중 이 셋만 메모리에 **실측 실패**가 기록된 표면을 다룬다(공통규칙 15 ②). 각 조항의 발동 조건을 그 사례에 대어 보았고, 셋 다 발동했다(proposal §3). 나머지 후보는 그럴듯하지만 실측 실패가 없어, 넣으면 상상한 위반 지점만 막고 비용이 남는다.

**왜 AGENTS.md가 아닌가.** 셋 다 특정 역할이 특정 시점에 하는 일이라 그 역할의 정의 파일이 맞는 자리다. 상시 로드 파일(R14 예산)에 둘 이유가 없다.

**충돌 처리(공통규칙 8).**
- 변이는 실제 쓰기라 reviewer의 "저장소 상태 불변"(agent-rules ⑨) 원칙과 부딪힌다. 그래서 ⑨에 사본 방법을 넣고, 그 사본 안의 쓰기만 예외로 했다. 기존 orchestrate 격리 규칙(변이하는 리뷰어는 `isolation: worktree`)은 HEAD에서 시작해 미커밋 diff를 못 보므로, ⑨ 사본으로 한정한 변이는 그 규칙에서 빠지도록 맞췄다. PKI 하위 하네스 5항(변이 검사는 보안·데이터 보호 가드만)은 더 구체적인 규칙이라 PKI에서는 그쪽이 이긴다(루트 §2). 조항에 "프로젝트 하네스가 대상을 좁힐 수 있다"를 적었다.
- 소비 경로 열거는 Solo 모드의 "diff와 가리키는 문서만" 범위와 부딪힌다. 그래서 그 범위를 표적 검색만큼 넓히고, 자유 탐색 금지와 작업 한도는 유지했다.
- 전제 검증은 재시도 한도와 부딪히지 않도록 "라운드를 늘리지 않고 다음 시도가 출발하는 지점을 바꾼다"로 적었다.

## 검증 라운드에서 확정한 설계 결정

독립 검증이 같은 변경에 **두 번 BLOCK**을 냈다. 1라운드는 필수 수정 1·권장 수정 5·낮음 3이었고, 델타 라운드는 필수 수정 1·낮음 3이었다. metaskill 개선 모드는 이것을 지연이 아니라 신호로 본다. 그래서 남은 쟁점을 여기서 먼저 확정하고 적용했다.

1. **변이는 HEAD worktree가 아니라 작업 트리 사본에서 한다.** 리뷰 대상은 대개 커밋 전 diff다. HEAD에서 만든 worktree(orchestrate의 `isolation: worktree` 포함)는 그 diff를 못 본다. 사본 방법은 agent-rules ⑨ 한 곳에만 적고 나머지는 가리킨다.
2. **사본에서는 변이 전에 기준 실행을 먼저 한다.** 사본에는 `.git`과 무시 대상 파일이 없다. 그래서 변이 없는 테스트가 원본과 같은 결과(통과·실패·건너뜀 수)를 내는지 먼저 맞춰 본다. 다르면 빠진 파일을 복사하거나 그 가드를 미검증으로 적는다. 이 단계가 없으면 거짓 차단과 거짓 통과가 둘 다 생긴다. 실측: 원본 트리 `integrity-check` 52 통과·0 건너뜀, 사본 51 통과·1 건너뜀(R20).

