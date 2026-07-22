# ADR 029: 세션 훅 Codex 파리티 기본값 — 미검증 이벤트도 선제 등록

- **날짜**: 2026-07-22
- **변경 내용**: 세션 훅 등록 정책을 "확인된 이벤트만 Codex 등록"(ADR 019 — SessionStart 2종)에서 **"세션 훅 신설 시 `.claude/settings.json`과 `.codex/hooks.json`에 대칭 등록이 기본값"**으로 확장한다. Codex에서 지원이 미확인인 이벤트(PostToolUse/PreToolUse 등)도 **선제 등록**한다. 첫 적용: gate-reminder(ADR 028)를 `.codex/hooks.json`에 등록.
- **대상**: `.codex/hooks.json`, AGENTS.md 11절, docs/adr/028(결정 2 갱신), docs/specs/2026-07-22-gate-reminder-hook.md
- **사유**: 사용자 지시(2026-07-22 — "앞으로 훅도 일단은 Codex에서도 적용될 수 있도록"). 선제 등록이 안전한 근거: ① Codex 훅 포맷은 Claude와 동일(`hooks.EventName[].hooks[].command` — ADR 019)이라 미지원 이벤트 항목은 무시될 뿐이고, ② 훅 스크립트 자체가 전면 fail-open(비정상 stdin·필드 부재 → exit 0)이라 스키마가 달라도 세션을 막지 않으며, ③ 지원될 경우 즉시 방어가 생긴다 — 기다렸다 등록하는 것보다 등록해 두고 확인하는 쪽이 공백이 짧다.

## 설계 결정

1. **matcher는 양 CLI 도구명 알터네이션**: Codex의 도구명은 Claude와 다르므로(shell/apply_patch 계열) `.codex/hooks.json`의 matcher에 두 계열을 함께 적는다(예: `Bash|shell|local_shell`, `Edit|Write|MultiEdit|NotebookEdit|apply_patch`). 과잉 매칭 비용은 없다 — matcher는 이벤트 선별일 뿐, 판단은 스크립트가 한다.
2. **명령 경로는 `$PWD`**: ADR 019와 동일(Codex엔 `CLAUDE_PROJECT_DIR`가 없고, 스크립트는 cwd 폴백 내장).
3. **한계의 정직한 수용**: Codex 훅은 실험 기능·Windows 미지원(ADR 019)이고, PreToolUse 상당 이벤트의 존재·차단 시맨틱스(exit 2)·stdin 계약은 **미확인**이다. 등록은 "적용될 수 있는 상태"를 만들 뿐 동작 보장이 아니다 — 실검증은 Codex 설치 머신에서 하고, 스키마 차이가 확인되면 스크립트에 필드 매핑을 추가한다(추측 매핑을 미리 넣지 않는다 — 16절 최소주의).
4. **integrity-check는 훅 대칭을 강제하지 않는다**: 대칭 검사(R12)는 agent 어댑터 한정 유지. 훅은 이벤트 모델이 CLI마다 달라 기계 검사로 1:1을 강제하면 정당한 비대칭(agentsview-daemon 제외 등)이 오탐이 된다 — 대칭 의무는 이 ADR과 11절 문서가 운반한다.
