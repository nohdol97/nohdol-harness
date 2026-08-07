---
name: team-review
description: "Review diffs, PRs, specs, or harness changes against spec criteria using one reviewer for small scope or perspective fan-out plus integration for large/high-risk scope. Use for review, security audit, 리뷰·검토·검증. Not for built-in/plugin review tools; harness team-review owns the verdict. Re-run: team-review, review, code review, 리뷰, 코드 리뷰, 검토, 검증."
---

# team-review — Size-Scaled Team Review

## Why this skill

A single reviewer sees only the defects of their own perspective — the eye watching correctness misses secret leaks, and the eye watching style misses test gaps. This skill **decomposes review into independent perspectives run in parallel, then filters them through an integration gate** so that no one person's blind spot survives into the final verdict. But a team is not free — **spinning up a team for a small diff is waste**, so the mode is chosen by size.

## Verdict criteria (fixed)

- **Judge against the spec**: if the target work has a spec (`docs/specs/`), its **completion criteria are the verdict criteria** (root AGENTS.md section 13). If there is no spec, record that fact itself as a finding (a section 13 violation — unless the change is trivial).
- **Findings without evidence are excluded**: every finding carries a location (file:line) and grounds — follow the integrator's 5 gate principles (`.agents/agents/integrator.md` section 2).
- Reviewers do not fix (reviewer agent principle). Fixes go to a separate implementation step.

## Phase 0 — Scoping and mode selection

Count the target's (diff·PR·spec document·harness change) changed files and risk level (whether guardrail section 3 applies; infra·security related), then:

| Mode | Criteria | Composition |
|---|---|---|
| **Solo** | Changed files ≤5, low risk | 1 reviewer agent (team overhead > value) |
| **Team** | Changed files 6+ or high risk (infra·security·cross-project) — threshold single source: orchestrate Phase 0-1 verdict table | Perspective fan-out below + integrator |

If the boundary is ambiguous, start solo; if the solo reviewer reports "scope exceeded", promote to team.

**Install-site gate (before mode selection — `사내` profile only)**: where REGISTRY.md's 「설치처 프로필」 records `사내`, **subagent dispatch is off entirely and there is no override marker** (ADR 042 widening ADR 038 — contract single source: orchestrate's Install-site exemption). Neither branch below dispatches; what differs is who owns the result:

- **Routed here automatically** — from orchestrate's verification phase, a branch-workflow finish, or any other skill's review step: hand the target back to the caller in one line, saying the profile blocked dispatch. The caller's own exemption clause defines the self-verification and the record that replace this skill.
- **The user asked for a review** (in their own words, this session): **the review still happens — the main loop performs it inline**, against the fixed verdict criteria below and, where scope is large, walking the perspective axes one at a time in sequence instead of in parallel. Report it as a review with the verdict, findings, and evidence, and add one line saying it ran **without fan-out and without an independent reviewer** — a review the author performed on their own work is not the same artifact, and the reader has to be able to tell. ADR 038's `[review-ok]` no longer buys a dispatch; asking no longer changes what runs, only that it runs at all.

Neither branch touches the perspective axes or the integration criteria below — this gate decides whether reviewers are dispatched at all, not how they judge.

**Diagram obligation (both modes — this is not a perspective, it is a check that runs whenever the target includes a spec)**: the `diagram` skill's thresholds decide whether one is owed, and **the checker cannot see a missing diagram** — it only validates one that is present (ADR 039). Catch it in both directions: a design/boundary section meeting a threshold with no diagram, and a diagram added where no threshold was met. Judge against the thresholds, not taste; on a borderline section apply the deciding test (must the reader hold 2+ relationships at once?) and say which way you read it. **It sits here, above the mode fork, because Solo is the path small diffs and generate-verify pairs actually take** — placed under Team mode it would miss most reviews. **The other two governed types are held elsewhere and not here**: a PR body is authored at branch-workflow finish 4, after the review window, and an issue is created at registration before any review exists, so those two are held by their own authoring steps (ADR 039).

**Agent-call budget**: record the expected reviewer count after choosing applicable perspectives. Preserve correctness/tests and any security·infra perspective required by the target, then omit non-applicable axes. Rework uses the **same reviewer thread** for **delta re-verification** with only the new diff, latest tests, and changed completion criteria. Add another reviewer only for a **new independent risk axis**, an unavailable prior thread, or author/verifier independence. Do not respawn the same perspective merely to obtain a fresh context.

## Team mode — perspective fan-out (delegated to orchestrate)

Team mechanics (creation·queue·team-log·termination) use **orchestrate's mode B (subagents)** as-is — this is independent parallel collection where inter-reviewer communication is unnecessary. What this skill defines is only the perspective axes and the integration criteria.

**Perspective axes** (select only those that fit the target, 3–5 — reuse the reviewer agent with per-perspective prompts):

| Perspective | What it looks at |
|---|---|
| Correctness | Logic defects, edge cases, implementation gaps against spec requirements (R numbers) |
| Tests | Do all spec completion criteria (C numbers) exist as tests; failure-case coverage (section 13 TDD) |
| Security | Plaintext secrets, input validation, permissions — guardrail section 3 violations |
| Convention | Compliance with harness rules·commit conventions·document formats (doc-writer templates) |
| Performance | Obvious inefficiencies (N+1, needless loops) — no speculative optimization proposals |
| Simplicity/over-engineering | **Selected only for non-trivial logic diffs** — looks only at what can be deleted (separate from correctness·security·performance). 5 tags: `stdlib` (reimplementing the standard library), `native` (duplicating platform·dependency features), `yagni` (single-implementation abstractions·unused config), `delete` (dead code·speculative features), `shrink` (can be shorter). Findings use the format `L<line>: <tag> <what>. <replacement>.`, and the report ends with `net: -<N> lines possible` (or `Lean already` if none). The verdict criterion is root AGENTS.md section 16 code minimalism — but the section 16 exception areas (validation·error handling·security·explicitly requested features) are not deletion targets. **This axis also checks that changed lines trace back to the request** (section 16 surgical change): adjacent-code improvements·refactors·style cleanups unrelated to the request are flagged as out of scope (untagged, format `L<line>: out-of-scope <what>`) — the only legitimate cleanup is orphan code created by one's own change. Reason: untraceable changes silently widen the diff-review scope and dilute verification density (karpathy-guidelines port, proposal: 2026-07-22) |
| UX·accessibility | Selected only for UI-change diffs — accessibility (WCAG conformance, touch target size, keyboard navigation, ARIA), user safety mechanisms (autosave·undo·error recovery UX). Criteria come from the target project harness and the user's global policy accessibility requirements |

**Infra domain specialization (mandatory when the target includes k8s·AWS·manifests·IaC)**: if the perspective axes above answer "what defects to look at", this rule answers "who looks at the infra perspective". A generic reviewer can read a manifest but cannot see **operational knowledge** like namespace resource caps and admission (failure evidence: the k8s manifest review gap — a value unchecked against caps blows up not at apply but at pod·PVC creation time as FailedCreate). So, **symmetric to `infra-specialist` being the only domain specialization on the build side, the review side specializes only in infra** — web·app·backend are sufficiently covered by the perspective fan-out plus the target project's AGENTS.md, and creating domain reviewers would violate root section 16 minimalism (multiplied against the perspective axes, agents explode).
- **Placement**: when the target includes infra changes (Phase 0 already promoted to team mode via high risk), **the infra-relevant portion of the correctness·security perspectives is handled by `infra-specialist` in review mode** — same as per-perspective reviewer reuse, except this perspective is invoked with `agentType=infra-specialist`. **Review-mode contract**: read-only — **Edit forbidden** (placed as a verifier, not a producer, so the reviewer principle applies), **invoked at design tier** (verification uses the top-performance tier — same as the model-designation rule in the reviewer-prompt section below, root section 9 false-negative defense). Out-of-domain perspectives (convention·simplicity·tests etc.) remain with generic reviewers.
- **Independence exception**: in an orchestrate build pipeline, **if infra-specialist itself authored the manifest**, this placement would be self-verification, so do not use it — a generic reviewer verifies with the infra checklist below (produce-verify independence, reviewer section 1). External diff·PR review (team-review's standard entry) is always eligible since the reviewer is not the author.
- **Infra review checklist** (included in that perspective's prompt): ① are container `resources.limits/requests`·PVC `storage`·PVC count within the namespace LimitRange·ResourceQuota·StorageClass caps (admission pre-flight — infra-specialist section 2) ② do the rollout strategy·PodDisruptionBudget·probes (readiness/liveness) guarantee zero downtime ③ are secrets referenced via secretRef·external secrets rather than plaintext in manifests (guardrail section 3) ④ is the kubectl target scope (`--context`·`-n`) explicit ⑤ is there a rollback procedure.

Every reviewer prompt must include: an instruction to read the target project harness (`.agents/projects/<name>/AGENTS.md`), the spec path, and the output path `_workspace/<task>/phase1_reviewer-<perspective>_report.md` (doc-writer work-report template — **English**, root section 15. The integrator's final verdict and the user-facing report are in Korean). Reviewers·integrator are **design tier**, so the Agent call must set `model` to the top-performance model per the section 9 table (orchestrate tier application rule — left unset, session-model inheritance silently ignores the tier policy).

**Simultaneous dispatch (mandatory)**: perspective reviewers do not depend on each other's results, so **dispatch all of them in one response (same turn)** (orchestrate mode-B simultaneous-dispatch rule). Waiting for the correctness review to finish before starting the test review is serial degeneration and a rule violation — the only place where sequencing is allowed is the integrator after all reviews finish (fan-in inherently depends on review completion).

**Integration**: the integrator merges via the 5 gate principles → `phase2_integrator_verdict.md`. The final report uses orchestrate's fixed format (must-fix count·locations / should-fix count / report path).

## Solo mode — lightweight review protocol (removing fixed overhead for small diffs)

One reviewer agent handles it, with the gate principles (evidence-free findings excluded, severity placement) applied identically — **only the fixed overhead is cut**: not skipping verification but making it cheap (measured 2026-07-21: even on a small diff a reviewer spent minutes·tens of thousands of tokens — re-collection·all-axis sweeps·report filing are fixed costs independent of diff size).

1. **Inline the inputs (dispatcher's duty)**: include **the full diff, a spec completion-criteria excerpt (with path), and the latest test output** directly in the dispatch prompt — do not leave the reviewer to re-collect via tool round-trips. **But if the diff exceeds 10KB, pass a diff file path (scratchpad etc.) instead of inlining the full text** — the intent (eliminating re-collection round-trips) is equally achieved with a single Read, while inlining a large diff double-loads the same content into the dispatch prompt and the reviewer's file re-read (measured 2026-07-22: 53KB diff worked flawlessly via the pointer method). Independence is preserved: the verdict owner is different, **the reviewer re-runs change-related tests directly** (never taking the implementer's report on faith — section 13 item 2), and **the provided diff is scope-checked against the actual repository diff** (`git diff --stat` level — prevents omissions on the dispatcher=author path, reviewer §3).
2. **Perspective selection**: review only the axes matching the change type (e.g. docs diff → correctness·convention; logic diff → correctness·tests·simplicity; add security when a security surface is touched). Skip non-applicable axes with a one-line "N/A" — the all-axis sweep belongs to team mode (high risk).
3. **Report lightweighting**: **for ≤2-file·low-risk diffs, skip the `_workspace/` report file** and deliver the verdict as return text (PASS/BLOCK + finding list·grounds — English, root section 15. Risk uses Phase 0's two-level verdict — low risk = guardrail section 3 not applicable). Reason: report files assume write-once·read-N-times, but a produce-verify pair has a single consumer, the orchestrator (N=1), so filing is pure cost. **On a must-fix finding, do file the report** (it becomes the reference document for the rework loop — `phase1_reviewer_report.md`, existing format).
4. **Background dispatch**: dispatch defaults to `run_in_background` even when the verdict gates the next step — end the turn and resume from the completion notification (CLAUDE.md anchor, user decision 2026-07-24; the session stays conversable during the review).
5. **Verification-scope cap (dispatcher states it)**: for small-diff reviews, dispatch with the verification scope limited to **the diff and its pointer targets** (referenced specs·rules·reports), exclude free repository exploration from scope, and state a work cap (default ~10 tool calls) in the dispatch prompt. Within the cap, **exhaust the 2 never-skip duties first (test re-run·diff scope check)**; on hitting the cap, honestly declare the remaining items via **evidence field ④ (what was not verified)** and deliver the verdict — this is not cutting verification but scaling its depth to the diff surface, and unverified scope is never hidden (section 13 item 2). Reviews needing external fact-checking (external-repo adoption review etc.) get an explicitly raised cap from the dispatcher (measured 2026-07-22: free-exploration review of a small docs diff cost ~58k tokens per run — cap·scope limits estimated to save 30–50%).

**For 3–5 files (low risk)**, keep input inlining·perspective selection·background as-is but use the full report format as before (`phase1_reviewer_report.md`); **for 6+ or high risk**, promote to team mode (Phase 0 table — risk has only two levels (low/high), there is no "medium" grade).

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Blind spots | One reviewer's perspective bias carries straight into the final verdict | Perspective decomposition + independent parallel + gate |
| Verdict criteria | Taste·impression-based review | Reproducible verdict against spec completion criteria |
| Cost | Same weight for every review | Size-scaled — solo for small, team only for large |
| Rework cost | New reviewer and full recollection each round | Same reviewer thread + delta re-verification |
| Noise | Evidence-free findings mixed in | Excluded at the gate |
