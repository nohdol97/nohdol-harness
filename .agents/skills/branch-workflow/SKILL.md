---
name: branch-workflow
description: Start and finish subproject work on clean feature branches to prevent stale-branch merge conflicts. On start - fetch, fast-forward main, create a feat/fix branch; on finish - rebase onto latest main, push, and open a PR via gh (merge stays with the user). Applies to subproject repos only, not the root harness repo. Use when starting any subproject task or when the user says 작업 시작, 브랜치 만들어, PR 생성, 머지 준비. Re-run keywords - branch, PR, rebase, 브랜치, 작업 시작.
---

# branch-workflow — 하위 프로젝트 브랜치·PR 워크플로우

## 왜 이 스킬인가

관찰된 반복 문제(진화 트리거 '반복 실패'): 이전 작업의 오래된 브랜치 위에서 새 작업을 시작 → main과 점점 벌어짐 → 머지 시점에 충돌. 원인은 충돌 자체가 아니라 **시작 시점이 최신 main이 아니었던 것**이다. 그래서 이 스킬은 시작(항상 최신 main에서 분기)과 마무리(PR 직전 rebase)의 양 끝을 고정한다. 2026-07-12 사용자 인터뷰로 방식 확정.

**적용 범위**: 하위 프로젝트 독립 저장소만. **루트 하네스 저장소는 예외** — 문서 중심이라 main 직커밋을 유지한다(루트 AGENTS.md 5절).

## 시작 절차 (모든 하위 프로젝트 작업의 첫 단계)

1. **현재 상태 확인**: `git status` — 미커밋 변경이 있으면 진행하지 않고 처리 방법(커밋/stash/폐기)을 사용자에게 묻는다. 이유: 남의 작업일 수 있는 변경을 자동 처리하면 유실 사고가 된다.
2. **main 최신화**: `git fetch origin` → `git checkout main` → `git pull --ff-only`. fast-forward 불가면(로컬 main 오염) 중단하고 상태를 보고한다 — 오염된 main에서 분기하면 문제가 브랜치로 전파된다.
3. **새 브랜치 생성**: `git checkout -b <type>/<간결한-설명>` — type은 커밋 컨벤션과 동일(feat|fix|refactor|chore 등), 설명은 kebab-case (예: `feat/login-oauth`, `fix/schedule-overlap`).
4. 작업 진행 (커밋은 Conventional Commits + 프로젝트 스코프). **기능 추가·동작 변경이면 구현 전에 스펙 → 실패 테스트 순서를 지킨다**(루트 AGENTS.md 13절 SDD+TDD, 스펙은 doc-writer 템플릿).

## 마무리 절차 (작업 완료 시)

1. **검증**: 테스트·빌드 통과 확인 (실패 상태로 PR을 만들지 않는다).
2. **PR 직전 rebase**: `git fetch origin` → `git rebase origin/main`. 충돌 시 해소 **전에** 충돌 파일·내용을 사용자에게 보고하고 해소 방향을 확인한다.
3. **푸시**: `git push -u origin <브랜치>`. rebase로 이력이 바뀐 기푸시 브랜치는 `--force-with-lease`를 쓰되 **자신의 feature 브랜치 한정 + 사용자 확인**(3절 가드레일 — force 계열은 예외 없이 확인). main에는 어떤 경우에도 force 금지.
4. **PR 생성**: `gh pr create` — 제목은 커밋 컨벤션 형식, 본문은 변경 요약 + 검증 결과. PR URL을 보고한다.
5. **머지는 사용자가 한다.** 머지 후 feature 브랜치 삭제를 권장한다 — 다음 작업의 시작 절차(1~3)가 "브랜치는 일회용"을 전제로 하기 때문이다.

## 엣지 케이스

- **작업이 길어져 main이 크게 앞서감**: 마무리까지 기다리지 말고 중간에 `git rebase origin/main`을 수행해도 된다 — 충돌은 작을 때 해소하는 것이 싸다.
- **gh CLI 부재 / 원격이 GitHub이 아님**: PR 생성 단계를 건너뛰고 푸시된 브랜치명과 수동 PR 생성 안내를 보고한다.
- **원격 없음(로컬 전용 저장소)**: 시작 절차의 fetch/pull을 생략하고 로컬 main 기준으로 분기, 마무리는 로컬 머지를 사용자에게 확인받는다.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 시작점 | 오래된 브랜치 위에서 시작 → 충돌 예약 | 항상 최신 main에서 분기 |
| 충돌 시점 | 머지 순간에 한꺼번에 발견 | PR 직전 rebase로 사전 해소 + 보고 |
| 리뷰 기록 | 로컬 머지 시 기록 없음 | PR 단위로 변경·검증 결과가 남음 |
| 최종 게이트 | 자동 머지로 사람 개입 없음 | 머지 버튼은 사용자 — 사람이 장악 |
