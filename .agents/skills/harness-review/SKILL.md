---
name: harness-review
description: Weekly harness operations review. Scans recent git history, _workspace remnants, and session patterns for the three evolution triggers (3+ repeated request types, 2+ repeated failures, harness bypass), verifies symlink integrity and registry freshness, then proposes concrete metaskill actions. Use when the user says 주간 점검, 하네스 리뷰, weekly review, harness review, or when a week has passed since the last review. Re-run keywords - harness-review, weekly, evolve, 주간 점검, 진화.
---

# harness-review — 주간 하네스 운영 점검

## 왜 이 스킬인가

루트 AGENTS.md 8절은 진화 트리거 3신호를 "주 1회 관찰"하는 것을 운영 습관으로 요구한다. 관찰 절차가 스킬로 고정되어 있지 않으면 이 습관은 몇 주 안에 증발한다 — 하네스는 쓰이면서 어긋난 부분이 드러날 때만 진화할 수 있다. 이 스킬은 **관찰과 제안**만 담당한다. 실제 생성·개선의 실행은 metaskill의 몫이다 (역할 분리: 관찰자가 곧바로 실행까지 하면 제안의 근거 검증이 생략된다).

## 절차

### 1. 신호 수집 (진화 트리거 3신호)

| 신호 | 관찰 방법 |
|---|---|
| 반복 요청 3회+ | 최근 세션 기억·`_workspace/` 작업명들·git 커밋 메시지에서 같은 유형 작업의 반복 확인 |
| 반복 실패 2회+ | team-log.jsonl의 실패 이벤트, 같은 종류의 재작업 커밋(fix 연쇄) 확인 |
| 하네스 우회 | orchestrate 없이 처리된 다중 프로젝트 작업, `.agents/` 밖에 생긴 에이전트·스킬 정의, 레지스트리에 없는 프로젝트 디렉토리 |

### 2. 구조 무결성 점검

- 심링크: `readlink .claude/agents .claude/skills`가 `../.agents/*`를 가리키는지. **`.claude/` 아래에 심링크가 아닌 실파일이 생겼는지** (생겼다면 우회 신호 — 원본은 `.agents/`에만 있어야 한다).
- 레지스트리: `project/` 하위 실제 디렉토리 목록과 AGENTS.md 레지스트리 표가 일치하는지.
- 잔여물: `_workspace/`에 종료 기록(team-log의 team_delete) 없는 작업 디렉토리가 방치되어 있는지.
- 변경 이력: 최근 하네스 커밋마다 변경 이력 테이블 갱신이 동반되었는지 (`git log -p -- AGENTS.md`).

### 3. 제안 생성

- 신호가 감지되면: 어떤 신호가, 어떤 근거로, 어떤 에이전트/스킬 신설·개선으로 이어지는지를 **metaskill 호출 제안** 형태로 정리해 사용자에게 보고한다. 승인 없이 생성하지 않는다.
- 신호가 없으면: "신호 없음 — 현재 구조 유지"라고 보고하고 끝낸다. **무신호에 개선을 지어내지 않는다** (완벽주의 금지 — 루트 AGENTS.md 9절).

## 출력 형식

1. 3신호 각각의 감지 여부와 근거
2. 구조 무결성 점검 결과 (통과/문제)
3. metaskill 제안 목록 (없으면 "없음")

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 진화 트리거 | "주 1회 관찰" 선언만 있고 절차 부재 → 미실행 | 고정 절차로 재현 가능한 점검 |
| 우회 감지 | .claude/ 직접 생성·레지스트리 불일치가 조용히 누적 | 무결성 점검에서 표면화 |
| 오버 엔지니어링 | 점검자가 매번 즉흥 개선안 양산 | 무신호 시 "유지" 보고로 종료 |
