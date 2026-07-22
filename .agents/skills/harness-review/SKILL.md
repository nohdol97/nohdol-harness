---
name: harness-review
description: Harness operations review in two modes - daily lite (scan the three expansion signals since the last check) and weekly full (adds the shrink/efficiency signal - unused skills, token-waste patterns - plus symlink/registry/frontmatter integrity), proposing concrete metaskill actions. Runs as a background subagent (the main loop dispatches, reports the summary, handles approval) and is auto-triggered by the SessionStart reminder hook via markers. Use when the reminder fires or the user says 일일 점검, 주간 점검, 하네스 리뷰, harness review. Do NOT use for creating/scaffolding or actually applying changes to the harness (→ metaskill), nor for an on-demand usage audit of one specific external tool/plugin (→ tool-audit) - harness-review only scans signals and proposes, it never edits the harness itself. Re-run keywords - harness-review, daily, weekly, evolve, 일일 점검, 주간 점검, 진화.
---

# harness-review — Harness Operations Review (two modes: daily lite · weekly full)

## Why this skill

Root AGENTS.md §8 requires observing the four evolution-trigger signals as an operating habit. If the observation procedure is not pinned down as a skill, that habit evaporates within weeks — the harness can only evolve when the places where it diverges from real use become visible. This skill handles **observation and proposal only**. Actual creation/improvement execution belongs to metaskill (separation of roles: if the observer also executes immediately, verification of the proposal's grounds gets skipped).

## Execution modes (designated by the reminder hook — two-tier cadence)

| Mode | Cadence | Scope | Completion marker |
|---|---|---|---|
| **Daily lite** | 1 day | Step 1 signal collection only — sessions since the last check. Integrity check skipped (weekly's job) | `.harness-review-daily-last` |
| **Weekly full** | 7 days | Steps 1–3 in full | `.harness-review-last` + daily, both |

Daily mode **ends with a one-line "no signals" report and marker update when there are no signals** — the daily cost must stay at a few minutes of scanning to be sustainable. If there are signals, it proceeds to step 3 (proposal generation) just like the weekly mode.

**Daily mode scope/cost ceiling**: Restrict data sources to **agentsview queries (sessions since the last marker), `git log`, and lightweight file checks (listing `_workspace/` task names, grepping team-log.jsonl for `task_failed`, directory-existence checks — for the filesystem items of signal-collection table ①–③, daily mode goes only this far)** — no full reads of harness files, no re-reading skill/agent bodies (structure/integrity is the weekly's job). Without agentsview installed, daily mode scans with git log + lightweight file checks only and states that fact in the report. Target cost is **within 30k tokens** for the subagent — the measured case of a no-signal report consuming 112k tokens (2026-07-17, applying the spirit of signal ④ — prescribed immediately rather than waiting for the repetition threshold because a daily recurrence is a structurally guaranteed cost) is the basis for this ceiling. The root §8 "record mistakes immediately" discipline covers first-occurrence lessons, so the daily scan focuses only on detecting **repetition** signals.

## Execution method (subagent delegation — main loop must not perform the review directly)

If the main loop performs the review directly, the first response is occupied by the review and the user's request is delayed, and the main context gets polluted with review details (file lists, intermediate judgments) (2026-07-14 user-confirmed). Observation can be delegated, but approval requires conversation — the boundary sits here.

1. When the review instruction arrives (reminder trigger or direct user request, same handling), the main loop **dispatches one explorer subagent in the background** and handles the user's request in parallel. The subagent prompt must include: ① read `.agents/skills/harness-review/SKILL.md` and perform steps 1–3 of the designated mode (full/daily), but **proposals only up to drafts** (no creation/modification execution — for daily mode, state the "scope/cost ceiling" above verbatim in the prompt) ② save outputs to `_workspace/harness-review-<YYYY-MM-DD>/` ③ also perform the step-4 marker/ops-log updates ④ the final return is a summary in the output format (signals, integrity, proposal drafts, marker-update status). **Language (root §15)**: write the dispatch prompt, review notes, and final return summary in English, but state in the prompt that **proposals, the ops log, and pending-queue entries are written in Korean** (documents the user reads and approves).
2. When the subagent completes, the main loop **digests the summary into Korean** and reports it in chat (no quoting/literal translation of the English return — §15 language-mixing guard) and confirms the marker/ops-log updates (updating directly if missed).
3. **Proposal approval and execution (metaskill invocation, or pending-queue recording under a corporate profile) belong to the main loop** — the subagent goes only as far as observation and drafts. The no-unauthorized-creation rule survives delegation.

## Procedure

### 1. Signal collection (the four evolution-trigger signals — daily mode covers ①–③ only)

| Signal | Observation method |
|---|---|
| ① Repeated requests, 3+ | Check for repetition of the same type of work in recent session memory, `_workspace/` task names, and git commit messages |
| ② Repeated failures, 2+ (incl. same correction 2+) | Check `task_failed` events in team-log.jsonl (orchestrate event contract), rework commits of the same kind (fix chains), and **repeated user corrections with the same content** ("아니 그게 아니라"-type — measured via agentsview session search) |
| ③ Harness bypass | **Implementation/multi-step work handled without the team-necessity judgment (orchestrate Phase 0-1)** (absence of the one-line judgment report is the evidence — root AGENTS.md §7 item 3), multi-project work handled without orchestrate, agent/skill definitions created outside `.agents/`, project directories absent from the registry, **harness skill triggers routed away to built-in/plugin/sc:* external skills** (CLAUDE.md skill-priority violation — e.g. PR creation via gstack ship, work resumption via checkpoint) |
| ④ Shrink/efficiency (weekly full only) | **3+ weeks uninvoked**: search each skill/agent name with `agentsview session search` to check recent invocation history — if uninvoked for 3+ weeks, propose retirement/consolidation (if agentsview is not installed, withhold judgment — no retirement proposals without evidence). **Token-overconsumption pattern 2+**: check top token/cost sessions via `agentsview stats`, and confirm via session logs whether team formation for simple tasks, repeated collection of the same information, or unnecessary full-file loading recurred → propose procedure improvements (downgrade the judgment, reuse artifacts, split into references/) |

**agentsview integration (primary data source for signal collection when installed)**: If `agentsview` is installed, measure instead of relying on session memory — use `agentsview session search "<request-type keyword>"` for repeated requests/corrections, and `agentsview stats`·`agentsview session list` for rework/failure patterns and token/cost. All Claude Code and Codex sessions are indexed, so it is more accurate than memory or commit messages and has no blind spots between CLIs. If not installed, use the observation methods in the table above as-is, but withhold judgment on ④ (installation is harness-install step 3).

### 2. Structural integrity check

**Machine judgment first (integrity-check.py)**: Among the items below, symlinks (R1), `.claude/` real-file intrusion (R2), skill/agent frontmatter (R3·R4), MOC consistency (R5), CLAUDE.md first line (R6), and required gitignore entries (R7) are **judged deterministically by `python3 .agents/hooks/integrity-check.py`** (spec: docs/specs/2026-07-19-integrity-check-script.md). **Run it first** and digest its PASS/FAIL/SKIP into the report — do not re-read harness files (weekly-review token savings + determinism). Installation sites where symlinks are impossible show R1·R2 as SKIP. Only the **semantic-judgment items** the script does not cover (git hook registration, `_common.py`, Codex hook symmetry, sub-harness consistency, AGENTS.md size budget, registry, leftovers) are checked directly via the procedure below. The individual bullets below are the detailed judgment criteria for script-missing/fallback situations.

- Symlinks: whether `readlink .claude/agents .claude/skills` points to `../.agents/*`. **Whether non-symlink real files have appeared under `.claude/`** (if so, a bypass signal — originals must exist only in `.agents/`). → integrity-check.py R1·R2 judge this mechanically (gitignored runtime artifacts excluded).
- git hook layer: whether `git config --global --get core.hooksPath` points to this harness's `.agents/githooks` — it is the **sole enforcement layer** of tdd-gate (§13), so an unregistered machine has the gate switched off entirely (occurs when someone only pulled and never ran harness-install step 1 — ADR 015). If unregistered, propose the registration command.
- Hook common module: whether `.agents/hooks/_common.py` exists — it is the single source of the stdio UTF-8 reconfiguration for the three hooks (spec 2026-07-15-hooks-common-bootstrap), so if lost, each hook silently passes via no-op fallback and the cp949 protection disappears (fail-open, so not even an error is raised). If absent, propose recovery.
- Codex hook registration consistency: whether the two SessionStart reminders in `.claude/settings.json` (`harness-review-reminder`·`worklog-reminder`) are also registered in `.codex/hooks.json` — if added to only one side, reminders go missing in Codex sessions (ADR 019 presumes symmetric registration in both files). Also confirm `[features] codex_hooks = true` exists in `.codex/config.toml`.
- Document map (MOC) freshness: whether the ADR/spec/proposal rows of `docs/README.md` match the actual files in `docs/adr/`·`docs/specs/`·`docs/proposals/` — report files missing from the index, index rows without files, or superseded entries still marked "active" (a violation of the root AGENTS.md §6 sync obligation = the documentation version of declared-but-unimplemented).
- Sub-harnesses: whether the `.agents/projects/` subdirectory list matches the REGISTRY.md registry rows (harness-presence ✓). Whether harness files (AGENTS.md·CLAUDE.md·`.claude/`·`.agents/`) have appeared inside `project/<name>/` (if so, a bypass signal — originals must exist only in root `.agents/projects/`; root AGENTS.md §12, ADR 006·007). A CLAUDE.md in a sub-project is an old-spec leftover — propose deletion. If lazily-created `skills/`·`agents/` exist but the sub AGENTS.md has no list/path notation, that is an unloadable state — report it.
- Skill loadability: whether each SKILL.md's frontmatter starts with `---` on line 1 and has a `description` (a description-less skill cannot auto-trigger — the 2026-07-13 outage), and whether line endings are LF (the `file` command must show no CRLF marker).
- **AGENTS.md loading size budget**: if `wc -c AGENTS.md` **exceeds 40,000 bytes, propose a diet** — this file is always-on every session via `@AGENTS.md`, so growth is a fixed token cost, and the longer it gets the more rules drown in the body. Diet technique: keep rule+reason, move case studies/measurement narratives out to changelog/ADR pointers (same technique as the ADR 021 change-history split).
- Registry: whether REGISTRY.md exists (if not, installation incomplete — guide to harness-install); if it exists, whether the table matches the actual directory list under `project/`.
- Leftovers: in `_workspace/`, a task directory **with** a team-log.jsonl but no `team_delete` event is an abnormal-termination signal. A team task directory with no team-log at all is an event-contract bypass signal (informational).
- **`_workspace/` housekeeping**: list task directories whose last modification is **14+ days old** as deletion candidates and propose them (e.g. `find _workspace -mindepth 1 -maxdepth 1 -type d -mtime +14` — directory mtime is approximate, so candidates are advisory; final judgment is user confirmation). Exclude the three operational-data exceptions (`harness-updates.md`·`harness-ops-log.md`·`.harness-review-*` markers — root AGENTS.md §4), and **execute deletion only after user confirmation, as it is §3 destructive work**. Reason: the §4 "not preserved" principle had no enforcement device, so session artifacts were accumulating indefinitely (2026-07-18 observation — 5+ audit directories lingering).
- Pending queue: whether `_workspace/harness-updates.md` has items with status `대기` (pending) (root AGENTS.md §5 installation profile). On a **personal** site, that means carried-over improvements are sleeping — propose metaskill application. On a **corporate** site, that is normal (awaiting carry-over to the personal machine) — report only the item count.
- Change history: whether recent harness commits were each accompanied by a change-history update — **for the root, `git log -p -- docs/harness-changelog.md`** (split per ADR 021); for sub-projects, the table at the bottom of the relevant AGENTS.md. Also confirm the CLAUDE.md first-line `@AGENTS.md` import exists (ADR 021 — regressing to a prose link means the single source is no longer always-on).
- Secret leakage (if agentsview installed): scan whether secrets leaked into session logs with `agentsview secrets scan` — the §3 guardrail ("never record") is the preventive rule and this is the post-hoc verification. On detection, report to the user immediately as must-fix.
- Declared-but-unimplemented: list rules that are declared but have no enforcement device (hook, test, procedure step, definitive wording) — unapplied tier→model mapping, "parallel execution" declared but run sequentially, and silent hooks were all of this type. Usage signals (step 1) cannot catch these, so the structural inspection does.
- Loading bloat (the harness's own contribution to token waste): check for SKILL.md bodies exceeding 500 lines (violating metaskill common rule 3) and bloat of the always-loaded CLAUDE.md/descriptions — these are fixed per-session token costs, so propose splitting the excess into `references/` or compressing.

### 3. Proposal generation

- If signals are detected: organize which signal, on what evidence, leads to which agent/skill creation/improvement, in the form of a **metaskill invocation proposal**, and report to the user. Never create without approval.
- **Installation-profile branch (check the REGISTRY.md profile before finalizing proposals — root AGENTS.md §5)**: On a **corporate** site, do not propose repository modifications — on user approval, record the proposal content in `_workspace/harness-updates.md` as a `대기` (pending) item (§5 format: target file, change content, and reason, at a level applicable on the personal machine without extra context). On a **personal** site, propose metaskill execution as usual.
- If there are no signals: report "신호 없음 — 현재 구조 유지" (no signals — keep current structure) and stop. **Do not invent improvements in the absence of signals** — evolution proposals are legitimate only when grounded in the §8 signals.

### 4. Completion marker & ops log update (must not be skipped — the updater is whoever performed the review; the subagent when delegated)

- **Markers**: record one line with today's date (`YYYY-MM-DD`, **KST**) — **daily mode**: `_workspace/.harness-review-daily-last`; **weekly full mode**: both `.harness-review-last` and `.harness-review-daily-last`. The SessionStart reminder hook (`harness-review-reminder.py`) uses these markers to judge 1-day/7-day elapse and auto-trigger the next review (elapse judgment is also KST — read and write timezones are kept aligned). If the markers are not updated, the reminder repeats every session.
- **Ops log**: append a one-line review result to `_workspace/harness-ops-log.md` — format: `- YYYY-MM-DD [전체 점검|일일 점검] 신호 N건(요약) / 무결성 통과|문제 N건 / 제안 N건(요약)` (Korean — this log is user-read). This log is the single out-of-chat record of "what the last review saw and what was improved" (improvement executions are appended by metaskill as `[개선]` items). Since the reminder hook stays silent before the due date (noise removal, 2026-07-16), past history is checked directly through this log.

## Output format

1. Detection status and evidence for each signal (daily: ①–③, weekly: ①–④)
2. Structural integrity check result (pass/problems)
3. metaskill proposal list (or "none")
4. Completion marker update confirmation

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Evolution triggers | Only a "observe weekly" declaration, no procedure → never executed | Reproducible review via fixed procedure |
| Bypass detection | Direct `.claude/` creation and registry mismatches silently accumulate | Surfaced by the integrity check |
| Over-engineering | The reviewer improvises improvement ideas every time | Ends with a "keep" report when there are no signals |
