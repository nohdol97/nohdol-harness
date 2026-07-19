# 스펙: 하네스 무결성 기계 점검 스크립트 (integrity-check)

- **상태**: 구현됨 (2026-07-19 — TDD 14 케이스 통과, 현 저장소 29 pass/0 fail)
- **날짜**: 2026-07-19
- **대상 코드**: `.agents/hooks/integrity-check.py` (+ 회귀 테스트 `.agents/hooks/integrity-check_test.py`)
- **관련**: docs/proposals/2026-07-19-oh-my-openagent-adoption.md (채택 ②), AGENTS.md 8절 승격 원칙, harness-review 주간 무결성 점검

## 1. 배경

harness-review 주간 점검의 "구조 무결성" 단계(심링크·frontmatter·`.claude/` 실파일·인덱스 정합)는 현재 **모델이 파일을 읽어 절차로 판정**한다. 이 방식은 ⓐ 비결정적이고(같은 결함을 회차에 따라 놓칠 수 있음) ⓑ 매주 하네스 파일 재독 토큰을 쓴다(무신호 보고 112k 토큰 실측이 일일 상한 신설의 근거였던 것과 같은 계열). 전부 기계 판정 가능한 항목이라 8절 승격 원칙("기계적 차단이 가능하면 훅으로")의 적용 대상이며, oh-my-openagent의 meta-audit 테스트(문서-현실 불일치 시 CI 실패)가 방향을 실증했다. tdd-gate·secret-gate에 이은 세 번째 "문서 규칙 → 실행 계층" 승격이다.

## 2. 목표

주간 무결성 점검의 기계 판정 항목을 파이썬 스크립트 1개의 **결정론적 PASS/FAIL 리포트**로 대체한다. harness-review 주간 서브에이전트는 이 스크립트를 Bash 1회로 실행하고, 남는 일은 의미 판정(레지스트리 정합·규칙 충돌 등)뿐이다.

## 3. 비목표

- **커밋 차단 게이트가 아니다** — 리포트 전용. 차단 승격 여부는 운용 관찰 후 별도 판정.
- 진화 신호 스캔(8절 ①~④)의 대체가 아니다 — 신호는 의미 판정이라 모델 몫.
- 하위 프로젝트(`.agents/projects/`, `project/`) 검사는 범위 밖 — 설치처별 데이터라 보편 불변식이 없다.
- 자동 수정(fix) 기능 없음 — 발견은 metaskill 제안 경로로 흐른다.

## 4. 요구사항

레포 루트(스크립트 위치 기준 상대 탐색, `CLAUDE_PROJECT_DIR` 부재 시 cwd 폴백 — `_common.py` 관례)에서 다음을 검사한다:

- **R1 심링크**: `.claude/agents` → `../.agents/agents`, `.claude/skills` → `../.agents/skills` (readlink 일치).
- **R2 `.claude/` 실파일 침입**: `.claude/` 직속에 심링크·허용 목록(`settings.json`, `settings.local.json`) 외 항목이 있으면 FAIL (§11 우회 신호). 단, **git이 무시하는 항목은 제외**한다(`git check-ignore` 판정 — `.gitignore`와 머신 로컬 `.git/info/exclude` 모두 포함): CLI 런타임 산출물(예: 현재 존재하는 `.claude/scheduled_tasks.lock`)은 하네스 우회가 아니라 도구 동작이고, 이를 FAIL로 잡으면 완료 기준 2가 구조적으로 성립 불가다. 이 제외 동작은 테스트 픽스처로 검증한다(무시된 파일 → PASS, 추적 가능한 침입 실파일 → FAIL).
- **R3 스킬 frontmatter**: `.agents/skills/*/SKILL.md` 각각 — 첫 줄 `---`, `description:` 키 존재, LF 개행(CRLF 검출 시 FAIL).
- **R4 에이전트 frontmatter**: `.agents/agents/*.md` 각각 — `name`/`description`/`tools`/`tier` 키 존재(§10).
- **R5 MOC 정합**: `docs/adr/`·`docs/specs/`·`docs/proposals/`의 `.md` 파일 ↔ `docs/README.md` 링크의 **양방향 대조** — 파일은 있는데 인덱스에 없음 / 인덱스에 있는데 파일 없음 모두 FAIL.
- **R6 CLAUDE.md 첫 줄**: `@AGENTS.md` 임포트(ADR 021) 유지 여부.
- **R7 gitignore 필수 항목**: `.gitignore`에 다음 패턴이 원문 그대로 존재 — `_workspace/`, `project/`, `REGISTRY.md`, `.agents/projects/*`, `!.agents/projects/README.md` (ADR 005·006, 2026-07-19 현행 .gitignore 실측 표기).
- **R8 출력·종료 코드**: 항목별 `PASS`/`FAIL <사유·경로>` 한 줄씩 + 말미 요약 1줄. 문제 0건이면 exit 0, 1건 이상이면 exit 1. 출력 라벨은 영어(소비자는 harness-review 서브에이전트 — §15), 사용자 보고는 그 에이전트가 한국어로 소화.
- **R9 오류 처리**: 검사 대상 부재·읽기 실패는 해당 항목 FAIL로 보고(조용한 통과 금지 — 점검 도구는 게이트와 달리 fail-loud가 맞다). 스크립트 자체 예외로 전체가 죽지 않게 항목 단위 격리.
- **R10 의존성**: 표준 라이브러리만(§16 사다리 3) — 서드파티 설치 불요.
- **R11 설치처 범위**: 지원 대상은 macOS·Linux 심링크 설치처다(ADR 019와 같은 범위). §11이 허용하는 **심링크 불가 설치처(sync 스크립트 대체)에서는 R1·R2를 SKIP으로 판정하고 사유를 출력**한다(FAIL 아님) — 판별은 `.claude/agents`가 심링크가 아니면서 해당 설치가 ADR 기록상 sync 방식인 경우인데, 스크립트는 ADR을 읽지 않으므로 단순화한다: `.claude/agents`가 심링크가 아니면 R1·R2를 `SKIP (non-symlink installation — verify sync script per §11)`으로 출력하고 종료 코드에 반영하지 않는다. Windows 등 그 외 플랫폼 지원은 범위 밖(doc-writer 크로스 플랫폼 체크리스트는 이 사유로 스코프 아웃).

## 5. 완료 기준

1. `integrity-check_test.py` 회귀 테스트 통과 — 임시 디렉토리 픽스처로 R1~R7 각각의 정상/결함 케이스(심링크 파괴, 실파일 침입, CRLF, 키 누락, 인덱스 고아·유령 행, 첫 줄 훼손, gitignore 항목 삭제)를 재현해 PASS/FAIL·exit code를 검증한다(§13 테스트 먼저 — 구현 전 실패 테스트 작성).
2. 현 저장소에서 실행 시 전 항목 PASS (결함이 드러나면 먼저 고치고 통과).
3. harness-review SKILL.md의 주간 2단계(구조 무결성 점검)가 "스크립트 실행 + 결과 소화"로 갱신된다 — 문서와 절차가 같은 커밋에서 움직인다(§6).
4. docs/README.md 스펙 표에 본 스펙 행이 등재되고, 구현 커밋에서 상태가 `구현됨`으로 갱신된다.
