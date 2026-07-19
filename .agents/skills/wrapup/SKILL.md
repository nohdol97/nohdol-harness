---
name: wrapup
description: "Wrap up the current session before clearing context - enumerate this session's work (changed files, decisions, done/open items, blockers), ask whether to persist it via work-tracker (cross-session/cross-machine epics) or carryover (local same-machine handoff note) or both or neither, run the chosen skill, then instruct the user to run /clear. A thin orchestrator - it does NOT reimplement persistence, it delegates to work-tracker and carryover. It CANNOT run /clear itself (that is a built-in CLI command, not a skill) - it only guides the user to run it. Slash-invoked only (/wrapup), NOT part of harness auto-routing (same as carryover). Do NOT use for mid-session progress logging without an impending clear (→ work-tracker directly), and do NOT auto-run /clear. Re-run keywords - wrapup, 마무리, 세션 마무리, clear 전 정리, 정리하고 clear, 컨텍스트 비우기 전."
---

# wrapup — clear 전 세션 마무리

## 왜 이 스킬인가

`/clear`는 Claude Code **내장 CLI 명령**이라 실행 순간 컨텍스트가 즉시 비워지고, 그 시점에 모델이 끼어들 턴이 없다. 그래서 "clear 하기 직전에 이번 세션에서 남길 것을 챙기는" 일이 매번 누락된다 — 여러 세션에 걸칠 작업을 등록하지 못하거나, 다음 세션에 이어받고 싶던 메모가 사라진다.

이 스킬은 그 간극만 메운다. `/clear`를 직접 고칠 수는 없으므로, **`/clear` 앞에 두는 마무리 관문**으로 동작한다 — 이번 세션 작업을 훑고, 무엇을 어디에 남길지 사용자에게 물어 처리한 뒤, "이제 `/clear` 하세요"를 안내한다.

**얇은 오케스트레이터다 — 저장 로직을 새로 짜지 않는다.** 실제 저장은 기존 `work-tracker`(세션 넘김 정형 추적)와 `carryover`(로컬 가벼운 핸드오프)에 위임한다. 이 스킬이 하는 일은 ⓐ 세션 작업 수집 ⓑ 어디에 남길지 갈래질 ⓒ clear 안내, 이 세 가지뿐이다. 이유: 저장 로직을 복제하면 두 스킬과 어긋나 부채가 된다(ADR 007·루트 AGENTS.md 16절).

**이 스킬은 슬래시(`/wrapup`)로만 호출된다** — carryover와 같은 이유로 하네스 자동 라우팅(CLAUDE.md 앵커·§7)에 등록하지 않는다. 사용자가 "이제 세션을 마무리하고 컨텍스트를 비우겠다"고 명시적으로 결정하는 순간에만 동작해야 하는 도구이기 때문이다.

## 핵심 제약 — 자동 clear 불가

**이 스킬은 `/clear`를 대신 실행할 수 없다.** `/clear`는 CLI 내장 명령이고 스킬은 그것을 호출할 수단이 없다. 마무리 처리가 끝나면 **사용자에게 직접 `/clear`를 입력하도록 안내**하는 것으로 마친다. "자동으로 clear까지 해줄게" 같은 약속을 하지 않는다 — 지키지 못한다.

## 절차

### 1. 이번 세션 작업 훑기

이번 세션에서 무슨 일을 했는지 수집한다. 최소한:
- **변경/추가된 파일** — `git status`·`git diff --stat`로 확인(커밋 여부 무관)
- **내린 결정·합의** — 대화에서 확정된 방향·선택
- **완료 항목 / 미완 항목 / 블로커** — 지금 끝난 것, 다음에 이어야 할 것, 막힌 것

수집 결과를 사용자에게 **한국어로 짧게 요약**해 보여준다(무엇을 남길지 판단할 근거).

### 2. 무엇을 어디에 남길지 묻기

AskUserQuestion으로 사용자에게 저장 대상을 고르게 한다. 선택지:

- **work-tracker에 등록** — 여러 PR·며칠 규모·크로스 머신 작업, GitHub 이슈로 정형 추적
- **carryover 이월 노트** — 이번 세션→다음 세션 로컬 가벼운 핸드오프(같은 머신)
- **둘 다** — 정형 추적 + 로컬 메모를 모두
- **아무것도 안 남김** — 그냥 clear (남길 게 없거나 이미 커밋으로 충분)

경계가 헷갈리면 아래 표(work-tracker vs carryover)를 근거로 사용자에게 판단을 돕는 한 줄을 덧붙인다. **자동으로 정하지 말고 사용자에게 확정을 받는다** — 어디에 남길지는 사용자의 작업 계획에 달렸다.

### 3. 선택에 위임

고른 대상의 스킬을 그대로 호출한다(중복 구현 금지):
- work-tracker 선택 → `work-tracker` 스킬(등록 모드)
- carryover 선택 → `carryover` 스킬(저장 모드)
- 둘 다 → 두 스킬 순차 호출. 이때 **같은 내용을 양쪽에 중복 적재하지 않는다** — 정형 추적이 필요한 항목은 work-tracker로, 로컬 핸드오프 메모는 carryover로 나눠 담는다(아래 경계 표).

각 스킬이 자기 완료 기준으로 마친 뒤에만 다음 단계로 간다.

### 4. `/clear` 안내

저장이 끝나면 마무리 요약과 함께 **사용자에게 `/clear` 입력을 안내**한다. 예: "남길 것을 정리했습니다. 이제 `/clear`를 입력하면 컨텍스트가 비워지고, 저장한 내용은 다음 세션에서 이어받을 수 있습니다." 스킬이 clear를 대신 실행하지 않는다(위 핵심 제약).

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
| 저장 위치 판단 | 매번 work-tracker냐 carryover냐 헷갈림 | 경계 표로 갈래질 후 위임 |
| 중복 구현 | 마무리 로직을 매번 즉흥 처리 | 기존 두 스킬 재사용, 로직 단일 원본 유지 |
