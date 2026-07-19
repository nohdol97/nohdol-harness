---
name: wrapup
description: "Wrap up a session before clearing context - enumerate this session's work and ask whether to persist it via work-tracker (cross-session epics) or carryover (local handoff note); and ONLY when signals exist, capture harness/project improvement signals (repeated requests/failures, harness bypass, reusable lessons, subproject skill/agent candidates), log lessons to auto-memory, and PROPOSE metaskill follow-up. Thin orchestrator delegating to work-tracker/carryover/metaskill; it does NOT apply harness changes itself (capture and propose only) and CANNOT run /clear (a CLI command) - only guides the user. Complements harness-review (end-of-session capture vs periodic scan). Slash-invoked only, NOT auto-routed. Do NOT use for mid-session logging without an impending clear (→ work-tracker), nor auto-apply harness edits or auto-run /clear. Re-run keywords - wrapup, 마무리, 세션 마무리, clear 전 정리, 세션 회고."
---

# wrapup — clear 전 세션 마무리

## 왜 이 스킬인가

`/clear`는 Claude Code **내장 CLI 명령**이라 실행 순간 컨텍스트가 즉시 비워지고, 그 시점에 모델이 끼어들 턴이 없다. 그래서 "clear 하기 직전에 이번 세션에서 남길 것을 챙기는" 일이 매번 누락된다 — 여러 세션에 걸칠 작업을 등록하지 못하거나, 다음 세션에 이어받고 싶던 메모가 사라지거나, **이번 세션에서 드러난 하네스·프로젝트 개선 신호가 컨텍스트와 함께 증발한다.**

이 스킬은 그 간극을 메운다. `/clear`를 직접 고칠 수는 없으므로, **`/clear` 앞에 두는 마무리 관문**으로 동작한다 — 이번 세션 작업을 훑고, 무엇을 어디에 남길지 물어 처리하고, **개선 신호가 있으면 포착·제안**한 뒤, "이제 `/clear` 하세요"를 안내한다.

**얇은 오케스트레이터다 — 저장·반영 로직을 새로 짜지 않는다.** 작업 저장은 `work-tracker`·`carryover`에, 하네스·프로젝트 개선의 실제 반영은 `metaskill`에 위임한다. 이 스킬이 하는 일은 ⓐ 세션 작업 수집·저장 갈래질 ⓑ 개선 신호 포착·제안 ⓒ clear 안내다. 이유: 저장·반영 로직을 복제하면 원본 스킬과 어긋나 부채가 된다(ADR 007·루트 AGENTS.md 16절).

**이 스킬은 슬래시(`/wrapup`)로만 호출된다** — carryover와 같은 이유로 하네스 자동 라우팅(CLAUDE.md 앵커·§7)에 등록하지 않는다. 사용자가 "이제 세션을 마무리하고 컨텍스트를 비우겠다"고 명시적으로 결정하는 순간에만 동작해야 하는 도구이기 때문이다.

## 두 가지 핵심 제약

1. **자동 clear 불가**: 이 스킬은 `/clear`를 대신 실행할 수 없다(CLI 내장 명령). 처리가 끝나면 **사용자에게 직접 `/clear` 입력을 안내**하는 것으로 마친다. "자동으로 clear까지 해줄게" 같은 약속을 하지 않는다.
2. **개선사항 자동 반영 불가**: 회고 단계는 신호를 **포착·기록·제안**까지만 한다. 하네스·프로젝트를 **직접 수정하지 않는다** — 무단 하네스·프로젝트 변경은 가드레일 위반(루트 AGENTS.md 3절)이고 metaskill은 무단 생성·폐기를 금지한다(하네스는 사용자의 운영 자산). 실제 반영은 **사용자 승인 후 metaskill 경로**로만 간다(기존 진화 게이트와 동일).

## 절차

### 1. 이번 세션 작업 훑기

이번 세션에서 무슨 일을 했는지 수집한다. 최소한:
- **변경/추가된 파일** — `git status`·`git diff --stat`로 확인(커밋 여부 무관)
- **내린 결정·합의** — 대화에서 확정된 방향·선택
- **완료 항목 / 미완 항목 / 블로커** — 지금 끝난 것, 다음에 이어야 할 것, 막힌 것

수집 결과를 사용자에게 **한국어로 짧게 요약**해 보여준다.

### 2. 이번 세션 회고 — 개선 신호 포착 (신호 있을 때만)

이번 세션을 되돌아보며 **개선 신호가 있었는지만 가볍게 확인**한다. 대상:
- **하네스 개선 신호** (루트 AGENTS.md 8절 확장 신호 ①~③): 같은 유형 요청 반복 / 같은 실패·같은 사용자 정정 반복 / **하네스를 우회해 처리한 사례**
- **재발 방지 교훈** ("실수 즉시 기록" — 8절): 2회 반복을 기다릴 것 없이 1회 발생이라도 재발 방지 가치가 있는 실수·교훈
- **프로젝트별 개선**: 하위 프로젝트 작업 중 드러난 스킬·에이전트 후보(§12 지연 생성 트리거), 하위 AGENTS.md의 미비점

**신호가 없으면 "이번 세션 개선 신호 없음" 한 줄로 넘어간다** — 회고를 무겁게 만들면 매번 우회된다(최소주의). 억지로 신호를 만들지 않는다.

**신호가 있으면**:
- **교훈은 지금 즉시 기록한다** (제안 대기 없이 — 8절 "실수 즉시 기록"): Claude 세션은 auto-memory(feedback 타입)에 기록하되 **인덱스 줄에는 교훈 요지가 아니라 발동 상황**(어떤 작업에서 이걸 확인해야 하는지)을 쓴다. Codex 세션은 같은 저장소의 교훈 파일과 MEMORY.md 인덱스를 직접 기록한다.
- **하네스·프로젝트 반영이 필요한 것은 제안만 한다** — "이번 세션에서 〈신호〉를 관찰했습니다. metaskill로 반영할까요?"(하네스 자산) 또는 하위 AGENTS.md "스킬 후보" 섹션 기록 제안(프로젝트). **사용자가 승인하면 그때 metaskill로**, 승인 전에는 아무것도 고치지 않는다.

**harness-review와의 경계 (중복 아님)**: 이 회고는 세션 **끝**에 맥락이 살아있을 때 신호를 **포착**하는 단계이고, `harness-review`는 세션 **시작** 시 마커로 주기(1일/7일)를 판정해 누적 흔적을 **스캔·제안**하는 단계다. wrapup의 포착은 harness-review를 대체하지 않고 **그 스캔의 입력을 정확하게** 만든다 — 둘은 상보다.

### 3. 무엇을 어디에 남길지 묻기

AskUserQuestion으로 저장 대상을 고르게 한다: **work-tracker 등록**(여러 PR·며칠 규모·크로스 머신) / **carryover 이월 노트**(다음 세션 로컬 핸드오프) / **둘 다** / **아무것도 안 남김**. 경계가 헷갈리면 아래 표를 근거로 한 줄 덧붙인다. **자동으로 정하지 말고 사용자 확정을 받는다.**

### 4. 선택에 위임

고른 대상의 스킬을 그대로 호출한다(중복 구현 금지): work-tracker 선택 → `work-tracker`(등록 모드), carryover 선택 → `carryover`(저장 모드), 둘 다 → 순차 호출하되 **같은 내용을 양쪽에 중복 적재하지 않는다**(정형 추적은 work-tracker, 로컬 메모는 carryover로 분담 — 아래 표). 각 스킬이 완료된 뒤에만 다음으로 간다.

### 5. `/clear` 안내

저장·제안이 끝나면 마무리 요약과 함께 **사용자에게 `/clear` 입력을 안내**한다(스킬이 clear를 대신 실행하지 않는다 — 위 핵심 제약 1).

## work-tracker vs carryover 경계 (판단 근거)

| | work-tracker | carryover |
|---|---|---|
| 저장처 | GitHub Issues / `docs/backlog.md` (git 추적, 크로스 머신) | `_workspace/carryover/*.md` (gitignore, **같은 머신 로컬**) |
| 대상 | 여러 PR·며칠 규모 에픽, 정형 | 이번 세션→다음 세션 **가벼운 핸드오프 메모** |
| 유실 위험 | 낮음(원격 백업) | 로컬만 — 머신 밖으로 못 넘김 |

→ 정식·크로스 머신 추적이 필요하면 work-tracker, 로컬 스크래치 핸드오프면 carryover. 이 둘을 섞으면 이슈 무덤이 생기거나(모든 걸 GitHub에) 중요한 크로스 머신 작업이 로컬에만 남아 유실된다.

## with / without

| 지표 | 이 스킬 없이 | 이 스킬로 |
|---|---|---|
| clear 전 마무리 | 컨텍스트를 비우고 나서야 "등록할걸" 후회 | clear 직전 관문에서 저장 여부를 강제로 챙김 |
| 개선 신호 | 세션 끝 생생한 신호가 증발, harness-review가 사후 재구성 | 맥락이 살아있을 때 포착 → 즉시 기록·제안 |
| 저장 위치 판단 | 매번 work-tracker냐 carryover냐 헷갈림 | 경계 표로 갈래질 후 위임 |
| 중복 구현 | 마무리·반영 로직을 매번 즉흥 처리 | 기존 스킬(work-tracker·carryover·metaskill) 재사용 |
