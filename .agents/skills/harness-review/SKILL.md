---
name: harness-review
description: Harness operations review in two modes - daily lite (scan only the three evolution triggers since the last check) and weekly full (adds symlink/registry/frontmatter integrity), proposing concrete metaskill actions. Auto-triggered by the SessionStart reminder hook via markers. Use when the reminder fires or the user says 일일 점검, 주간 점검, 하네스 리뷰, harness review. Re-run keywords - harness-review, daily, weekly, evolve, 일일 점검, 주간 점검, 진화.
---

# harness-review — 주간 하네스 운영 점검

## 왜 이 스킬인가

루트 AGENTS.md 8절은 진화 트리거 3신호를 "주 1회 관찰"하는 것을 운영 습관으로 요구한다. 관찰 절차가 스킬로 고정되어 있지 않으면 이 습관은 몇 주 안에 증발한다 — 하네스는 쓰이면서 어긋난 부분이 드러날 때만 진화할 수 있다. 이 스킬은 **관찰과 제안**만 담당한다. 실제 생성·개선의 실행은 metaskill의 몫이다 (역할 분리: 관찰자가 곧바로 실행까지 하면 제안의 근거 검증이 생략된다).

## 실행 모드 (리마인더 훅이 지정 — 2단 주기)

| 모드 | 주기 | 범위 | 완료 마커 |
|---|---|---|---|
| **일일 경량** | 1일 | 1단계 신호 수집만 — 마지막 점검 이후 세션 대상. 무결성 점검 생략(주간의 몫) | `.harness-review-daily-last` |
| **주간 전체** | 7일 | 1~3단계 전부 | `.harness-review-last` + daily 둘 다 |

일일 모드는 **신호가 없으면 "신호 없음" 한 줄 보고 후 마커 갱신으로 끝낸다** — 매일의 비용은 스캔 몇 분이어야 유지된다. 신호가 있으면 주간과 동일하게 3단계(제안 생성)로 넘어간다.

## 절차

### 1. 신호 수집 (진화 트리거 3신호)

| 신호 | 관찰 방법 |
|---|---|
| 반복 요청 3회+ | 최근 세션 기억·`_workspace/` 작업명들·git 커밋 메시지에서 같은 유형 작업의 반복 확인 |
| 반복 실패 2회+ | team-log.jsonl의 `task_failed` 이벤트(orchestrate 이벤트 계약), 같은 종류의 재작업 커밋(fix 연쇄) 확인 |
| 하네스 우회 | **팀 필요성 판정(orchestrate Phase 0-1) 없이 처리된 구현·다단계 작업**(판정 한 줄 보고의 부재가 증거 — 루트 AGENTS.md 7절 3항), orchestrate 없이 처리된 다중 프로젝트 작업, `.agents/` 밖에 생긴 에이전트·스킬 정의, 레지스트리에 없는 프로젝트 디렉토리, **하네스 스킬 트리거가 내장·플러그인·sc:* 외부 스킬로 샌 라우팅**(CLAUDE.md 스킬 우선순위 위반 — 예: PR 생성이 gstack ship으로, 작업 재개가 checkpoint로) |

**agentsview 연동 (설치된 경우 신호 수집의 1차 데이터 소스)**: `agentsview`가 설치되어 있으면 세션 기억 대신 실측한다 — `agentsview session search "<요청 유형 키워드>"`로 반복 요청을, `agentsview stats`·`agentsview session list`로 재작업·실패 패턴을 조회한다. Claude Code·Codex 세션 전체가 인덱싱 대상이라 기억·커밋 메시지보다 정확하고 CLI 간 사각지대가 없다. 미설치면 위 표의 관찰 방법을 그대로 쓴다(설치는 harness-install 3단계).

### 2. 구조 무결성 점검

- 심링크: `readlink .claude/agents .claude/skills`가 `../.agents/*`를 가리키는지. **`.claude/` 아래에 심링크가 아닌 실파일이 생겼는지** (생겼다면 우회 신호 — 원본은 `.agents/`에만 있어야 한다).
- 하위 하네스: `.agents/projects/` 하위 디렉토리 목록과 REGISTRY.md 레지스트리 행("하네스 유무" ✓)이 일치하는지. `project/<이름>/` 안에 하네스 파일(AGENTS.md·CLAUDE.md·`.claude/`·`.agents/`)이 생겼는지 (생겼다면 우회 신호 — 원본은 루트 `.agents/projects/`에만 있어야 한다. 루트 AGENTS.md 12절, ADR 006·007). 하위에 CLAUDE.md가 있으면 구 규격 잔재 — 삭제 제안. 지연 생성된 `skills/`·`agents/`가 있는데 하위 AGENTS.md에 목록·경로 명시가 없으면 로드 불능 상태 — 보고.
- 스킬 로드 가능성: 각 SKILL.md의 frontmatter가 첫 줄 `---` + `description` 보유인지(무설명 스킬은 자동 트리거 불능 — 2026-07-13 장애), 개행이 LF인지(`file` 명령에 CRLF 표기 없어야 함).
- 레지스트리: REGISTRY.md가 존재하는지(없으면 설치 미완료 — harness-install 안내), 존재하면 `project/` 하위 실제 디렉토리 목록과 표가 일치하는지.
- 잔여물: `_workspace/`에서 team-log.jsonl이 **있는데** `team_delete` 이벤트가 없는 작업 디렉토리는 비정상 종료 신호. team-log 자체가 없는 팀 작업 디렉토리는 이벤트 계약 우회 신호(정보성).
- 대기 큐: `_workspace/harness-updates.md`에 상태 `대기` 항목이 있는지(루트 AGENTS.md 5절 설치처 프로필). **개인 설치처**면 이월된 개선이 잠자고 있는 것 — metaskill 적용을 제안한다. **사내 설치처**면 정상(개인 머신 이월 대기 중) — 항목 수만 보고한다.
- 변경 이력: 최근 하네스 커밋마다 변경 이력 테이블 갱신이 동반되었는지 (`git log -p -- AGENTS.md`).
- 시크릿 유출(agentsview 설치 시): `agentsview secrets scan`으로 세션 로그에 시크릿이 샜는지 스캔한다 — 3절 가드레일("기록 금지")은 예방 규칙이고 이것이 사후 검증이다. 발견 시 must-fix로 즉시 사용자 보고.

### 3. 제안 생성

- 신호가 감지되면: 어떤 신호가, 어떤 근거로, 어떤 에이전트/스킬 신설·개선으로 이어지는지를 **metaskill 호출 제안** 형태로 정리해 사용자에게 보고한다. 승인 없이 생성하지 않는다.
- **설치처 프로필 분기 (제안 확정 전 REGISTRY.md 프로필 확인 — 루트 AGENTS.md 5절)**: **사내** 설치처면 저장소 수정을 제안하지 않는다 — 사용자 승인 시 제안 내용을 `_workspace/harness-updates.md`에 `대기` 항목으로 기록한다(5절 형식: 대상 파일·변경 내용·사유를 개인 머신에서 맥락 없이 적용 가능한 수준으로). **개인** 설치처면 기존대로 metaskill 실행을 제안한다.
- 신호가 없으면: "신호 없음 — 현재 구조 유지"라고 보고하고 끝낸다. **무신호에 개선을 지어내지 않는다** — 진화 제안은 8절 신호에 근거할 때만 정당하다.

### 4. 완료 마커·운영 로그 갱신 (누락 금지)

- **마커**: 오늘 날짜(`YYYY-MM-DD`) 한 줄을 기록한다 — **일일 모드**는 `_workspace/.harness-review-daily-last`, **주간 전체 모드**는 `.harness-review-last`와 `.harness-review-daily-last` 둘 다. SessionStart 리마인더 훅(`harness-review-reminder.py`)이 이 마커들로 1일/7일 경과를 판정해 다음 점검을 자동 트리거한다 — 마커를 갱신하지 않으면 매 세션 리마인더가 반복된다.
- **운영 로그**: `_workspace/harness-ops-log.md`에 점검 결과 한 줄을 append한다 — 형식: `- YYYY-MM-DD [전체 점검|일일 점검] 신호 N건(요약) / 무결성 통과|문제 N건 / 제안 N건(요약)`. 이 로그가 "지난 점검에서 뭘 봤고 뭘 개선했는지"의 채팅 밖 단일 기록이다(개선 실행 기록은 metaskill이 `[개선]` 항목으로 append) — 리마인더 훅의 기한 전 상태 한 줄이 이 파일을 가리킨다.

## 출력 형식

1. 3신호 각각의 감지 여부와 근거
2. 구조 무결성 점검 결과 (통과/문제)
3. metaskill 제안 목록 (없으면 "없음")
4. 완료 마커 갱신 확인

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 진화 트리거 | "주 1회 관찰" 선언만 있고 절차 부재 → 미실행 | 고정 절차로 재현 가능한 점검 |
| 우회 감지 | .claude/ 직접 생성·레지스트리 불일치가 조용히 누적 | 무결성 점검에서 표면화 |
| 오버 엔지니어링 | 점검자가 매번 즉흥 개선안 양산 | 무신호 시 "유지" 보고로 종료 |
