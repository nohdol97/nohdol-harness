---
name: tool-audit
description: "Audit an installed external plugin/MCP/skill pack/framework using AgentsView usage, fixed token cost, overlap, and rollback evidence. Use for 도구 감사, 사용 실측, 플러그인 정리. Not for harness-native usage or periodic scans (harness-review), candidates (tool-eval), or applying removals (metaskill). Re-run: tool-audit, usage audit, plugin audit, 도구 감사, 사용 실측."
---

# tool-audit — Measured Usage Audit for External Tools

## Why This Skill

External tools (plugins, MCP servers, skill packs, frameworks) are installed once but cost something every session — always-loaded descriptions, tool schemas, and imports occupy context, and when their triggers overlap with harness skills they contaminate routing. This audit procedure was formalized after observing the same request type 3+ times (2026-07-18, signal ①): the SuperClaude removal (measured 0 uses across all 51,331 messages, ~36k tokens per session), and the gstack/MCP/plugin audits were each reinventing the procedure per session. **Principle: measurement, not gut feeling, renders the verdict** — "we'll probably use it" is not grounds for keeping.

## Procedure

1. **Fix the target and its cost surface**: confirm the tool name, install location (global `~/.claude/`·`~/.agents/` / project), and load mechanism. **Whether it is always-loaded is the key** — only things carried into context every session (skill descriptions, MCP tool schemas, CLAUDE.md imports) have a fixed cost; explicit-invocation-only tools have near-zero idle cost (in that case, tell the user the audit itself has little payoff).
2. **Measure actual usage (agentsview)**: search all recorded sessions for usage traces. Design search terms in 3 families — ① the tool's command/trigger phrases (`/sc:`, `gstack`, etc.) ② tool invocation names (the `mcp__<server>__` prefix) ③ artifact paths/markers the tool produces. Tally: matched message count, the search denominator (total message count — a measurement without a denominator is not evidence), and the most recent use date. **Zero hits may mean "the search terms did not catch the triggers", so derive search terms back from the tool's own docs and cross-check at least twice** (false-negative defense).
3. **Measure the fixed cost**: estimate the token size of the always-loaded portion (if it is a file-size-based approximation, state that it is an approximation). Cost per session × session frequency is the cost of keeping it.
4. **Judge overlap**: check whether harness skills/agents with the same triggers/features exist (root AGENTS.md §7 item 7 — on overlap the harness takes precedence, so the external tool is effectively a dead path).
5. **Verdict and proposal**: build the proposal from the criteria table below with the measured figures attached. The verdict stops at the proposal — **execution (removal, config changes) happens only after user approval**, and via metaskill when harness assets are involved.

| Measured result | Proposal |
|---|---|
| 0 uses + always-on cost present | Remove (after backup) |
| Low use + feature overlap with harness | Integrate into harness then remove, or adjust trigger boundaries |
| Real use + no overlap | Keep (tidy boundaries with negative triggers if needed) |
| Unmeasurable (no records / search impossible) | Honestly report the verdict as deferred — do not remove on guesswork |

6. **State the backup/recovery path**: a removal proposal must include the recovery method (config backup location, reinstall command) — the SuperClaude precedent (removal after backup; recovery procedure in session records). After executing a removal, log one line to `_workspace/harness-ops-log.md`.

## Deliverables

- If findings are numerous, write to `_workspace/tool-audit-<tool>/report.md` (English — root §15, two-tier progressive disclosure) and deliver the user report digested into Korean. A short audit is fine as a chat report (forcing a report file is noise).

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Procedural consistency | Search terms and verdict criteria reinvented per session | Fixed 3-family search terms and criteria table |
| Verdict evidence | "We don't seem to use it" impression-based verdicts | Measured match count / denominator / last-use date |
| Safety | No recovery path after removal | Backup/recovery path required and stated |
