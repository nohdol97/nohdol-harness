---
name: project-status
description: "Summarize all registered projects from REGISTRY.md with explorer fan-out for git state, activity, harness presence, and stale rows. Use for 프로젝트 상태, 전체 현황, 상태 요약, what changed across projects, cross-project planning. Re-run: project-status, status, overview, 현황, 상태 요약."
---

# project-status — Full Project Status Report

## Why this skill

In a multi-project management harness, "what state is everything in right now" is the most frequently needed question, but investigating it ad hoc each time means different items get checked per project, making comparison impossible. This skill collects **the same items in the same way** and produces a single report. Also used as advance reconnaissance before planning cross-project work.

## Procedure

### Phase 0 — Preconditions

- Read REGISTRY.md. **If it does not exist, stop and direct the user to harness-install** (installation incomplete).
- If the registry is empty, report "no registered projects" and finish.
- Set `_workspace/project-status-<date>/` as the working directory, and record events per orchestrate's **team-log event contract** (mode B included).

### Phase 1 — Parallel collection (**execution mode:** subagents)

> **`사내` profile — collection runs sequentially in the main loop instead** (ADR 042; contract single source: orchestrate's Install-site exemption). Dispatch is blocked at the call there and no override marker exists, so the fan-out below is unreachable. **The skill still runs and still produces the report**: walk the registry rows one at a time, collect the same four fixed items per row, and write them straight into the Phase 2 sections — the intermediate `phase1_explorer-<project>_status.md` artifacts have no author, so skip them and keep the final report only. Say in the report that collection ran without fan-out; the coverage is the same but the wall-clock and the context cost are not, so a large registry may need the run split across turns.

Deploy one explorer per registry row in parallel (orchestrate mode B, cap 10–20 — **dispatch all of them simultaneously in one turn**, the mode-B simultaneous-dispatch rule). Fixed collection items for each explorer:

1. git state: whether it is an independent repository, branch, uncommitted changes, 3 most recent commits
2. Harness: whether root `.agents/projects/<name>/AGENTS.md` exists, plus the list of lazily created `skills/`·`agents/` (root AGENTS.md section 12 — the harness lives centrally, not in the project directory). If harness files are found inside `project/<name>/`, report it as a bypass signal
3. Registry cross-check: whether the actual directory layout matches the registry row (stack, sub-structure)
4. Notable findings: only those with evidence (bloated build artifacts, signs of abandonment, etc.)

Output: `phase1_explorer-<project>_status.md`

### Phase 2 — Integration (**execution mode:** integrator solo)

> **`사내` profile — the main loop merges** (same clause as Phase 1). This fan-in is not a review, so ADR 038 left it alone; ADR 042 blocks it anyway, because it blocks the dispatch rather than the purpose.

The integrator merges per the gate principles, but since this skill's final report is a status report, the sections are fixed as follows:

- **Needs attention**: evidence-backed issues such as neglected uncommitted changes, registry mismatches, missing harness
- **Per-project summary table**: name / git state / recent activity / harness / registry match
- **Recommendations**: proposals linked to metaskill·harness-review (registry updates, harness creation, etc.)

### Final response

Report to the user only the needs-attention count and items, the summary table, and the path to the full report.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Consistency | Different items checked per project → no comparison possible | Fixed 4-item collection enables comparison |
| Freshness | Registry-reality mismatches silently accumulate | Registry cross-check on every run |
| Time | Sequential investigation, one project at a time | Parallel explorer fan-out |
