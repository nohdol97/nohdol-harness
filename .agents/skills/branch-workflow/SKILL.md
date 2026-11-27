---
name: branch-workflow
description: "Start and finish subproject feature branches: sync main, branch, rebase, push, PR, and gated merge. Use for 작업 시작, 브랜치, PR 생성, 머지 준비, ship, push to main. Subprojects only; never --auto/--admin; never push directly to main. Re-run: branch, PR, rebase, 브랜치, 작업 시작."
---

# branch-workflow — subproject branch & PR workflow

## Why this skill

Observed recurring problem (evolution trigger "repeated failure"): starting new work on top of a previous task's stale branch → drifting further from main → conflicts at merge time. The cause is not the conflict itself but that **the starting point was not the latest main**. So this skill pins both ends: the start (always branch off the latest main) and the finish (rebase right before the PR). Method confirmed in the 2026-07-12 user interview.

**Scope**: independent subproject repositories only. **The root harness repository is an exception** — it is document-centric and keeps direct commits to main (root AGENTS.md section 5).

**Install-site scope**: both profiles use the same dedicated feature-worktree procedures (ADR 052), with the **Pi runtime exception** in root AGENTS.md §11 (ADR 053). Pi-native sessions may choose the checkout option; Claude/Codex sessions keep the dedicated worktree.

### Pi checkout option

Only an identified Pi session may replace the dedicated-feature-worktree start with this option. The orchestrate gate still comes first. Choose one execution directory and report its absolute path and feature branch; keep the session cwd at the harness root. The worktree-only statements in the standard start procedure below describe the default path, not a requirement to migrate this option into a worktree.

Before switching a shared checkout, inspect `git -C <checkout> status --porcelain`, `git -C <checkout> branch --show-current`, and `git -C <checkout> worktree list`. A dirty checkout or another session using it is not permission to move their work: use an isolated worktree, serialize the work, or obtain a data-loss decision under §3 before switching. Do not stash, reset, or force a switch. For a clean checkout exclusively available to this task, create a new branch with:

```bash
git -C <checkout> fetch origin &&
git -C <checkout> switch --no-track -c <type>/<description> origin/main
```

Continue only if both commands succeed and `git -C <checkout> branch --show-current` reports the intended feature branch; never fall back to writing on main. For a local-only repository, skip fetch and use local `main`, as in Edge cases. For an existing task, preserve its branch and path instead of recreating it: inspect status first, reuse an existing worktree if that branch is held there, and switch a clean unoccupied checkout with `git switch <branch>` only when needed. If branch identity or ownership is unclear, preserve the tree and resolve it before writing. Recheck the selected branch before edits, commits, and after any interruption, since this option lacks worktree isolation.

Use the chosen absolute checkout path wherever Finish procedure says `<worktree>`; pass that same path to each subagent and verify its branch. Tests, rebase, push, PR evidence, and the Session merge gate remain mandatory. Parallel writers must be isolated or serialized. On wrapup, the shared `project/<name>/` directory is never removed with `git worktree remove`; retain its branch and report it. Apply worktree cleanup only to actual linked worktrees.

## Start procedure (first step of every subproject task)

> **Order**: for implementation or multi-step work, the **orchestrate Phase 0-1 gate ruling comes first** (root AGENTS.md section 7, item 3) — this start procedure is the first step after the ruling confirms execution, before touching any files. If you create the branch before the gate and the ruling comes back "not direct execution", an empty branch is left behind. The gate's in-flight work survey (orchestrate 0-2 item 7) also precedes worktree creation: do not create a worktree for a task another session already holds or has declared.

**Work happens in a dedicated worktree, never in the `project/<name>/` checkout itself.** That checkout is left on whatever branch it was already on, untouched. Reason: branching off `origin/main` into a fresh directory makes "started from the latest main" **structural instead of procedural**, and it closes both failure modes this skill was built for at once — a stale starting point, and silently landing back on main after a resume (a worktree holds exactly one branch, so there is nothing to land back onto).

**Firing condition — work that changes files.** Implementation, fixes, refactors, spec/doc edits inside the subproject repository: worktree first. **Read-only work creates no worktree** — diagnosis, status checks, exploration, and reading code stay in `project/<name>/`, because setup and cleanup buy nothing when nothing is written. When read-only diagnosis becomes the first product Edit, that transition re-enters the orchestrate gate (root §7 item 3) and this procedure runs then.

**The start procedure no longer refreshes that checkout**, and read-only work is exactly what gets routed to it. `wrapup`'s fast-forward step catches up the projects a session touched, so it no longer drifts indefinitely — but that step is slash-invoked, runs only at wrap-up, pulls only what is already merged, and skips any checkout not on `main`, so assume nothing about how current the tree is. Before diagnosing there, `git -C project/<name> fetch origin` and read `origin/main` when the answer depends on current state; treat the working copy as a possibly-stale snapshot. Same reasoning as root §5 — a stale read is what makes a confident wrong answer.

**The session does not move into the worktree.** cwd stays at the harness root; every command names the worktree by **absolute path** (`git -C <worktree>`, absolute paths for Read/Edit/Write). Reason: `EnterWorktree` binds the session to one repository's worktree and switching out requires a worktree of *that same* repository — so cross-project work would be trapped in the first project's worktree, subagents included (they inherit the parent's cwd). Staying at root also keeps root §12's "every session starts at the root" premise intact rather than making harness loading depend on parent-directory `CLAUDE.md` discovery.

1. **Create the worktree** — from the harness root:
   ```bash
   root="$(pwd -P)"
   test -f "$root/REGISTRY.md" && test -f "$root/.agents/skills/branch-workflow/SKILL.md" || { echo "Run from the harness root" >&2; exit 1; }
   worktree="$root/project/.worktrees/<name>/<type>/<description>"
   git -C project/<name> fetch origin
   git -C project/<name> worktree add "$worktree" \
       -b <type>/<description> --no-track origin/main
   test "$(git -C "$worktree" rev-parse --show-toplevel)" = "$worktree"
   ```
   `<type>/<description>` follows the commit convention — type is feat|fix|refactor|chore etc., description in kebab-case (`feat/login-oauth`, `fix/schedule-overlap`). **`--no-track` is required**: without it the new branch takes `origin/main` as upstream, so `git status` in the worktree reports it as "behind" and suggests `git pull` — which would merge main into the feature branch (measured 2026-07-29: upstream reads `chore/x...origin/main` without the flag, and no upstream with it). Variants:
   - **Resuming an existing branch** (work-tracker resume, review rework): drop `-b` and `--no-track` — `worktree add <abs-path> <type>/<description>`.
   - **No remote** (local-only repository): branch off local `main` instead of `origin/main`.
   - **`origin/main` cannot be fetched**: stop and report. Branching from a stale base reintroduces exactly the drift this skill prevents.
   - **`core.autocrlf` is `true`** (`git -C project/<name> config --get core.autocrlf`; the usual Git for Windows global): a plain `worktree add` checks every text file out as CRLF while the long-lived checkout may hold LF, so LF-enforcing linters fail across the whole worktree (observed 2026-11-27 on a corporate Windows host: Prettier failed on 1,131 files). Create it unchecked out, scope LF settings to that worktree, then check out — chained, so nothing after a failed `add` can touch an existing worktree:
     ```bash
     git -C project/<name> config extensions.worktreeConfig true &&
     git -C project/<name> worktree add --no-checkout "$worktree" -b <type>/<description> --no-track origin/main &&
     git -C "$worktree" config --worktree core.autocrlf false &&
     git -C "$worktree" config --worktree core.eol lf &&
     git -C "$worktree" checkout -f HEAD -- .
     test "$(git -C "$worktree" rev-parse --show-toplevel)" = "$worktree"
     ! git -C "$worktree" ls-files --eol | grep -q 'w/crlf'   # succeeds when no CRLF file is left
     ```
     `core.eol lf` is needed because with `autocrlf` off a `text=auto` attribute falls back to `core.eol`, whose default `native` is CRLF on Windows; an explicit `eol=` in `.gitattributes` overrides both, so a nonzero count there is the repository's own choice. The settings live in that worktree's own config, so later rebases there also write LF, and the repository's `true` stays for everything else. To repair a worktree already checked out as CRLF, the uncommitted-work check must come **before** the settings change (afterwards every CRLF file reads as modified), and the index must be dropped first — a forced checkout skips files whose stat still matches the index, which left CRLF in place in a `text=auto` repository (measured); deleting the files instead breaks on submodule directories:
     ```bash
     test -n "$worktree" && test "$(git -C "$worktree" rev-parse --show-toplevel)" = "$worktree" &&
     test -z "$(git -C "$worktree" status --porcelain)" &&
     git -C project/<name> config extensions.worktreeConfig true &&
     git -C "$worktree" config --worktree core.autocrlf false &&
     git -C "$worktree" config --worktree core.eol lf &&
     git -C "$worktree" rm -r -q --cached . &&
     git -C "$worktree" reset -q --hard HEAD
     ```
     The first line stops on a wrong or empty `$worktree`, a non-empty status on uncommitted work; resolve that first, since this rewrites every tracked file.

   **Location is `project/.worktrees/<name>/<branch>/`**, and each part of that is load-bearing: `project/` is gitignored (REGISTRY.md path convention), so the root repository stays clean; the leading dot keeps it out of the `project/*/` glob that project scans use; and it sits **outside `_workspace/`**, which holds session artifacts — a worktree holding uncommitted work must remain separate from artifact cleanup. **The worktree path must be absolute**: a relative path is resolved against `-C`'s directory, not the root. The final `test` is a start gate: if it fails, inspect `git -C project/<name> worktree list --porcelain` and stop before editing. Preserve any worktree created at the wrong path; do not silently move or remove it. On resume, derive the expected path from the root, project name, and branch as above, then compare the registered worktree's actual path to it; an existing branch at a different path is not an exemption.
2. **Uncommitted changes in `project/<name>/` no longer block the start.** The old rule stopped here and asked the user, because `git checkout main` would have moved work that might not be yours. Nothing moves now — `worktree add` does not touch that checkout. Still **report the leftover changes in one line** so they are not forgotten, and if they belong to the task you are about to start, ask before working around them in a second directory. The old resume-time `git branch --show-current` re-check is gone with the same cause: a worktree holds one branch, so there is no branch to have silently landed on (the 2026-07-22 case it guarded is recorded in ADR 035).

**A fresh worktree has no dependency directory, and bootstrapping it is part of the start, not a surprise mid-task.** A worktree shares the repository, not the untracked build state — `.venv`, `node_modules`, and their kin do not come along. Measured 2026-08-05: all six registered projects carry a `.venv` (7–27MB), and recreating `telemetry-contract`'s took **8–12s** (two runs, cold and on a `git archive` copy — the point is the order of magnitude, not the second). Run the bootstrap **before any command runs in the new worktree**, using the command the project's own AGENTS.md gives (`telemetry-contract` §2 records `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`), and **name that step in any dispatch prompt that will run tests there** — otherwise the agent meets a missing runner mid-task and either rebuilds it unprompted or reports a failure that is not the code's (observed 2026-08-05: an implementer had to create the venv itself before it could run anything).

**Never share that directory by symlink or copy to skip the cost.** These projects install editable (`pip install -e`), and **which tree a borrowed environment imports depends on how you invoke it** — measured in this workspace and recorded at `.agents/projects/agent-eval-onboarding/AGENTS.md`: `.venv/bin/python -m pytest tests/` picks up the *worktree's* package, while the `.venv/bin/pytest` console script picks up the *checkout's*. So the failure is not uniform, which is exactly why the prohibition is flat rather than conditional: the unsafe form is the shorter one people actually type, and the two are indistinguishable in a green test run. A pass over the wrong tree costs more than every rebuild it would have saved.

3. Do the work **at the worktree path** (commits via `git -C <worktree>`, following Conventional Commits + project scope). **When the work is dispatched to a subagent — the official route at 3+ files — put the absolute worktree path in the issuing prompt** (orchestrate's CONTEXT element): agents inherit the session cwd, which is the root, and `project/<name>/` is sitting on an unrelated branch, so an agent left to infer the location writes to the wrong branch (the orchestrator layer commits — implementer and infra-specialist do not). **For feature additions or behavior changes, keep the spec → failing test order before implementing** (root AGENTS.md section 13 SDD+TDD; spec uses the doc-writer template).

## Finish procedure (on task completion)

> Steps 1–3 run **inside the worktree** — `git -C <worktree> …`, tests and build invoked at that path. Running them in `project/<name>/` verifies and pushes a different branch than the one you changed.

1. **Verify**: confirm tests and build pass (do not open a PR in a failing state).
2. **Rebase right before the PR**: `git -C <worktree> fetch origin` → `git -C <worktree> rebase origin/main`. On conflict, resolve it keeping both sides' intent and re-run the affected tests; report the files and the choice at completion (root §13-0). Stop for the user only when keeping one side would discard the other's behavior.
3. **Push**: `git -C <worktree> push -u origin <브랜치>`. For an already-pushed branch whose history was rewritten by rebase, use `--force-with-lease`, but **only on your own feature branch + with user confirmation** (section 3 guardrail — force variants require confirmation without exception). To avoid needing one when `main` moves after the push, merge `origin/main` into the branch instead of rebasing again. Never force-push to main under any circumstances.
4. **Create the PR**: `gh pr create --repo <owner/repo>` — **`--repo` for the same reason as in the cleanup section** (cwd is the harness root, so an unqualified `gh` targets the root harness repository); derive it from `git -C project/<name> remote get-url origin`. Title in commit-convention format; body follows the **doc-writer PR template** (`.agents/skills/doc-writer/references/templates.md` #5: 요약/변경 내용/연결/검증/리뷰 포인트) exactly. If the task is registered in work-tracker, put `Closes #<issue-number>` in the 연결 (links) section (auto-closes the issue on merge). The 검증 (verification) section must contain actual commands and results — no evidence-free "tests pass". **The 변경 내용 section carries the diagram obligation, and this step is where it is held** — a PR body is authored after the review window closes, so no reviewer sees it before it ships (ADR 039). Apply the `diagram` skill's thresholds to what this PR changed; where one is met, draft the body to a scratchpad `.md`, run `check.py` on it, then submit. **A met threshold with no diagram, or a `check.py` failure, blocks PR creation exactly as an absent 독립 검증 line does** — otherwise this clause advises where the line beside it withholds, and "held" would mean two different things inside one step. **It must also carry the template's 독립 검증 line, and this step holds the PR until it does**: either the reviewer rounds and their verdict, or — where independent review could not run — that fact stated in those words plus what was verified in its place. **An absent line blocks PR creation exactly as an evidence-free 검증 section does**, because it is the only step where a missing review becomes visible before the merge; without it a declared unreviewed PR and a silently unreviewed one are the same document. Report the PR URL.
5. **Merge per Session merge below**, then clean up per Worktree cleanup — the start procedure presumes "branches and worktrees are disposable".

## Session merge (every project, every installation profile — ADR 064)

The session that owns the PR merges it without asking. Reason: work stopped at every open PR, and the user kept re-typing "머지도 알아서". The gate replaces the human at the merge button, so it is never shortened. A project AGENTS.md may tighten it. Merge only PRs this session owns: one it opened, or one handed over by an author shown to have stopped; never a peer's.

1. **Independent review**: `reviewer` PASS on the PR's final head, must-fix items applied and delta-reviewed. Host self-review does not count. A PASS carries over to a head whose only change is a conflict-free rebase onto or merge of `origin/main` **and** whose PR patch is unchanged (`git diff origin/main...HEAD | git patch-id --stable` equal before and after, each measured against its own fetched base); record both ids. A conflict resolution or any other commit needs a delta review. Review could not run → do not merge; leave the PR open and report.
2. **full suite green** on the tree that merges (fresh `origin/main` in the branch; root §13-2 run limits). When `main` moves again after the final run, rerun as `orchestrate` `references/test-execution.md` says, unless the project AGENTS.md records a user-directed narrower rerun scope, which governs (PKI Merge rule 2). Same cap exhausted → leave the PR open and report; never loop. A project with no runnable suite: run what its AGENTS.md names and say so in the PR; if nothing verifies the change, do not merge.
3. **Do not wait for CI.** Read `gh pr checks <N> --repo <owner/repo>` once just before merging. Pending or absent → merge. Failed → read that log: caused by this change, or cause undetermined → fix or investigate first; shown unrelated (also red on `origin/main`, or an infrastructure fault) → merge and report it.
4. **§3 is not relaxed.** A merge that triggers a production deploy, a DB migration run, or an IAM/permission change needs the §3 confirmation first: check the project AGENTS.md, workflows, and GitOps or hosting triggers; unknown trigger on a deployable project → treat as deploying. Deploying after the merge stays with `release`.
5. **Merge**: `gh pr merge <N> --repo <owner/repo> --merge --match-head-commit <SHA that items 1 and 2 hold for>` (use the method the repository allows when merge commits are disabled). **never `--admin`, never `--auto`**, never force, never a direct push to `main`. Branch protection, required approvals or pending required checks that refuse the merge are respected: leave the PR open, re-check it at the next task boundary and at completion, and report; if `gh` queued it, `gh pr merge <N> --repo <owner/repo> --disable-auto`.
6. **Confirm** `gh pr view <N> --repo <owner/repo> --json state` is `MERGED` and `origin/main` contains it after a fetch; record it on the tracking issue.
7. **Clean up in the same turn**, before the next task or the report; do not leave it for `wrapup`: run Worktree cleanup below for this PR's branch, plus any other worktree of the project for which all hold: its PR measures `MERGED`, its HEAD equals that PR's `headRefOid` or is an ancestor of `origin/main`, and an in-flight survey in this turn shows its author stopped (the survey's test — absence of evidence is not enough). Otherwise keep it and report. The completion report names what was removed and what stayed with its reason. A merge is not finished while its worktree remains unexplained.

**Stop instead of merging** when a precondition fails twice, a live peer holds overlapping files, or the PR touches credentials or migrates user data. A PR left open stops only what depends on it: continue with other ready tasks and list the open PR at completion. Without `gh` or on a non-GitHub remote, use the host's equivalent CLI under the same gate; with none, leave the PR or branch and report.

## Worktree cleanup (single source — `wrapup` delegates here)

A worktree is removable only when **both** hold, checked in this order:

1. **The branch is merged, measured now** — root §5 forbids inferring merge state from conversation recency; run the check in this session, after a `git -C project/<name> fetch origin`.
   - **`gh pr view <branch> --repo <owner/repo> --json state,mergedAt` is the primary measurement** (`state: "MERGED"`). It reads the PR, so it is correct regardless of how the merge was performed. **`--repo` is not optional here.** `gh` resolves the repository from cwd, and cwd is the harness root — an unqualified call queries the *root harness* repository, where a subproject branch either does not exist (the check then silently degrades to the fallback and its squash blind spot, so nothing is ever cleaned up) or, on a branch-name collision, returns the harness PR's `MERGED` and falsely authorizes automatic removal of an unmerged subproject worktree. Derive the value, do not type it from memory: `git -C project/<name> remote get-url origin` → `<owner>/<repo>`. Measured 2026-07-29: unqualified from the root, `gh repo view` resolves to the harness repo and the subproject branch returns *"no pull requests found"*; with `--repo` it returns the real PR state.
   - **Fallback when `gh` is unavailable or the remote is not GitHub**: `git -C project/<name> branch -r --contains <branch>`, looking for `origin/main`. Know its two limits before trusting it (both measured 2026-07-29): **squash and rebase merges rewrite the commit, so a genuinely merged branch reads as unmerged** — that direction is safe (nothing gets deleted) but it means a squash-merging repository never cleans up through this path, so say so rather than reporting "nothing to remove"; and **a branch with no commits of its own reads as merged**, because its tip *is* the base commit — harmless, since such a worktree holds nothing to lose.
2. **`git worktree remove` succeeds without `--force`** — measured: it exits 128 with *"contains modified or untracked files"* when anything is unsaved, so **the refusal is itself the data-loss check**. Never reach for `--force` to get past it; a refusal means check 1 passed on a branch whose working copy still holds unsaved work, which is a report, not an obstacle.

**Only the primary `gh` result `state: "MERGED"` qualifies for no-question cleanup.** It is the path root §3 classifies as verified cleanup because it proves the PR itself completed. The ancestry fallback above and the local-main edge case below do not prove a completed PR; before attempting check 2 for those paths, present the candidates and take one user confirmation for the batch. If confirmation is absent, leave them and report why.

Then remove, in this order:

```bash
git -C project/<name> worktree remove <abs-path>   # first — the worktree holds the branch checked out
test "$(git -C project/<name> branch --show-current)" = main &&
  git -C project/<name> merge --ff-only origin/main   # only when the checkout is on main; a refusal is reported, not forced
git -C project/<name> branch -d <branch>
```

Order matters: measured, `branch -d` exits 1 with *"Cannot delete branch … checked out at …"* while any worktree holds it.

The fast-forward is not optional tidying: `branch -d` compares a branch without upstream to the checkout's HEAD, so a stale local `main` makes such a merged branch look unmerged (measured 2026-11-25: PKI `main` 518 behind with 135 merged local branches, nearly all without upstream; after the fast-forward `branch -d` deleted all but 3, whose upstream lagged). Squash-merged branches can still be refused. Skip it for a Pi-option checkout parked on a feature branch, and while a live peer is using that checkout.

**If `branch -d` refuses after a successful removal**, leave the local branch and report it — the worktree is already gone, so cleanup is not blocked. A merged PR does not prove that the local branch tip still equals the merged PR head: new commits may have been added after the merge, and `-D` would discard them. Never use `-D` automatically; a later force deletion is a separate destructive action under root §3 and needs its own user request and confirmation.

**When the primary `gh` check measured `state: "MERGED"`, remove the eligible worktree automatically; do not ask for cleanup confirmation.** Root §3 classifies this exact path as verified cleanup: the primary check proves the remote PR is complete, and check 2 proves the worktree holds no unique unsaved state. The authorization stops at non-force worktree removal and ordinary `branch -d`; it never authorizes `git worktree remove --force`, `branch -D`, deleting an unmerged branch, acting on an unverifiable merge state, or silently promoting a fallback ancestry result into the PR-verified path. Report what was removed and any local branch that remained.

**Whatever fails either check stays, and is reported as a list with its reason** — unmerged / uncommitted work present / merge state unverifiable (fetch failed, no remote). Never delete it and never report a surviving worktree as cleaned up.

> **These are not the harness's other worktrees.** `orchestrate`'s `isolation: worktree` (parallel-write isolation for 2+ concurrent mutating agents) and agent-rules ⑨'s bisect isolation are created by the tool or the agent and live only for one dispatch. The worktrees here outlive a dispatch and hold a feature branch. The two kinds coexist; never clean up one under the other's rule.

## Edge cases

- **Work drags on and main gets far ahead**: no need to wait for the finish — running `git -C <worktree> rebase origin/main` mid-work is fine; conflicts are cheaper to resolve while small.
- **gh CLI absent / remote is not GitHub**: skip the PR-creation step and report the pushed branch name plus manual PR-creation guidance. Cleanup then measures the merge with `git branch -r --contains`, since `gh pr view` is unavailable.
- **No remote (local-only repository)**: skip the fetch and branch off local `main` at start; at finish, merge locally under Session merge 1, 2 and 4 (`git merge --no-ff` in a checkout of `main` that is clean and unoccupied; otherwise report). Cleanup check 1 reads local `main` in place of `origin/main`.
- **A worktree for that branch already exists** (`worktree add` fails with "already checked out"): reuse it rather than creating a second one — `git -C project/<name> worktree list` shows the path.
- **The subproject is not a git repository**: this skill does not apply at all; there is no branch and no worktree to make.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Starting point | Starting on a stale branch → conflicts pre-booked | Branched off the latest main, structurally — the worktree is created from `origin/main` |
| Main checkout | Shared tree switched between branches; a resume can land back on main | `project/<name>/` never moves; each task gets its own directory holding one branch |
| Finished branches | Merged branches and their directories accumulate silently | Removed only after a measured merge check, with the `worktree remove` refusal as the data-loss guard |
| Conflict timing | Discovered all at once at merge time | Pre-resolved + reported via rebase right before the PR |
| Review record | No record with local merges | Changes and verification results preserved per PR |
| Final gate | Unreviewed merge, or every PR waiting on a person | The owning session merges only behind independent PASS + full suite; §3 and branch protection still stop it |
