# ADR 056: 일일·주간 하네스 리뷰 폐기

- 날짜: 2026-10-08
- 상태: 채택

## 결정
사용자 요청에 따라 `harness-review` 스킬의 일일·주간 모드와 SessionStart 알림을 제거한다. 정기 점검을 다른 스킬에 재배정하지 않는다. 관찰된 신호에 따른 metaskill 개선과 수동 `integrity-check.py`는 유지한다.

## 근거와 범위
사용자가 두 모드의 제거를 명시했다. 제거를 위한 추가 질문은 없으며 개인 설치처와 독립 검증 가능 여부를 확인했다. 연결된 지식 소스 진입점은 읽기 시간 초과로 이용하지 못했고 외부 주장은 채택하지 않았다.

스킬만 지우면 시작 훅이 사라진 스킬을 계속 호출하고 무결성 검사가 삭제를 오류로 판정한다. 따라서 두 런타임 등록과 필수 훅 목록도 함께 제거한다. 공유 프로필 판독기의 테스트는 공용 스위트로 옮긴다.

새 의무나 발동 조건은 추가하지 않는다. 사용자 지시로 기존 기능을 폐기하므로 실패 횟수 기반 신설 조건은 적용하지 않는다. 일일·주간 실행 경로 모두 삭제되는지 회귀 검사한다.

## 영향
- 스킬·알림 훅 삭제, Claude·Codex 등록 및 무결성 목록 갱신.
- 활성 규칙·라우팅·설치 설명·한국어 요약·목록 갱신.
- 기존 ADR과 스펙의 당시 기록은 보존하고 폐기 배너로 현재 상태를 표시.
- 로컬 과거 결과·마커는 삭제하지 않으며 새 실행 경로에서 읽지 않는다.

### 변경 경로

- `.agents/githooks/tdd-gate.py`
- `.agents/hooks/_common.py`
- `.agents/hooks/_common_test.py`
- `.agents/hooks/dispatch-gate_test.py`
- `.agents/hooks/harness-review-reminder.py`
- `.agents/hooks/harness-review-reminder_test.py`
- `.agents/hooks/harness-review-retirement_test.py`
- `.agents/hooks/integrity-check.py`
- `.agents/hooks/integrity-check_test.py`
- `.agents/hooks/token-efficiency-contract_test.py`
- `.agents/hooks/worklog-reminder.py`
- `.agents/skills/README.ko.md`
- `.agents/skills/branch-workflow/SKILL.md`
- `.agents/skills/doc-writer/references/templates.md`
- `.agents/skills/harness-install/SKILL.md`
- `.agents/skills/harness-review/SKILL.md`
- `.agents/skills/metaskill/SKILL.md`
- `.agents/skills/orchestrate/SKILL.md`
- `.agents/skills/project-status/SKILL.md`
- `.agents/skills/tool-audit/SKILL.md`
- `.agents/skills/wrapup/SKILL.md`
- `.claude/settings.json`
- `.codex/config.toml`
- `AGENTS.ko.md`
- `AGENTS.md`
- `CLAUDE.md`
- `README.md`
- `docs/README.md`
- `docs/adr/013-evolution-signal-expansion.md`
- `docs/adr/044-mattpocock-skills-partial-adoption.md`
- `docs/harness-changelog.md`
- `docs/specs/2026-07-14-harness-review-reminder-hook.md`
- `docs/specs/2026-10-08-retire-harness-review.md`

## 검증
[제거 스펙](../specs/2026-10-08-retire-harness-review.md)의 완료 기준으로 검사한다. 실제 새 CLI 세션과 Windows 호스트 실행은 미검증이다.

## 변경 이력
| 날짜 | 변경 내용 | 대상 | 사유 |
|---|---|---|---|
| 2026-10-08 | 두 정기 리뷰 모드 폐기 | 스킬·시작 훅·활성 안내 | 사용자 요청 |
