---
name: orchestrate
description: "Gate and orchestrate agent work. Phase 0 judges whether a request needs direct handling, one subagent, a generate-verify pair, or a team - then runs session teams (task queue depends_on, P2P, hybrid phases, severity-gated integration). Use for ANY implementation or multi-step task (작업해줘, 구현해줘, 만들어줘, 수정해줘, 고쳐줘, 기능 추가, 리팩토링, implement, build, fix, refactor, debug - troubleshooter runs AFTER this gate), build continuation (진행해줘, 계속), and 팀 구성, 병렬 작업, cross-project work. Precedes external implement/debug/QA skills (sc:implement, investigate, qa) - auxiliary tools inside phases only. Do NOT use for review/audit (→ team-review), doc/spec writing (→ doc-writer), harness work (→ metaskill), or deploys (→ release). Re-run keywords - orchestrate, team, parallel, implement, 오케스트레이션, 구현, 작업, 병렬."
---

# orchestrate — Agent Team Orchestration

## Why this skill

Handling work that spans multiple projects and multiple perspectives in a single context explodes the context and drops verification. This skill decomposes work into a team, but **never defines the team permanently in files**. A team is a **session object** — created in memory at start and released at the end. Reason: team composition must change every time to fit the shape of the work, and a persisted team forces a structure that does not fit the next task.

This skill is not for team work only — it is **the gate for all implementation and multi-step requests** (ADR 010). Reason: the structure "only work that needs a team calls this skill" had no judging authority, so the bypass of handling complex work in a single context without judgment kept recurring. As a gate, every task passes the scale judgment — and if the verdict is "handle directly", the overhead is a single table read.

## Standard team roster (reuse first)

When composing a team, **reuse the standard agents in `.agents/agents/` first**. Defining members ad hoc every time makes each member's rules subtly different, making execution unpredictable.

| Agent | Tier | Role | Typical placement |
|---|---|---|---|
| explorer | explore | Collection, search, summarization (no source edits; Write only for `_workspace/` reports) | Upstream — parallel collection, fan-out |
| architect | design | Spec drafts, task decomposition (depends_on), interface design (no implementation) | Upstream — leads skeleton Phase ② |
| troubleshooter | design | Root-cause investigation — reproduce→hypothesize→verify→confirmed cause (no fixes) | Upstream — replaces explorer on bug/incident work |
| implementer | implement | Implements code, docs, config (holds Edit — implementation family) | Midstream — pipeline implementation, generator in generate-verify |
| infra-specialist | implement (design when placed in review mode — team-review infra specialization rule) | Writes k8s/AWS manifests and IaC, infra diagnosis and deploy planning (holds Edit; mutating commands require user confirmation) | Midstream — infra segment of cross-deploy pipelines |
| reviewer | design | Verification and verdicts (no fixes) | Downstream — verifier in generate-verify, independent verification |
| integrator | design | Fan-in, integration gate, final report | Farthest downstream — endpoint of all deliverables |

Only when a domain-specific member is needed (e.g., payments domain expert, DB migration expert), define one ad hoc per root AGENTS.md §10 (the 10 agent-definition rules), and if the same role repeats 3+ times, propose promotion to `.agents/agents/` (evolution trigger — the same path by which the k8s expert was promoted to infra-specialist, ADR 011).

**Applying tiers is the orchestrator's job (declaration alone does not apply them)**: `tier` in frontmatter is a harness-only field the CLI does not interpret. When creating team members (Agent calls), **explicitly set the `model` parameter per the root AGENTS.md §9 table** — the design tier gets the current CLI's highest-performing model; implement and explore get the standard model. Without it, members inherit the session model as-is and the tier policy (especially "verification uses top performance, no lightweight models") is silently ignored.

## Phase 0 — Gate (always first)

### 0-1. Team necessity judgment (first decision for every request)

| Verdict | Signals | Execution |
|---|---|---|
| **Handle directly** | Questions/lookups/explanations; trivial edits of ≤2 files (behavior-preserving — **infrastructure manifests excluded**; infra-specialist routing per root §7 item 5 takes precedence); interactive iterative work | Report the verdict in one line and exit the skill — the session does the work itself (team overhead > value) |
| **Single subagent** | Single project, single perspective, but context isolation pays off (bulk file exploration, collection, summarization) | 1 member from the standard roster (mode B) |
| **Generate-verify pair (minimum implementation unit)** | Feature addition/behavior change (§13 scope) but a multi-perspective team is unnecessary — **if risk is high (§3 — infra/security), it is a team verdict regardless of file count (row below), not a pair** | **3+ files: 1 implementer + 1 reviewer — the main loop does not implement directly.** ≤2 files: direct implementation by the orchestrator is allowed + independent reviewer mandatory (lightweight review protocol — the ban on self-verification is invariant). Risk has only 2 levels (low/high), so the boundary inside the pair is file count. See "Verification-mandatory rule" and "Implementation-owner rule" below |
| **Team** | Multiple projects / multiple perspectives (3+) / 6+ changed files / §3 guardrail risk (infra/security) | Pattern selection (`../metaskill/references/patterns.md`) → team composition |

- **When in doubt, start on the lighter side** and promote when the transition-signal table in patterns.md points to it (same philosophy as team-review Phase 0 — start solo on a fuzzy boundary, promote when scope-exceeded is reported). Reason: over-judging slows every task down and causes the gate itself to be bypassed.
- **This table is the single source for the scale threshold (6+ changed files)** — team-promotion thresholds in other skills (team-review etc.) reference this value (if they diverge, the same work gets different scale verdicts depending on the skill).
- **Report the verdict and its rationale to the user in one line** and proceed. A silent verdict is indistinguishable from a harness bypass.
- **Continuations also re-take the gate**: even for continuation requests like "진행해줘" / "계속" (continuing an in-progress implementation or infra step — resuming a registered cross-session task via "이어서" belongs to work-tracker), if the target work involves new implementation, behavior change, or infra manifest change, do not skip the 0-1 judgment — fast-tracking a continuation on the grounds that "a judgment already happened" neutralizes the gate. In particular, k8s/infra manifest changes are judged with infra-specialist placement even on continuation (real case: an infra-change continuation skipped the judgment and failed on unchecked admission constraints; root AGENTS.md §7 items 3·5). **Implementations handed over via work-tracker "이어서" or carryover resume are treated the same** — the resume skill only hands over the re-entry point; the implementation itself is re-judged by this gate. **The transition point where a flow that started as read-only diagnosis (log checks, kubectl, cause investigation) naturally slides into code modification is also subject to re-judgment — even without an explicit "구현해줘" from the user, the moment the first Edit/Write touches product code is the trigger** (real cases 2026-07-21/22: the diagnose→fix transition bypass happened twice in one session and recurred even after user callout and self-correction — wording alone could not catch it, so the gate-reminder hook mechanically reminds once per session, ADR 028).
- **Implementation-owner rule (sub-project product code)**: in the pair verdict above, do not substitute issuing an implementer with "context handoff is expensive, so doing it myself is cheaper" — that justification is itself a bypass signal (measured 2026-07-21: repeated main-loop direct-implementation pattern in sub-project and resumed sessions). **Only ≤2 files (and low risk — it is a pair verdict, and high risk is a team verdict from the start) makes direct implementation the official path**, and even then independent reviewer verification cannot be skipped (the ban on self-verification is the essence of the §13 guarantee). If directly-implemented work grows to 3+ files, hand it to implementer at that point (transition signal). Risk grades are 2 levels only (low/high) — the single source is this table's team row and team-review Phase 0 ("§3 guardrail applicability, infra/security"); do not invent intermediate grades like "medium risk". Reason: main-loop direct implementation bloats the context with implementation detail and removes the entity watching overall progress (in accord with the Leader-role section).

### 0-2. Preconditions

1. **Input check**: if the work instruction is empty or ambiguous, stop immediately and report why.
2. **`_workspace/` detection**: if `_workspace/<task>/` already exists, check whether it is residue from a previous session — decide whether to resume or start fresh, and if starting fresh, change the task name so existing artifacts are not overwritten.
3. **Scope judgment**: if the scope is large (e.g., over 40 files), split it and handle only the high-risk batch in this run. Reason: trying to do everything at once wrecks quality and traceability simultaneously.
4. **Registry routing**: identify the relevant projects from the project registry in root REGISTRY.md and load each harness. If REGISTRY.md is missing, installation is incomplete — stop and point to harness-install.
5. **clarify-first (design/architecture-level requests only — root AGENTS.md §13 item 0)**: if the verdict is **team** and an architect is placed, the architect performs that procedure. But when the verdict is **handle directly / generate-verify pair** — so no architect is involved — and the target is design/architecture-level (module boundaries, technology choices, refactoring direction, etc.), the orchestrator runs clarify-first itself before starting: enumerate implicit assumptions and missing constraints, ask only the questions whose answers change the approach (respecting the no-question-spam guard), declare the rest as assumptions, then proceed. Reason: locking in an approach and appending questions afterward incurs the loss of precisely solving the wrong problem (an entry-path gap — architect already embeds this procedure, but the direct and generate-verify paths had no owner).

## Primitives

| Primitive | Role |
|---|---|
| **TeamCreate** | Creates team metadata. Each member is created individually by calling the Agent tool with team_name. Make member boundaries (role scope) explicit. |
| **TaskCreate** | Shared task queue. Manages `depends_on`, owner, and status as the single source. |
| **SendMessage** | P2P without going through the leader. Fields: `to`, `summary`, `message`. |

> **Environment fallback**: if TeamCreate/TeamDelete are unavailable in the current environment, substitute mode B (subagent mode) and record that fact in team-log.jsonl.

## Channel selection criteria

- Small, immediately usable info → **SendMessage**
- Work with an owner and a status → **TaskCreate / TaskUpdate**
- Large artifacts, phase-to-phase handoff → **`_workspace/` files** (`phase{N}_{agent}_{content}.md`)

## depends_on is the core

Dependent tasks must be declared with `depends_on`. The resulting **dependency graph determines the team's coordination structure** — a linear graph is a pipeline, a fan shape is fan-out. Express the coordination structure as the graph, not in prose.

### Team size guide

| Size | Tasks | Members | Tasks per member |
|---|---|---|---|
| Small | 5–10 | 2–3 | 3–5 |
| Medium | 10–20 | 3–5 | 4–6 |
| Large | 20+ | 5–7 | 4–5 |

For the supervisor pattern, 3–5 workers is optimal. Hierarchical delegation **must not exceed 2 levels of depth** — latency grows exponentially. The generate-verify retry default is 2–3; on hitting the limit, ask a human for judgment.

## The leader's (orchestrator's) role

The leader **does not fix code directly.** Reason: the moment the leader touches hands-on work, no one is left watching overall progress.

1. Compose the team → 2. Place the task queue → 3. During execution, allow direct member-to-member communication and intervene only for idle notifications and errors → 4. Integrate results → 5. Disband the team + session clean.

Error-intervention criterion: **if 2 or more members fail, do not continue with partial results — disband the team and report to the user** (the shared default of agent error handling — in accord with agent-rules.md §5). Reason: the integrated output of a half-collapsed team looks complete but is not.

## Common member rules (inserted into every member prompt in agent-team mode)

> In mode B (subagent mode), apply ①·③·⑤·⑥·⑦·⑧ (for ⑥, exclude only the SendMessage part — it still applies to issuing prompts, reports, and return text), and report Critical findings to the orchestrator in the final response.

1. **Read the target project's harness before working** — `.agents/projects/<name>/AGENTS.md`. Team members and subagents do not inherit the sub-project's hooks/settings, so reading the document is the only path to receive that project's rules (root AGENTS.md §12).
2. On any finding, notify the relevant members immediately via SendMessage.
3. Save final judgments to files.
4. **On a Critical finding**, report to the orchestrator and the relevant members simultaneously. Continue the remaining work, but keep the final verdict in a blocking state (must-fix included).
5. Do not modify outside your role scope (e.g., reviewers must not modify code).
6. **Internal communication is in English** (root AGENTS.md §15) — issuing prompts, `_workspace/` interim reports, SendMessage claim/request bodies, and **the final text returned to the orchestrator** (§15's 4th channel). Exceptions: the integrator's final report and deploy runbooks are in Korean (documents the user reads directly — when file = return value, the return is Korean too); code/log quotes stay in the original language. Reason: Korean costs ~1.5–2x tokens for the same content, and interim reports are re-read many times.
7. **Do not use git commands that mutate repository state (working tree, index, HEAD) for inspection or comparison purposes** — `git stash`, `checkout/restore`, `reset`, `clean` are forbidden; compare with `git diff <ref>..<ref>` and `git show <commit>:<path>`; diagnostics needing HEAD movement (bisect) run in an isolated `git worktree add` copy (single source: agent-rules ⑨ supplementary rule — parallel uncommitted changes can coexist in the shared tree).
8. **Read narrowly**: narrow candidates with Grep/Glob, then Read only the needed line ranges — whole-file Reads only when whole-file understanding is the goal. Reason: whole-file loading is the largest consumer of member context input tokens (input-reduction review 2026-07-22 — an ingestion axis separate from the artifact layer §15/§4).

Fixed message format (JSON): `{type, severity, file, line, claim, request}` — carries both the finding and the action the recipient must take.

## Integration gate (owner: integrator)

Result integration is **owned by the integrator agent**; the single source of the 5 gate principles (severity-first ordering / duplicate merging / excluding evidence-free suggestions / demotion·promotion rules / must-fix·should-fix·watch 3 sections) is `.agents/agents/integrator.md` §2. Even when a leader integrates directly on a small team, the same principles apply.

## Verification-mandatory rule (generate-verify built in — under any verdict or pattern)

**Work that includes feature addition or behavior change includes a final independent reviewer verification phase regardless of the verdict grade** — under a generate-verify pair verdict, the pair's reviewer does it; under a team verdict, the verification phase does (spec-based review per §13 item 3 — the spec's completion criteria are the verdict criteria). Reason: an implementer's self-assessment passes its own bias — if verification is optional, it gets skipped first precisely on busy work. If the scale is large (same as the team threshold in the 0-1 verdict table — 6+ changed files) or the risk is high, promote the verification phase to team-review team mode (perspective fan-out).

**Pair-verification issuing follows the lightweight review protocol** (single source: the team-review "Solo mode" section — measured 2026-07-21: even at small scale a review takes minutes). It splits into two layers: ① **inline input (include the full diff, a spec completion-criteria excerpt, and the latest test output in the issuing prompt) and `run_in_background` issuing are the default for all pair verification** (removing re-collection round-trips pays at any scale; the reviewer keeps re-running relevant tests. **For diffs over 10KB, pass the file path instead of the full text** — single source: team-review Solo mode item 1). ② **Report-file omission (verdict via return text) applies only to ≤2 files** (file it when a must-fix is found). This rule trims fixed overhead, not verification — the verification mandate of this section itself is invariant.

## Team-run learning notes (3+ phase team runs only — oh-my-openagent adoption, proposal: 2026-07-19)

In **team runs of 3+ phases**, the orchestrator maintains `_workspace/<task>/learnings.md` (English — §15, read only by models): at each phase-integration point, append the **environment/codebase learnings** confirmed in that phase (build flags, reproduction traps, settled design decisions, blocked paths), and **include that content in the CONTEXT of later phases' issuing prompts**. Reason: today there is no path for a trap discovered by member A to reach member B's prompt, so the same rediscovery can repeat — this note is the learning feedback loop within a single team run.

- **Boundary**: do not create it for small runs (1–2 phases, solo collection) — discipline that becomes noise gets bypassed (root §4·§16). Learnings that outlive the session belong to auto-memory (record mistakes immediately, §8) and work-tracker, not this note — `learnings.md` is unpersisted along with `_workspace/`.

## The 3 execution-mode templates

### A. Agent team mode (default)

First choice for collaboration of 2+ members. TeamCreate → create members (explicit role boundaries for each) → queue via TaskCreate (with depends_on) → allow member-to-member SendMessage → integrate → disband.

### B. Subagent mode (alternative)

Use for **parallel collection** that needs no team communication. The orchestrator acts only as a result collector. **Include the output path and the instruction to read the target project's AGENTS.md in the prompt body** (e.g., "Before working, read `.agents/projects/<name>/AGENTS.md`, and save the result to `_workspace/<task>/phase1_<name>_report.md`"). Cap: 10–20.

**7-element issuing-prompt skeleton (format — oh-my-openagent adoption, proposal: 2026-07-19)**: write issuing prompts with the 7-element skeleton **TASK** (what) / **OUTCOME** (completion criteria, expected artifacts) / **SKILLS** (skills to use) / **TOOLS** (tools to use) / **MUST DO** (required) / **MUST NOT** (boundaries — §3 positive-form constraints first) / **CONTEXT** (output path, AGENTS.md to read, upstream artifacts). This is a **checklist, not fixed boilerplate** — omit elements that do not apply (no forcing 7 elements onto small issuings — root §16 minimalism). Reason: when what/why/boundaries vary from issuing to issuing, subagent output quality and rework rates wobble — the skeleton reduces that variance.

**Concurrent-issuing rule (the actual implementation of parallelism — violating it degenerates to serial)**: Agent calls for subagents with no mutual dependency **must all be issued in one response (same turn)**. Calling one, waiting for its result, then calling the next is serial, not parallel — for independent work it is pure wasted time. `run_in_background: true` is the default for **every** dispatch — even a single agent whose result the next step depends on: report what is running, end the turn, and resume the dependent step from the completion notification, so the session stays conversable for the user (user decision 2026-07-24); reserve foreground for short lookups (≲1 min) whose result must be inlined in the same response. The notification-resume pattern applies to **interactive sessions**; headless runs with no next turn (autoloop `claude -p` iterations) complete dependent dispatches synchronously instead of ending the turn. Even without background support, same-turn concurrent issuing alone runs them in parallel. Sequencing is justified only when a previous agent's result is needed in the prompt — that case is a pipeline, not mode B, so declare it with depends_on.

**Parallel-write isolation (mode-agnostic — team and subagent alike)**: when issuing **2 or more concurrent** agents that modify files in the same repository (implementer, infra-specialist), set `isolation: worktree` on each Agent call — isolate even when the target files differ, as long as it is the same repository (the index, build artifacts, and formatters touch the same tree). If worktrees are unsupported, split the work so file scopes do not overlap; if they overlap, serialize with depends_on. Reason: parallel collection (reads) has no conflicts, but parallel writes create merge conflicts and state contamination — sequential runs need no isolation (it would only cost). (loop-engineering 'Parallel Collision' failure-mode adoption, 2026-07-18)

### C. Hybrid mode (default form of a team verdict)

Mix modes and patterns per phase. **Mandatory convention: state the phase's execution mode at the top of each phase section** (e.g., `**Execution mode.** Agent team`). Without this declaration things tangle beyond debuggability — the phase boundary must state "here the team disbands and subagents start running" so data handoff and verification scope can be traced.

**Standard skeleton** — team-verdict work picks only what it needs from the 5 phases below but **keeps the order**, and if implementation is included the verification phase cannot be skipped (verification-mandatory rule above):

| Phase | Pattern | Mode | Skip condition |
|---|---|---|---|
| ① Collection | Fan-out/fan-in | Subagents (explorer — troubleshooter for bugs/incidents) | If context is already sufficient |
| ② Design/consensus | Fan-out + debate | Agent team (architect-led, cross-verification needed) | If there are no design disputes |
| ③ Implementation | Pipeline / supervisor | Team or implementer solo (infra segment goes to infra-specialist) | If the work has no implementation |
| ④ Independent verification | Generate-verify | Subagent (reviewer — isolation is the independence) | **Cannot be skipped when implementation is included** |
| ⑤ Integration | Fan-in | 1 integrator | If there is only one artifact |

Each phase's pattern is **judged independently** by that phase's problem shape — do not force one pattern on the whole work. For composition details follow "Composite patterns — hybrid composition rules" in `../metaskill/references/patterns.md`. Phase boundaries are connected via `_workspace/` files.

## team-log.jsonl event contract (fixed schema)

Append team events to `_workspace/<task>/team-log.jsonl` **immediately as they occur** — batch-writing at shutdown loses the log of interrupted sessions and makes harness-review's failure-signal observation impossible.

- Format: one JSON line; required fields `ts` (ISO8601) and `event`; the rest are per-event details.
- `event` values (fixed): `team_create` / `task_dispatch` / `task_complete` / `task_failed` / `integration_complete` / `shutdown_request` / `team_delete`. harness-review reads `task_failed` and the absence of `team_delete` as signals.

## Shutdown sequence (session clean — fixed order)

1. SendMessage `shutdown_request` to all members.
2. Confirm in-progress file writes have completed.
3. TeamDelete.
4. Record the `shutdown_request`·`team_delete` events in `_workspace/<task>/team-log.jsonl` (per the event contract above).
5. **If it was cross-project work, update the "연관 프로젝트" (related projects) column of the affected rows in REGISTRY.md** and leave one row in the change history (root AGENTS.md §1 — relations are filled only from observed real work). This work is the first observed evidence that the two projects were linked.

If TeamDelete fails, **do not hide it** — report the items needing manual cleanup. Reason: a silently swallowed zombie team contaminates the next session's `_workspace/` detection.

## Final response format (fixed)

Report only these 3 things to the user:
1. Count and locations of blocking/must-fix items
2. Count of should-fix items
3. Full report path (`_workspace/<task>/...`)

Write the report **digested into Korean** — even though member reports are in English (§15), do not quote or transliterate them, and right before sending confirm that all user-facing text is Korean (language-mixing guard).

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Invocation scope | Complex work handled in a single context without judgment | Every implementation/multi-step request passes the scale judgment (Phase 0-1) |
| Context | Everything loaded into one session → explosion, interruption | Distributed across members; the leader only integrates |
| Cross-project | Only 1 harness loaded, remaining rules dropped | Registry-based loading of all harnesses |
| Verification | Generator self-assesses its own output | Integration gate + evidence-free suggestions excluded |
| Shutdown | Leftover teams and artifacts abandoned | Fixed shutdown sequence + team-log records |
