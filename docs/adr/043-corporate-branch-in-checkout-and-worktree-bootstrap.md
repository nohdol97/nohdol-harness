# ADR 043 — worktree 의존성 부트스트랩

> **현재 유효한 범위**: worktree별 의존성 설치와 환경 공유 방지다. 작업 위치는 [ADR 052](052-corporate-worktrees-restored.md)와 [ADR 053](053-pi-profile-exception.md)을 따른다. 개인·사내 모두 worktree를 사용할 수 있다. 철회된 사이트별 지시 본문은 2026-09-29 사용자 요청으로 제거했으며 이전 내용은 Git 이력에 남아 있다.

- 날짜: 2026-08-05 / 본문 정리: 2026-09-29
- 상태: 부분 대체(→052), 의존성 부트스트랩 활성
- 관련: ADR 035(하위 프로젝트 worktree 워크플로), ADR 052(프로필 공통 절차), ADR 053(Pi 체크아웃 선택권)

## 배경

**worktree는 의존성 디렉토리를 가져오지 않는다.** 저장소는 공유하지만 미추적 빌드 상태(`.venv`, `node_modules`)는 공유하지 않는다. 2026-08-05 실측: 등록된 6개 프로젝트가 전부 `.venv`를 갖고 있고(7~27MB), `telemetry-contract`의 것을 재생성하는 데 **8~12초**가 걸린다(2회 측정 — 실트리 8.1초, `git archive` 복사본 11.96초. 자릿수가 요점이고 초 단위가 아니다). 같은 날 `telemetry-contract` #3 작업에서 implementer가 worktree에 러너가 없는 것을 **작업 중에 발견**하고 스스로 만들었다 — 절차에 없어서 매번 각자 발견하는 상태였다.

## 결정

1. worktree 생성 직후, 프로젝트 AGENTS.md가 기록한 명령으로 의존성을 설치한다. 테스트를 돌릴 발행 프롬프트에도 그 단계를 적는다. 설치처 프로필에 관계없이 적용한다.
2. 의존성 디렉토리를 심볼릭 링크·복사로 공유하지 않는다. 이 프로젝트들은 editable 설치(`pip install -e`)라 **빌린 환경이 어느 트리를 import하는지는 호출 방식에 달렸다** — 이 워크스페이스에서 실측돼 `.agents/projects/agent-eval-onboarding/AGENTS.md`에 기록돼 있다: `.venv/bin/python -m pytest tests/`는 *worktree의* 패키지를, `.venv/bin/pytest` 콘솔 스크립트는 *체크아웃의* 것을 집는다. 실패가 균일하지 않다는 것이 금지를 조건부가 아니라 전면으로 두는 이유다 — 위험한 쪽이 사람들이 실제로 타이핑하는 짧은 형태이고, 둘은 초록 결과만 봐서는 구분되지 않는다. 틀린 트리 위의 통과는 아끼는 10초 남짓보다 비싸다.

## 근거

별도 worktree의 테스트는 그 worktree의 코드와 의존성을 사용해야 한다. 환경을 빌려 다른 체크아웃을 검사하면 테스트 통과가 작업 결과를 입증하지 못한다. 구체적인 시작·재개·정리 절차는 `branch-workflow`를 따른다.

## 영향

기존 부트스트랩 결정의 실행처(이번 변경에서 수정하지 않음):

- `.agents/skills/branch-workflow/SKILL.md` — worktree별 의존성 부트스트랩과 환경 공유 방지의 실행 절차.
- 프로젝트별 AGENTS.md — 실제 의존성 설치 명령의 정본.

이번 문서 정리의 변경 파일(이 ADR 자체 제외):

- `docs/adr/045-corporate-profile-dispatch-restored.md` — 낡은 유지 참조 제거.
- `docs/README.md` — ADR 043의 현재 범위 안내.
- `docs/specs/2026-07-19-autoloop-driver.md` — 철회된 안내를 대체 기록으로 정리.
- `docs/harness-changelog.md` — 과거 지시 요약 제거와 이번 변경 기록.
- `_workspace/harness-ops-log.md`(미추적) — 같은 지시가 남은 로컬 기록 정리.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-08-05 | worktree 의존성 부트스트랩 결정 | 의존성 설치·환경 공유 | 별도 worktree의 실행 환경을 명시 |
| 2026-09-08 | 작업 위치 결정을 ADR 052로 이관 | 사이트별 작업 위치 | 개인·사내 공통 절차 적용 |
| 2026-09-29 | 철회된 사이트별 지시와 우회 절차 본문 제거 | 이 문서 | 사용자가 사내 worktree 사용 제약 내용의 전면 제거 요청. 유효한 부트스트랩 결정과 ADR 파일은 유지 |
