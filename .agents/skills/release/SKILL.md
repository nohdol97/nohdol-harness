---
name: release
description: "Post-merge release workflow - verify the merged state, draft a deploy runbook (doc-writer template), execute each mutating step only with explicit user confirmation (root guardrail 3), verify the deployment, then close the work-tracker issue. Branches per project type: web/backend via k8s GitOps or a managed platform (Vercel etc.), Flutter app via store submission; DB migrations get a backup/verify/rollback step. Use when the user says 배포해줘, 릴리스, 배포 준비, deploy this, release, land, ship to production. PR merge itself stays with the user (never auto-merge; external land-and-deploy skills must not merge) - this skill starts AFTER merge. Re-run keywords - release, deploy, rollout, 배포, 릴리스, 롤백."
---

# release — Post-Merge Deploy/Release Workflow

## Why this skill

branch-workflow ends at PR creation — deploy, verification, and wrap-up after the merge (done by the user) had no procedure and were handled ad hoc each session. Deployment is the core target of the section 3 guardrails (the blast radius of a mistake is a running system), so the most dangerous stage must not be the one left without a procedure. External skills (gstack land-and-deploy etc.) do not know this harness's guardrails (confirmation with no exceptions, dev included) or its k8s conventions (explicit context, declarative-first) — per the CLAUDE.md skill priority, deployment is governed by this skill, and external tools are used only as aids in the verification phase.

## Phase 0 — Preconditions (always first)

1. **Identify the target**: identify the project in REGISTRY.md and read its harness (`.agents/projects/<name>/AGENTS.md`) — if there are project-specific deploy conventions (environment names, approval procedures), those take precedence.
2. **Check merge state**: confirm the changes to be deployed are merged into main. If the PR is unmerged, stop and direct the user to the branch-workflow finish procedure (merge is the user's) — never deploy directly from a branch.
3. **Check verification state**: confirm tests·build pass and the review verdict (team-review pass). Do not start a deploy in a failing state.

## Phase 1 — Deploy plan (runbook draft)

Write this deployment's plan using the **doc-writer runbook template** (preconditions/procedure/verification/rollback) and show it to the user first (the runbook is a user-read document — write it in Korean, root AGENTS.md section 15). If the scope is large, delegate to infra-specialist (orchestrate verdict). Branch by project type:

| Type | Procedure skeleton |
|---|---|
| Web·backend — k8s GitOps | Pin image tag → update manifests (declarative-first — `kubectl edit/patch` forbidden) → GitOps sync → observe rollout. Every kubectl call states `--context`·`-n` explicitly |
| Web — managed platform (Vercel etc.) | Check deploy trigger (if merge auto-deploys, observe the deploy in progress; if manually triggered, it is a mutating action — user confirmation) → confirm preview/production environment distinction → verify the deployment (Phase 3) |
| App (Flutter etc.) | Bump version·build number → release build → store submission (the submission itself is an external publication — user confirmation) → track review via a work-tracker issue |
| Other | The project harness's deploy procedure. If none, settle it via a user interview and propose recording it in the sub-project AGENTS.md |

**Deploys that include DB migrations (common to all types)**: if a migration is included, add the migration step as its own runbook item — **confirm backup·PITR availability before execution → execute (mutating action, user confirmation — section 3) → verify schema·data**, and the rollback section must specify not just code rollback but **the data recovery procedure**. Reason: code can be reverted, but schema·data do not revert automatically — a rollback section without migration recovery is not a rollback.

**Behavior-changing/heuristic features (common to all types — root AGENTS.md §13-5)**: if the deploy contains a speculative feature — a behavior-changing heuristic such as a threshold trigger, model routing, or auto-escalation — on a hot path (production or shared), verify in the runbook that it ships **feature-flagged, default OFF**. Turning it ON is **its own runbook step**, gated on real-environment measurement of the spec's performance/trigger-frequency assumptions — an unmeasured assumption listed in evidence field ④ blocks the flag-on step, not the deploy itself. Reason: unit tests and review PASS prove logic correctness only; a wrong trigger-frequency assumption regresses every user turn (2026-07-23 real case — SSE timeout).

**A plan without a rollback procedure is not a plan** — if the runbook template's rollback section is empty, do not proceed to Phase 2 (if rollback is impossible, state "rollback impossible — alternative").

## Phase 2 — Execution (⚠️ user confirmation at every step)

- **Mutating commands (`apply`·deploy triggers·store submission·migrations) require user confirmation at each step, immediately before execution** — no exceptions, dev environments included (section 3, confirmed 2026-07-12). Do not batch into one blanket approval: the result of an earlier step can change the premise of a later one.
- Record each step's executed command and actual output (`_workspace/<task>/phase2_{executor}_release-log.md` — section 4 naming convention; the executor is the leader or infra-specialist) — this becomes the troubleshooter's input on failure.
- On a step failure, stop immediately and execute the runbook's rollback procedure **after user confirmation**. Never push on to the next step in a failing state.

## Phase 3 — Post-deploy verification

- Execute the runbook's verification section: health checks, core user flows, presence of new errors in logs.
- For web, external tools (gstack browse·canary) may be used **as aids in this phase only** — governance belongs to this skill, tools are the means (CLAUDE.md skill priority principle).
- On verification failure, report the results and ask the user whether to roll back — never roll back automatically (a rollback is also a mutation).

## Phase 4 — Wrap-up

1. If the work is registered in work-tracker, comment the deploy result on the issue and close it (or convert it to app-review tracking).
2. Release notes·tags·CHANGELOG follow the project's conventions (if none, only propose creating them — no unilateral introduction).
3. Report a deploy summary (what·where·verification result·rollback or not) to the user.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Deploy procedure | Ad hoc every session — the most dangerous stage has no procedure | Runbook draft → per-step confirmation → verification, fixed |
| Guardrails | Leaking to external skills (land-and-deploy) ignores confirmation rules | User confirmation at every mutating step, no exceptions incl. dev |
| Rollback | Improvised after an incident | Rollback procedure fixed before deploying (no procedure → no execution) |
| Tracking | Deploy records exist nowhere | Persisted via execution log + work-tracker issue |
