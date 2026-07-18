@AGENTS.md

# CLAUDE.md

> 위 `@AGENTS.md`(첫 줄)가 단일 원본 전문을 세션 시작 시 **자동 주입**한다(ADR 021). 이 파일은 Claude Code 전용 로더이자, 매 턴 최우선으로 지켜야 할 **항상-온 앵커**만 둔다 — 전문 규칙·이유·상세는 AGENTS.md 단일 원본, 변경 이력은 `docs/harness-changelog.md`.

## 항상-온 앵커 (Claude 전용 — 상세는 AGENTS.md)

- **출력 언어 (§15)**: 사용자 대면 출력(채팅·요약·보고·질문·PR 본문·문서)은 **한국어로 고정**한다. 영어는 §15의 모델 전용 내부 통신(발행 프롬프트·팀 중간 리포트·P2P)에만 — 사용자가 읽는 곳에 영어를 흘리지 않는다. 서브에이전트 영어 리포트를 전할 때는 인용·직역이 아니라 **한국어로 소화해 보고**하고, 최종 보고 직전에 사용자 대면 텍스트가 전부 한국어인지 확인한다(§15 가드 1).
- **라우팅 — 스킬 맵 (§7)**: 구현·수정·리팩토링 등 다단계 작업 + 다중 프로젝트·팀·병렬 → `orchestrate`(Phase 0-1 게이트 — '직접 수행' 판정이면 즉시 반환하므로 가벼운 요청도 부담 없음). 하네스 생성·개선·프로젝트 신설 → `metaskill`. 리뷰·검토·검증("리뷰해줘"·"코드 리뷰"·"PR 검토") → `team-review`(내장 review 아님). 문서·스펙·리포트·런북 → `doc-writer`. 새 설치처·REGISTRY.md 부재 → `harness-install`. 세션 넘김 작업 등록·재개("작업 등록"·"이어서 하자"·"하던 작업 뭐였지") → `work-tracker`. 배포·릴리스 → `release`. PR 생성 → `branch-workflow`+doc-writer PR 템플릿. 전체 프로젝트 현황("프로젝트 상태"·"전체 현황"·"상태 요약") → `project-status`. URL 본문 읽기·요약("링크 읽어줘"·기사·문서 URL) → `defuddle`(.md URL·인증 페이지는 WebFetch). 설치된 외부 도구·플러그인 사용 실측 감사("플러그인 쓸모 있나"·"사용 실측"·"도구 정리") → `tool-audit`(주기 점검은 harness-review, 제거 실행은 metaskill). **continuation('진행해줘'·'계속')도 새 구현·동작 변경·k8s 매니페스트 변경이면 orchestrate 게이트를 다시 밟는다** — k8s 매니페스트 변경은 continuation이라도 `infra-specialist` 경유·네임스페이스 리소스 상한 선확인(상세: AGENTS.md §7). **수집·요약형 서브에이전트 발행은 general-purpose가 아니라 `explorer` 타입으로**(원인 조사→troubleshooter·검증→reviewer — §7 6항).
- **스킬 우선순위 (§7)**: ① 요청이 특화 스킬 트리거에 맞으면 **특화 스킬이 orchestrate 게이트보다 우선**(리뷰→team-review, 문서→doc-writer, 하네스→metaskill). ② 같은 트리거의 **내장·플러그인·SuperClaude·gstack 스킬보다 하네스 스킬이 우선** — "implement/fix/build"→`orchestrate`, "debug/investigate/QA·test-and-fix"→orchestrate 게이트 후 troubleshooter(수정은 implementer 루프), "design"→orchestrate 후 architect, "review/code review/security audit"→`team-review`, "deploy/land/ship to production"→`release`, "create a PR/ship/push to main"→`branch-workflow`, "resume/이어서/checkpoint/where was I"→`work-tracker`. **머지는 항상 사용자 몫** — 자동 머지하는 외부 스킬(land-and-deploy 등)에 위임 금지. 외부 스킬은 하네스 절차 안의 보조 도구로만 쓴다(외부 스킬로 새는 라우팅은 하네스의 판정·템플릿·가드레일을 통째로 우회한다).

## 하네스: 루트

- **목표**: 여러 하위 프로젝트(웹·앱·백엔드·k8s·AWS)를 담는 모노 워크스페이스의 공통 규칙·라우팅·오케스트레이션을 관리한다. 작업 전 대상 프로젝트의 AGENTS.md도 읽는다(라우팅 §7).
