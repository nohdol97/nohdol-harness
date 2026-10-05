---
name: project-status
description: "Summarize all registered projects from REGISTRY.md with explorer fan-out for git state, activity, harness presence, and stale rows. Use for 프로젝트 상태, 전체 현황, 상태 요약, what changed across projects, cross-project planning. Re-run: project-status, status, overview, 현황, 상태 요약."
---

# project-status — Full Project Status Report


**Runtime routing — root AGENTS.md §11 (ADR 053·054)**: the **Pi runtime exception** preserves ordinary dispatch/independent review in Pi-native sessions. Corporate Claude/Codex hosts instead delegate exploration/implementation to internal Pi workers through `orchestrate/references/corporate-pi.md`; design and final review stay in the host, native dispatch remains blocked except infra authoring. This takes precedence over older sequential-work wording below. Personal routing, corporate root-edit and data-egress restrictions stay unchanged.

## Why this skill

In a multi-project management harness, "what state is everything in right now" is the most frequently needed question, but investigating it ad hoc each time means different items get checked per project, making comparison impossible. This skill collects **the same items in the same way** and produces a single report. Also used as advance reconnaissance before planning cross-project work.

## Procedure

### Phase 0 — Preconditions

- Read REGISTRY.md. **If it does not exist, stop and direct the user to harness-install** (installation incomplete).
- If the registry is empty, report "no registered projects" and finish.
- Set `_workspace/project-status-<date>/` as the working directory, and record events per orchestrate's **team-log event contract** (mode B included).

### Phase 1 — Parallel collection (**execution mode:** subagents)

> **Corporate Claude/Codex host**: collect registry projects with parallel Pi explorers using `orchestrate/references/corporate-pi.md`; record their reports and actual coverage. The host integrates the result. Missing Pi configuration is reported as unavailable collection, not silently converted to sequential host exploration.

Deploy one explorer per registry row in parallel (orchestrate mode B, cap 10–20 — **dispatch all of them simultaneously in one turn**, the mode-B simultaneous-dispatch rule). Fixed collection items for each explorer:

1. git state: whether it is an independent repository, branch, uncommitted changes, 3 most recent commits
2. Harness: whether root `.agents/projects/<name>/AGENTS.md` exists, plus the list of lazily created `skills/`·`agents/` (root AGENTS.md section 12 — the harness lives centrally, not in the project directory). If harness files are found inside `project/<name>/`, report it as a bypass signal
3. Registry cross-check: whether the actual directory layout matches the registry row (stack, sub-structure)
4. Notable findings: only those with evidence (bloated build artifacts, signs of abandonment, etc.)

Output: `phase1_explorer-<project>_status.md`

### Phase 2 — Integration (**execution mode:** integrator solo)

> **Corporate Claude/Codex host**: the host integrates Pi collection reports; do not issue a native integrator.

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
