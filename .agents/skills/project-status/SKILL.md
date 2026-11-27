---
name: project-status
description: "Summarize all registered projects from REGISTRY.md with explorer fan-out for git state, activity, harness presence, and stale rows. Use for 프로젝트 상태, 전체 현황, 상태 요약, what changed across projects, cross-project planning. Re-run: project-status, status, overview, 현황, 상태 요약."
---

# project-status — Full Project Status Report


**Runtime routing — root AGENTS.md §11 (ADR 053·062)**: every installation profile uses ordinary subagent dispatch and independent review; the **Pi runtime exception** adds only Pi-native runtime and checkout rules. Corporate root-edit and data-egress restrictions stay unchanged.

## Why this skill

In a multi-project management harness, "what state is everything in right now" is the most frequently needed question, but investigating it ad hoc each time means different items get checked per project, making comparison impossible. This skill collects **the same items in the same way** and produces a single report. Also used as advance reconnaissance before planning cross-project work.

## Procedure

### Phase 0 — Preconditions

- Read REGISTRY.md. **If it does not exist, stop and direct the user to harness-install** (installation incomplete).
- If the registry is empty, report "no registered projects" and finish.
- Set `_workspace/project-status-<date>/` as the working directory, and record events per orchestrate's **team-log event contract** (mode B included).

### Phase 1 — Parallel collection (**execution mode:** subagents)

Partition the registry rows across explorers per the orchestrate mode-B agent count (default 1–3 explorers, each given a disjoint set of projects; more than 3 only when the partitions cannot be covered within the work cap, with that reason in the Phase 0 budget) and **dispatch all of them simultaneously in one turn** (the mode-B concurrent-issuing rule). Each prompt carries the mode-B fetch instruction, because the `project/<name>/` checkout is nobody's refresh target and root §5 forbids asserting state from an unrefreshed read. Fixed collection items for each project:

1. git state: whether it is an independent repository; `git -C project/<name> fetch origin` first, then the 3 most recent commits from `origin/main`; then `git -C project/<name> worktree list` and, for each entry, its branch and `git -C <entry> status --short` (uncommitted work lives in worktrees, invisible from the main checkout). A fetch that fails is reported as unverified, not as "no change"
2. Harness: whether root `.agents/projects/<name>/AGENTS.md` exists, plus the list of lazily created `skills/`·`agents/` (root AGENTS.md section 12 — the harness lives centrally, not in the project directory). If harness files are found inside `project/<name>/`, report it as a bypass signal
3. Registry cross-check: whether the actual directory layout matches the registry row (stack, sub-structure)
4. Notable findings: only those with evidence (bloated build artifacts, signs of abandonment, etc.)

Output: `phase1_explorer-<project>_status.md` (one file per project, even when one explorer covers several)

### Phase 2 — Integration (**execution mode:** integrator solo)

The integrator merges per the gate principles, but since this skill's final report is a status report, the sections are fixed as follows:

- **Needs attention**: evidence-backed issues such as neglected uncommitted changes, registry mismatches, missing harness
- **Per-project summary table**: name / git state / recent activity / harness / registry match
- **Recommendations**: proposals linked to metaskill (registry updates, harness creation, etc.)

### Final response

Report to the user only the needs-attention count and items, the summary table, and the path to the full report.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Consistency | Different items checked per project → no comparison possible | Fixed 4-item collection enables comparison |
| Freshness | Registry-reality mismatches silently accumulate | Registry cross-check on every run |
| Time | Sequential investigation, one project at a time | Parallel explorer fan-out |
