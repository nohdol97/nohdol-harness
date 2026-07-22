---
name: project-status
description: Summarize the status of all registered projects in one report. Reads REGISTRY.md, fans out explorer agents per project (git state, recent activity, harness presence, stale registry rows), and integrates findings into a single must-know report. Use when the user says 프로젝트 상태, 전체 현황, 상태 요약, what changed across projects, or before planning cross-project work. Re-run keywords - status, overview, 현황, 상태 요약.
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

Deploy one explorer per registry row in parallel (orchestrate mode B, cap 10–20 — **dispatch all of them simultaneously in one turn**, the mode-B simultaneous-dispatch rule). Fixed collection items for each explorer:

1. git state: whether it is an independent repository, branch, uncommitted changes, 3 most recent commits
2. Harness: whether root `.agents/projects/<name>/AGENTS.md` exists, plus the list of lazily created `skills/`·`agents/` (root AGENTS.md section 12 — the harness lives centrally, not in the project directory). If harness files are found inside `project/<name>/`, report it as a bypass signal
3. Registry cross-check: whether the actual directory layout matches the registry row (stack, sub-structure)
4. Notable findings: only those with evidence (bloated build artifacts, signs of abandonment, etc.)

Output: `phase1_explorer-<project>_status.md`

### Phase 2 — Integration (**execution mode:** integrator solo)

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
