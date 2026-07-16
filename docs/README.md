# docs/ — 결정·스펙·제안 지도 (MOC)

이 파일은 `docs/` 하위 문서의 **탐색 인덱스**다(obsidian Map-of-Content 착안). ADR·스펙이 늘면서 "어느 결정이 어느 결정을 대체했는지", "어느 스펙이 어느 코드·ADR에 걸리는지"를 파일을 다 열지 않고 한눈에 보기 위한 것이다. 규칙의 단일 원본은 여전히 [AGENTS.md](../AGENTS.md)이고, 이 인덱스는 **길잡이일 뿐 내용을 복제하지 않는다**(링크만).

> **동기화 의무**: ADR·스펙·제안을 새로 만들거나 상태가 바뀌면(대체·구현·기각) 이 인덱스의 해당 행을 **같은 커밋에서 갱신**한다(metaskill 절차·AGENTS.md 6절). 인덱스가 현실과 어긋나면 REGISTRY.md와 같은 이유로 아무도 안 믿게 된다.

## ADR (구조적 결정 기록) — `docs/adr/`

상태: **활성** = 유효, **부분 대체(→NNN)** = 일부 결정이 후속 ADR로 대체됨(각 ADR 상단 배너에 어느 부분인지 명시). ADR은 불변 기록이라 대체돼도 삭제하지 않는다 — 결정의 역사를 남긴다.

| ADR | 날짜 | 상태 | 제목 |
|---|---|---|---|
| [001](adr/001-initial-harness.md) | 2026-07-12 | 부분 대체(→005·021) | 루트 하네스 초기 구성 |
| [002](adr/002-project-dir-separation.md) | 2026-07-12 | 활성 | 하위 프로젝트 저장소 분리 (`project/`·`dev/` 미추적) |
| [003](adr/003-perfectionism-clause-removal.md) | 2026-07-12 | 활성 | "완벽주의 금지" 절 삭제 및 1차 독립 검증 반영 |
| [004](adr/004-registry-separation-standard-roster.md) | 2026-07-12 | 부분 대체(→005) | 레지스트리 분리(REGISTRY.md)와 표준 팀원 로스터 완성 |
| [005](adr/005-registry-untracked-portable-harness.md) | 2026-07-12 | 활성 | 하네스 이식성: REGISTRY.md 미추적, 경로 규약 이관, 티어 탈모델명 |
| [006](adr/006-subproject-harness-central-management.md) | 2026-07-13 | 활성 | 하위 프로젝트 하네스 중앙 관리 (원본 루트 일원화·미추적) |
| [007](adr/007-lazy-project-skills.md) | 2026-07-13 | 활성 | 하위 스킬·에이전트 지연 생성 + 프로젝트 로컬 배치 |
| [008](adr/008-tdd-gate-hook.md) | 2026-07-13 | 부분 대체(→014·015) | TDD 게이트 훅 (13절 실행 계층 강제) |
| [009](adr/009-work-tracker-session-persistence.md) | 2026-07-13 | 활성 | 세션 영속 작업 추적 (work-tracker, ccpm 패턴) |
| [010](adr/010-orchestrate-universal-gate.md) | 2026-07-13 | 활성 | orchestrate 범용 게이트화 (팀 판정 + 검증 필수 + 하이브리드) |
| [011](adr/011-roster-expansion-7-agents.md) | 2026-07-13 | 활성 | 표준 로스터 확장 (4종 → 7종) |
| [012](adr/012-installation-profile-push-policy.md) | 2026-07-14 | 활성 | 설치처 프로필(개인/사내)과 하네스 업데이트 대기 큐 |
| [013](adr/013-evolution-signal-expansion.md) | 2026-07-14 | 활성 | 진화 트리거 4신호 체계 (수축·효율 신호 신설) |
| [014](adr/014-tdd-gate-git-hook-layer.md) | 2026-07-14 | 부분 대체(→015) | TDD 게이트의 git 훅 계층 추가 (도구 무관 강제) |
| [015](adr/015-tdd-gate-single-git-layer.md) | 2026-07-14 | 활성 | TDD 게이트 git 계층 단일화 (008·014 일부 대체) |
| [016](adr/016-internal-communication-language.md) | 2026-07-15 | 활성 | 내부 통신 언어 정책 (모델만 읽으면 영어, 사용자면 한국어) |
| [017](adr/017-code-minimalism-product-code.md) | 2026-07-16 | 활성 | 코드 최소주의 — 제품 코드 (ponytail 이식) |
| [018](adr/018-claude-mem-adoption.md) | 2026-07-16 | 활성 | claude-mem 최소 채택 (세션 경계 리마인더·점진적 공개·private 마커) |
| [019](adr/019-codex-sessionstart-hook-parity.md) | 2026-07-16 | 활성 | Codex SessionStart 훅 병행 (리마인더 2종) |
| [020](adr/020-infra-domain-review-specialization.md) | 2026-07-16 | 활성 | 인프라 도메인 리뷰 특화 (team-review 인프라 관점을 infra-specialist가 리뷰 모드로) |
| [021](adr/021-claude-md-agents-import.md) | 2026-07-16 | 활성 | CLAUDE.md `@AGENTS.md` 임포트 (단일 원본 항상-온) + 변경 이력 분리 |
| [022](adr/022-superpowers-adoption.md) | 2026-07-17 | 활성 | superpowers 규율 착안 3건 이식 (압박 테스트·신선한 증거·리뷰 수신 규율) |

**대체 체인**: tdd-gate는 008(Claude Code 한정 PreToolUse) → 014(git 계층 추가, 도구 무관) → 015(git 계층 단일화, PreToolUse 제거)로 진화했다. 008·014의 나머지 결정(차단 지점·fail-open·예외·commit-msg 선택·전역 hooksPath 등)은 유효하다. 그 밖의 부분 대체: 티어 모델명·REGISTRY.md 추적은 001·004 → 005(탈모델명·미추적), CLAUDE.md 산문 포인터·변경 이력 위치는 001 → 021(`@AGENTS.md` 임포트·changelog 분리).

## 스펙 (SDD — 루트 자체 코드) — `docs/specs/`

루트 하네스가 추적하는 코드(훅 등)의 스펙. 하위 프로젝트 스펙은 각 프로젝트 저장소 `docs/specs/`에 있다(13절 — 여기 없음).

| 스펙 | 상태 | 대상 코드 | 관련 ADR |
|---|---|---|---|
| [2026-07-13-tdd-gate-hook](specs/2026-07-13-tdd-gate-hook.md) | 구현됨 | `.agents/githooks/tdd-gate.py` | 008·014·015 |
| [2026-07-14-agentsview-daemon-hook](specs/2026-07-14-agentsview-daemon-hook.md) | 구현됨 | `.agents/hooks/agentsview-daemon.py` | — |
| [2026-07-14-harness-review-reminder-hook](specs/2026-07-14-harness-review-reminder-hook.md) | 구현됨 | `.agents/hooks/harness-review-reminder.py` | 013·019 |
| [2026-07-15-hooks-common-bootstrap](specs/2026-07-15-hooks-common-bootstrap.md) | 구현됨 | `.agents/hooks/_common.py` | — |
| [2026-07-16-worklog-reminder-hook](specs/2026-07-16-worklog-reminder-hook.md) | 구현됨 | `.agents/hooks/worklog-reminder.py` | 018·019 |

## 제안 (외부 도구 분석·채택 설계) — `docs/proposals/`

외부 도구·패턴을 분석하고 무엇을 이식하고 무엇을 기각할지 설계한 문서. 채택되면 결과가 ADR로 확정된다(제안 = 과정, ADR = 결정).

| 제안 | 결과 | 요지 |
|---|---|---|
| [2026-07-15-ponytail-adoption](proposals/2026-07-15-ponytail-adoption.md) | → ADR 017 | ponytail 코드 최소주의 결정 사다리 이식(원칙+리뷰 관점만, 배송 기계 기각) |
| [2026-07-16-claude-mem-adoption](proposals/2026-07-16-claude-mem-adoption.md) | → ADR 018 | claude-mem 착안 3개 무의존 이식(워커·벡터 DB·전수 캡처 기각) |
| [2026-07-17-superpowers-adoption](proposals/2026-07-17-superpowers-adoption.md) | → ADR 022 | superpowers 규율 착안 3개 문서 이식(플러그인 통설치·나머지 11스킬 기각) |
