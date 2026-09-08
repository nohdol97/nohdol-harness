# ADR 052 — 사내 프로필 worktree 복원

- 날짜: 2026-09-08
- 상태: 활성
- 관련: ADR 035, ADR 043(사내 예외만 대체), [스펙](../specs/2026-09-08-corporate-worktrees.md)

## 배경
사용자가 사내 환경에서도 Git worktree를 허용하도록 요청했다. 기존 ADR 043은 사내에서 커밋·푸시·PR이 실패한다는 당시 사용자 보고를 근거로 예외를 두었다. 이번 결정은 그 예외를 철회하는 명시적 요청에 따른다. 당시 실패의 원인이 해결됐다는 주장은 하지 않는다. 이 기계에서는 사내 서버를 조회하지 않았다.

## 결정
개인·사내 모두 기존 `branch-workflow`의 전용 worktree 절차를 적용한다. 사내 전용 체크아웃 분기를 삭제하고, 시작·의존성 부트스트랩·PR·머지 실측·비강제 정리 절차를 공통으로 사용한다. 과거 Branch 전용 이월 노트는 브랜치와 미저장 작업을 확인하고 기존 브랜치 worktree 절차로 이어간다.

autoloop은 사내에서도 연결된 worktree를 대상으로 실행할 수 있다. 공유 체크아웃 거부(R18)는 그대로 유지하고, 모든 설치처에 worktree 생성 안내를 돌려준다. 안내만을 위해 존재했던 프로필 판독 함수는 삭제한다.

사내 프로필의 추적 루트 파일 편집 제한과 다른 프로필 정책은 이번 변경의 대상이 아니다. 원격·인증·권한 설정도 변경하지 않는다.

## 판단 근거와 검증
새 워크플로를 만들지 않고 ADR 043의 예외를 제거해 ADR 035의 공통 절차를 복원한다. 기존 규칙의 시작·재개·정리·발행 위치와 autoloop R18을 읽어 충돌 지점을 확인했다. 삭제되는 예외 외에 새 행동 규율·임계치·차단 조건은 도입하지 않는다.

회귀 기준은 사용자 요청과 기존 R18 격리 계약이다. 사내 공유 체크아웃에서 생성 안내를 기대하는 테스트를 먼저 실행해 기존 ADR 043 금지 메시지로 실패함을 확인했다. 변경 후 `python3 .agents/skills/autoloop/scripts/driver_test.py`는 통과했다. 사내·개인·프로필 파일 부재에서 공유 체크아웃 거부와 연결된 worktree 허용을 검사한다. 이는 로컬 판정 검증이며 사내 서버의 커밋·푸시·PR 성공을 입증하지 않는다.

지식 소스 진입점을 키워드로 조회했으나 관련 항목이 없어 외부 주장을 채택하지 않았다. 과거 ADR과 이력의 금지 설명은 당시 기록으로 보존하고, 현재 권위로 읽힐 문서에는 대체 표시를 달았다.

## 영향
- `.agents/skills/README.ko.md`
- `.agents/skills/autoloop/SKILL.md`
- `.agents/skills/autoloop/scripts/driver.py`
- `.agents/skills/autoloop/scripts/driver_test.py`
- `.agents/skills/branch-workflow/SKILL.md`
- `.agents/skills/carryover/SKILL.md`
- `.agents/skills/orchestrate/SKILL.md`
- `.agents/skills/orchestrate/references/product-design.md`
- `.agents/skills/wrapup/SKILL.md`
- `AGENTS.ko.md`
- `AGENTS.md`
- `docs/README.md`
- `docs/adr/035-subproject-worktree-workflow.md`
- `docs/adr/043-corporate-branch-in-checkout-and-worktree-bootstrap.md`
- `docs/adr/045-corporate-profile-dispatch-restored.md`
- `docs/specs/2026-07-19-autoloop-driver.md`
- `docs/specs/2026-09-08-corporate-worktrees.md`
- `docs/harness-changelog.md`

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-09-08 | 사내 worktree 예외 철회 | 위 영향 목록 | 사용자 명시 요청. 로컬 회귀로 공통 안내와 격리 유지 확인, 사내 서버 동작은 미검증 |
