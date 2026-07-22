---
name: branch-workflow
description: Start and finish subproject work on clean feature branches to prevent stale-branch merge conflicts. On start - fetch, fast-forward main, create a feat/fix branch; on finish - rebase onto latest main, push, and open a PR via gh (merge stays with the user). Applies to subproject repos only, not the root harness repo. Use when starting any subproject task or when the user says 작업 시작, 브랜치 만들어, PR 생성, 머지 준비, ship, push to main. Never auto-merge - external ship/land skills must not merge or push to main directly. Re-run keywords - branch, PR, rebase, 브랜치, 작업 시작.
---

# branch-workflow — subproject branch & PR workflow

## Why this skill

Observed recurring problem (evolution trigger "repeated failure"): starting new work on top of a previous task's stale branch → drifting further from main → conflicts at merge time. The cause is not the conflict itself but that **the starting point was not the latest main**. So this skill pins both ends: the start (always branch off the latest main) and the finish (rebase right before the PR). Method confirmed in the 2026-07-12 user interview.

**Scope**: independent subproject repositories only. **The root harness repository is an exception** — it is document-centric and keeps direct commits to main (root AGENTS.md section 5).

## Start procedure (first step of every subproject task)

> **Order**: for implementation or multi-step work, the **orchestrate Phase 0-1 gate ruling comes first** (root AGENTS.md section 7, item 3) — this start procedure is the first step after the ruling confirms execution, before touching any files. If you create the branch before the gate and the ruling comes back "not direct execution", an empty branch is left behind.

1. **Check current state**: `git status` — if there are uncommitted changes, do not proceed; ask the user how to handle them (commit/stash/discard). Reason: auto-handling changes that may belong to someone else's work becomes a data-loss incident. **Right after a session resume or a `/model` switch, re-check the current branch with `git branch --show-current` before editing files** — you may have silently landed back on main (real case 2026-07-22: caught just before a direct commit to main right after resume — applies not only at the start but also to mid-work resumes).
2. **Update main**: `git fetch origin` → `git checkout main` → `git pull --ff-only`. If fast-forward is impossible (local main contaminated), stop and report the state — branching from a contaminated main propagates the problem into the branch.
3. **Create a new branch**: `git checkout -b <type>/<concise-description>` — type matches the commit convention (feat|fix|refactor|chore, etc.), description in kebab-case (e.g. `feat/login-oauth`, `fix/schedule-overlap`).
4. Do the work (commits follow Conventional Commits + project scope). **For feature additions or behavior changes, keep the spec → failing test order before implementing** (root AGENTS.md section 13 SDD+TDD; spec uses the doc-writer template).

## Finish procedure (on task completion)

1. **Verify**: confirm tests and build pass (do not open a PR in a failing state).
2. **Rebase right before the PR**: `git fetch origin` → `git rebase origin/main`. On conflict, **before** resolving, report the conflicting files and content to the user and confirm the resolution direction.
3. **Push**: `git push -u origin <브랜치>`. For an already-pushed branch whose history was rewritten by rebase, use `--force-with-lease`, but **only on your own feature branch + with user confirmation** (section 3 guardrail — force variants require confirmation without exception). Never force-push to main under any circumstances.
4. **Create the PR**: `gh pr create` — title in commit-convention format; body follows the **doc-writer PR template** (`.agents/skills/doc-writer/references/templates.md` #5: 요약/변경 내용/연결/검증/리뷰 포인트) exactly. If the task is registered in work-tracker, put `Closes #<issue-number>` in the 연결 (links) section (auto-closes the issue on merge). The 검증 (verification) section must contain actual commands and results — no evidence-free "tests pass". Report the PR URL.
5. **The user does the merge.** After merge, recommend deleting the feature branch — the next task's start procedure (1–3) presumes "branches are disposable".

## Edge cases

- **Work drags on and main gets far ahead**: no need to wait for the finish — running `git rebase origin/main` mid-work is fine; conflicts are cheaper to resolve while small.
- **gh CLI absent / remote is not GitHub**: skip the PR-creation step and report the pushed branch name plus manual PR-creation guidance.
- **No remote (local-only repository)**: skip fetch/pull in the start procedure and branch off local main; at finish, get the user's confirmation for a local merge.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Starting point | Starting on a stale branch → conflicts pre-booked | Always branch off the latest main |
| Conflict timing | Discovered all at once at merge time | Pre-resolved + reported via rebase right before the PR |
| Review record | No record with local merges | Changes and verification results preserved per PR |
| Final gate | Auto-merge removes human involvement | The merge button belongs to the user — a human stays in control |
