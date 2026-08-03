---
name: wrapup
description: "Wrap up before clearing: route durable work to work-tracker or carryover, and capture real improvement signals/lessons. Slash-invoked only; guides but cannot run /clear. Not for mid-session logging, auto-applying harness edits, or periodic review. Re-run: wrapup, 마무리, 세션 마무리, clear 전 정리, 세션 회고."
---

# wrapup — Session Wrap-up Before clear

## Why this skill

`/clear` is a Claude Code **built-in CLI command**, so the context is emptied the instant it runs, and the model has no turn to intervene at that moment. As a result, "gathering what this session should leave behind, right before clear" gets missed every time — work spanning multiple sessions goes unregistered, notes meant for the next session vanish, and **harness/project improvement signals surfaced in this session evaporate along with the context.**

This skill fills that gap. Since `/clear` itself cannot be fixed, it operates as a **wrap-up gate placed in front of `/clear`** — it sweeps this session's work, **judges the save target by scope** and handles it (local saves are automatic without confirmation; only work-tracker registration gets a just-before confirmation), **captures and proposes improvement signals if any exist**, then guides the user to run `/clear`.

**It is a thin orchestrator — it does not re-implement save/apply logic.** Work saving is delegated to `work-tracker`·`carryover`, and actual application of harness/project improvements to `metaskill`. What this skill does is ⓐ collect session work and branch to the save target ⓑ capture and propose improvement signals ⓒ guide the clear. Reason: duplicating save/apply logic drifts from the source skills and becomes debt — keep only assets whose need is proven and reuse the rest (ADR 007 lazy creation).

**This skill is invoked only via slash (`/wrapup`)** — for the same reason as carryover, it is not registered in harness auto-routing (CLAUDE.md anchors·§7). It is a tool that should act only at the moment the user explicitly decides "I will now wrap up the session and empty the context."

## Two core constraints

1. **Cannot auto-clear**: this skill cannot run `/clear` on the user's behalf (a CLI built-in). When processing is done, it finishes by **guiding the user to type `/clear` themselves**. It never promises anything like "I'll do the clear for you automatically."
2. **Cannot auto-apply improvements**: the retrospective step goes only as far as **capturing, recording, and proposing** signals. It does **not modify the harness or projects directly** — unauthorized harness/project changes bypass the evolution gate (root AGENTS.md §8 propose→approve, §12 lazy creation), and metaskill forbids unauthorized creation/retirement (the harness is the user's operating asset). Actual application goes only through **the metaskill path after user approval** (same as the existing evolution gate).

## Procedure

### 1. Sweep this session's work

Collect what happened in this session. At minimum:
- **Changed/added files** — check via `git status`·`git diff --stat` (regardless of commit status). **Subproject work done in a worktree is invisible from the root and from `project/<name>/`** — a status run in either place reports a clean tree while uncommitted work sits in the worktree. Enumerate them with `git -C project/<name> worktree list` — **not by globbing the directory**, since a branch name with a slash nests (`project/.worktrees/<name>/feat/x/`) and a glob returns the intermediate `feat/`, not a worktree — then run the status check **at each worktree path**; a sweep that misses them is the exact input that makes step 3 conclude "nothing to leave" over unsaved work.
- **Decisions/agreements made** — directions and choices settled in the conversation
- **Done items / unfinished items / blockers** — what is finished now, what must continue next, what is stuck

Show the user a **short summary of the results, in Korean**.

### 2. Session retrospective — capture improvement signals (only when signals exist)

Look back over this session and **lightly check only whether improvement signals occurred**. Targets:
- **Harness improvement signals** (root AGENTS.md §8 expansion signals ①–③): repetition of the same request type / repetition of the same failure or the same user correction / **cases handled by bypassing the harness**
- **Recurrence-prevention lessons** ("record mistakes immediately" — §8): mistakes/lessons with recurrence-prevention value even on a first occurrence, without waiting for a second
- **Per-project improvements**: skill/agent candidates surfaced during sub-project work (§12 lazy-creation trigger), gaps in the sub AGENTS.md

**If there are no signals, move on with the one line "이번 세션 개선 신호 없음" (no improvement signals this session)** — a heavy retrospective gets bypassed every time (minimalism). Do not fabricate signals.

**If there are signals**:
- **Record lessons immediately, now** (no waiting for proposal — §8 "record mistakes immediately"): in Claude sessions, record to auto-memory (feedback type), but **the index line carries the triggering situation, not the lesson's gist** (in what kind of work this should be recalled). In Codex sessions, write the lesson file and the MEMORY.md index line in the same repository directly.
- **For anything requiring harness/project application, only propose** — "이번 세션에서 〈신호〉를 관찰했습니다. metaskill로 반영할까요?" (harness assets), or propose recording in the sub AGENTS.md "스킬 후보" (skill candidates) section (projects). **Only after user approval does it go to metaskill**; before approval, fix nothing.

**Boundary with harness-review (not a duplicate)**: this retrospective is the stage that **captures** signals at the session's **end** while context is alive, whereas `harness-review` is the stage that judges cadence (1-day/7-day) via markers at session **start** and **scans/proposes** from accumulated traces. wrapup's capture does not replace harness-review; it **makes the input to that scan accurate** — the two are complementary.

### 3. Auto-judge the save target by scope

Hold the scope collected in step 1 (change size, commit/push status, unfinished items, cross-machine needs) against the boundary table below and **judge the save target yourself** — do not present an empty menu every time. Judgment rules:

- **Nothing to leave**: all changes committed/pushed and no unfinished work/handoff crossing the session → skip the saving in step 4 and continue at step 5 (no confirmation). **"Nothing to leave" does not skip the worktree sweep** — a fully merged and pushed task is precisely the state whose worktree is now removable.
- **carryover**: there is a **local handoff** the next session will pick up (in-progress work, unfinished memos, this-machine-only context) → **auto-run** `carryover` (save mode) (local, gitignored, low-cost, easy to undo → no confirmation).
- **work-tracker**: a formal epic spanning multiple PRs/days, or **cross-machine tracking** is needed → **the judgment is automatic, but confirm once just before registering** ("이 에픽을 work-tracker에 등록할까요?"). Whether the store is a GitHub issue or `docs/backlog.md`, it is git-tracked and externally oriented, and registering everything creates an issue graveyard (§14) — never write without confirmation.
- **Both**: if formal tracking and a local handoff coexist, split them (formal → work-tracker, local memo → carryover — no duplicate loading of the same content). Only the work-tracker part goes through the confirmation above.

**Tell the user the verdict and its basis in one line** (e.g. "전부 커밋·푸시됨 + 미완 없음 → 남길 것 없음"). If the user overrides, follow that. **Only when the scope signals are too ambiguous to tell carryover from work-tracker, ask back via AskUserQuestion** — auto-judgment is the default; asking back is the exception.

### 4. Delegate per the verdict

Invoke the judged target's skill as-is (no duplicate implementation): carryover → `carryover` (save mode); work-tracker → `work-tracker` (register mode) **after user confirmation**; both → invoke sequentially but **never load the same content into both** (formal tracking to work-tracker, local memos to carryover — table below). Move on only after each skill completes.

### 5. Sweep subproject worktrees (delegated — `branch-workflow` owns the rule)

Subproject work runs in worktrees under `project/.worktrees/`, and finished ones would otherwise pile up unnoticed. **Run `branch-workflow`'s "Worktree cleanup" section against every worktree this session's projects hold** — that skill is the single source for the merge measurement, the removal conditions, and the command order. A worktree whose GitHub PR is freshly measured `state: "MERGED"` and whose non-force removal succeeds is removed automatically **without a cleanup question**; fallback and local-only paths retain that source's confirmation boundary. **Do not restate the underlying checks here**; a second copy drifts from the original and this skill re-implements nothing (core constraint above).

Placement is deliberate: cleanup runs **after** step 4's saving, so anything worth keeping is already in a carryover note or an issue before a directory is removed. The order is belt-and-braces rather than the actual guard — a worktree with unsaved work fails the removal check on its own.

If no worktree exists, say nothing (an empty cleanup report is noise). Report survivors in one line with their reason — they are the next session's starting points.

### 6. Fast-forward the projects this session touched

Worktrees are gone, so the `project/<name>/` checkouts are the only copies left — and **nothing updates them.** `branch-workflow`'s start procedure stopped pulling them when work moved into worktrees, and it says so itself while prescribing a fetch before any read. That prescription is the fallback, not the fix: it fires inside whatever future session happens to read, and a dispatched agent that never opened `branch-workflow` does not carry it. Correcting the state here removes the condition instead of relying on the next reader to remember.

**Scope: the projects this session touched** — committed, or merely surveyed. This is a cost boundary, not a safety claim: an untouched project can still go stale when the user merges an open PR elsewhere, and `branch-workflow` routes read-only work to that same checkout without creating a worktree. Widening the scope to every registered project would put a fetch round-trip per project into every wrap-up, which is the trade this boundary takes.

For each, from the harness root:

```bash
git -C project/<name> fetch origin
git -C project/<name> merge --ff-only origin/main
```

**Only for a checkout on `main`.** The command names `origin/main` but merges into whatever branch is checked out, and measured (git 2.39.5) a checkout parked on a leftover feature branch with no commits of its own is **fast-forwarded onto `origin/main`, silently moving that branch pointer** — which `branch-workflow` promises to leave untouched. Nothing is lost (ff keeps the old tip reachable), but it is not this step's business to move someone's branch. Read the branch first (`git -C project/<name> symbolic-ref --short HEAD`); anything other than `main`, including a detached HEAD, is reported and skipped. A repository with no `origin`, or whose default branch is not `main`, fails on its own and lands in the same skipped report.

**Let `--ff-only` do the judging — do not pre-gate on a dirty tree.** Measured (git 2.39.5): it exits 128 *"Not possible to fast-forward, aborting"* when the branch has diverged; it **succeeds** when unrelated files are dirty, leaving those changes untouched; and it aborts, preserving local edits, when the update would overwrite a dirty file. A `git status` pre-check is a blunter judgment layered over a precise one — it skips the safe case that git would have taken. **No variant of this can lose committed or uncommitted work**, which is why it needs no §3 confirmation.

Report each outcome in one line — advanced (with the short hashes), already current, or skipped with git's reason. **Never reach for a plain `merge` or a `reset --hard` to force one through**: a refusal means there is local state here that the remote does not have, which is a report, not an obstacle.

**"Nothing to leave" in step 3 does not skip this step** — a session that committed, pushed, and merged everything is exactly the one whose checkout is now furthest behind.

**This reduces how often the stale-read condition exists; it does not close it.** Say it that way rather than calling the remainder covered — the premise of this whole step is that `branch-workflow`'s fetch-before-read did not reach a dispatched agent, so handing the residual back to that same prescription would describe as guarded the exact reader class that already failed. Three gaps, and none of them is small:

1. **A PR merged after wrap-up.** The step pulls only what is already merged, so it cannot advance a checkout whose PR the user merges later. The worktree survives step 5 for the same reason, and both settle at the next wrap-up.
2. **Sessions that never run this skill.** `/wrapup` is slash-invoked only and deliberately outside auto-routing, so every session the user ends without typing it leaves the checkouts exactly as they were.
3. **A project this session did not touch**, made stale by a merge elsewhere and then read read-only next session — the scope boundary above, restated as what it costs.

Fetch-before-read remains the only guard in all three windows, which is precisely why **a dispatch that will read a checkout must carry the fetch instruction in its own prompt** — a subagent never loads `branch-workflow` on its own.

### 7. Guide `/clear` + next-session start prompt

When saving/proposing is done, along with a wrap-up summary, **guide the user to type `/clear`** (the skill does not run clear on their behalf — core constraint 1 above). Then **present the "next-session start prompt" as a copyable code block** — so the user does not have to reconstruct the resume path (`/carryover 재개` · "이어서 하자") from memory, wrapup produces the sentence that, pasted into a new session, starts the resume (2026-07-21 user request). Generation rules per save target:

- **When carryover was saved**:
  ```
  /carryover 재개 — <주제슬러그> 노트. 첫 행동: <노트 "In progress · Next"의 첫 항목 한 줄>
  ```
- **When work-tracker was registered**:
  ```
  이어서 하자 — #<이슈번호> <이슈 제목>. 첫 행동: <진행 로그 "다음" 항목 한 줄>
  ```
- **If both**, present the two blocks with an ordering (decide from the priority of the unfinished items whether the formal epic or the local memo comes first, and add one line saying so).
- **If nothing to leave**, generate no prompt (an empty resume prompt is noise).

The prompt is **in Korean** (a sentence the user types — root §15), and the trigger phrases (`/carryover 재개` · "이어서 하자") must match each skill's re-run keywords — these phrases are the key that puts the new session through routing (§7). Take the one-line "첫 행동" (first action) verbatim from the saved note/issue (do not invent it anew — divergence creates two resume points).

## work-tracker vs carryover boundary (judgment basis)

| | work-tracker | carryover |
|---|---|---|
| Store | GitHub Issues / `docs/backlog.md` (git-tracked, cross-machine) | `_workspace/carryover/*.md` (gitignored, **local to the same machine**) |
| Target | Multi-PR/multi-day epics, formal | **Light handoff memo** from this session to the next |
| Loss risk | Low (remote backup) | Local only — cannot leave the machine |

→ If formal, cross-machine tracking is needed: work-tracker; if a local scratch handoff: carryover. Mixing the two either creates an issue graveyard (everything on GitHub) or leaves important cross-machine work local-only and lost.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Pre-clear wrap-up | Regret ("should have registered") only after the context is emptied | The gate right before clear forces the save decision |
| Improvement signals | Fresh end-of-session signals evaporate; harness-review reconstructs after the fact | Captured while context is alive → recorded/proposed immediately |
| Save-target judgment | Confusion between work-tracker and carryover, asked every time | Auto-judged by scope (local saves unconfirmed, only work-tracker confirmed just before), asking back only when ambiguous |
| Duplicate implementation | Wrap-up/apply logic improvised every time | Reuses existing skills (work-tracker·carryover·metaskill·branch-workflow) |
| Worktrees | Finished ones accumulate; work inside them is invisible to a root `git status` and gets swept up as "nothing to leave" | Enumerated during the sweep, removed only after a measured merge check |
| Project checkouts | Left behind indefinitely once worktrees took over; a later read-only survey reports the stale tree as current | A touched checkout on `main` is caught up at wrap-up, so the stale-read window narrows to the three gaps step 6 names |
