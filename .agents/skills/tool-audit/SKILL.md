---
name: tool-audit
description: "Audit whether an installed external tool (plugin, MCP server, skill pack, framework) earns its keep - measure actual usage with agentsview across recorded sessions, quantify always-on token cost and feature overlap with harness assets, then propose keep/trim/remove with measured evidence and a backup/rollback path. Use when the user asks whether a tool or plugin is worth keeping, wants usage measured, or wants installed tooling cleaned up - 'is X plugin useful', 'do we actually use X', 도구 감사, 플러그인 감사, 사용 실측, 도구 정리. Do NOT use for the periodic evolution-signal scan or harness-native skill usage stats (→ harness-review), nor for actually applying removals or harness edits (→ metaskill after user approval). Re-run keywords - tool-audit, usage audit, plugin audit, 도구 감사, 사용 실측, 플러그인 정리."
---

# tool-audit — 외부 도구 사용 실측 감사

## 왜 이 스킬인가

외부 도구(플러그인·MCP 서버·스킬 팩·프레임워크)는 설치는 한 번이지만 비용은 매 세션이다 — 상시 로드되는 description·도구 스키마·임포트가 컨텍스트를 차지하고, 하네스 스킬과 트리거가 겹치면 라우팅을 오염시킨다. 이 감사 절차는 같은 유형 요청 3회+ 관찰로 정식화됐다(2026-07-18, 신호 ①): SuperClaude 제거(실측 0건/전 메시지 51,331건, 세션당 ~36k 토큰), gstack·MCP·플러그인 감사가 각 세션에서 절차를 재발명하고 있었다. **원칙: 감(느낌)이 아니라 실측이 판정한다** — "쓸 것 같다"는 유지 근거가 아니다.

## 절차

1. **대상·비용면 확정**: 도구 이름, 설치 위치(전역 `~/.claude/`·`~/.agents/` / 프로젝트), 로드 방식을 확인한다. **상시 로드 여부가 핵심** — 세션마다 컨텍스트에 실리는 것(스킬 description, MCP 도구 스키마, CLAUDE.md 임포트)만 고정 비용이 있고, 명시 호출 전용은 방치 비용이 거의 없다(이 경우 감사 실익도 낮음을 사용자에게 알린다).
2. **사용 실측 (agentsview)**: 기록된 전 세션에서 사용 흔적을 검색한다. 검색어는 3계열로 설계한다 — ① 도구의 명령·트리거 문구(`/sc:`, `gstack` 등) ② 도구 호출명(`mcp__<서버>__` 접두) ③ 도구가 만든 산출물 경로·마커. 집계: 매칭 메시지 수, 검색 모수(전체 메시지 수 — 분모 없는 실측은 근거가 아니다), 최근 사용일. **검색 0건은 "트리거가 안 잡힌 것"일 수도 있으므로 검색어를 도구 문서에서 역으로 뽑아 2회 이상 교차 확인**한다(false negative 방어).
3. **고정 비용 측정**: 상시 로드분의 토큰 크기를 추정한다(파일 크기 기반 개산이면 개산임을 명시). 세션당 비용 × 세션 빈도가 유지 비용이다.
4. **중복 판정**: 같은 트리거·기능의 하네스 스킬·에이전트가 있는지 대조한다(루트 AGENTS.md 7절 7항 — 겹치면 하네스가 우선이므로 외부 도구는 사실상 죽은 경로가 된다).
5. **판정과 제안**: 아래 기준표로 제안을 만들고 근거 수치를 붙인다. 판정은 제안까지다 — **실행(제거·설정 변경)은 사용자 승인 후**, 하네스 자산이 얽히면 metaskill 경유로 한다.

| 실측 결과 | 제안 |
|---|---|
| 사용 0건 + 상시 비용 有 | 제거 (백업 후) |
| 사용 少 + 하네스와 기능 중복 | 하네스로 통합 후 제거, 또는 트리거 경계 조정 |
| 실사용 有 + 중복 無 | 유지 (필요 시 부정 트리거로 경계만 정리) |
| 실측 불가(기록 없음·검색 불능) | 판정 보류를 정직하게 보고 — 추정으로 제거하지 않는다 |

6. **백업·복구 경로 명시**: 제거 제안에는 반드시 복구 방법(설정 백업 위치, 재설치 명령)을 포함한다 — SuperClaude 전례(백업 후 제거, 복구 절차는 세션 기록 참조). 제거 실행 후에는 결과를 `_workspace/harness-ops-log.md`에 한 줄 기록한다.

## 산출물

- 발견이 많으면 `_workspace/tool-audit-<도구명>/report.md`(영어 — 루트 15절, 점진적 공개 2단)에 쓰고, 사용자 보고는 한국어로 소화해 전달한다. 짧은 감사는 채팅 보고로 충분하다(리포트 파일 강제는 노이즈).

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| 절차 일관성 | 세션마다 검색어·판정 기준 재발명 | 3계열 검색어·판정 기준표 고정 |
| 판정 근거 | "안 쓰는 것 같다" 인상 판정 | 매칭 수/모수/최근 사용일 실측 |
| 안전성 | 제거 후 복구 경로 부재 | 백업·복구 경로 필수 명시 |
