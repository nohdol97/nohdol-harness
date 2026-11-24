# In-flight work survey (orchestrate 0-2 item 7)

Run before the first write on a project under **every** Phase 0-1 verdict (direct included), before the spec is written (0-2 item 5) or `branch-workflow` creates a worktree, and again on every continuation or resume ("진행해줘", "계속", "이어서", work-tracker/carryover re-entry). Applies to every registered project and to the root harness itself. The survey is read-only: it never edits, stashes, resets, or removes anything it finds.

## Why

Several sessions (Claude, Codex, Pi) can work the same repository at once, and the user's belief about what another session is doing is not evidence. Observed 2026-11-21: the user believed a peer session was running PKI Phase 0; measurement showed it was implementing V01 T09/T11/T14 with uncommitted edits made within the last minute. A new session started on "the next phase" would have written into the same files. Worktree isolation separates working trees, not overlapping file edits, shared documents, or duplicated tasks.

## Collect (`<P>` = `project/<name>`; root harness: `.`)

```bash
git -C <P> fetch -q origin
git -C <P> worktree list                              # every checkout of this repo
for w in $(git -C <P> worktree list --porcelain | awk '/^worktree /{print $2}'); do
  echo "== $w [$(git -C "$w" branch --show-current)]"
  git -C "$w" status --porcelain -uall | head -20     # uncommitted edits, untracked files listed individually
  (cd "$w" && git status -z -uall --porcelain | tr '\0' '\n' | awk 'skip{skip=0;next} /^[RC]|^.[RC]/{skip=1} {print substr($0,4)}' | while IFS= read -r f; do [ -f "$f" ] && /usr/bin/find "$f" -prune -mmin -60; done | head -3)   # changed/untracked files written in the last hour
  git -C "$w" log --format='%h %cr %s' origin/main..HEAD | head -5   # local commits not on main (unpushed ones appear nowhere else)
done
git -C <P> branch -r --no-merged origin/main          # pushed, unmerged branches
gh -R <owner/repo> pr list --state open               # when a GitHub remote exists
ls -t _workspace | head; tail -3 _workspace/<recent>/team-log.jsonl   # recent task logs naming this project
ps -eo pid,lstart,command | grep -E "project/(\.worktrees/)?<name>(/|$| )" | grep -v grep   # commands running inside its checkout or worktrees
```

On Claude Code also call `ListAgents` — it lists peer sessions on this machine with busy/idle state (measured 2026-11-21). It shows that a session exists, not what it edits; tie it to work through the worktree, team-log, and process evidence. **It is the only evidence that reads a session itself (the rest reads its work), so on Claude Code call it before judging any peer stopped.** No single absence shows a peer stopped — a team-log dispatch with no completion yet, a report not yet written, or a `ps` listing (sessions run from the harness root, and a filtered `ps` miscounts them) is consistent with work in progress; only the full stopped test in Separate your own work first does, with `ListAgents` where available. Observed 2026-11-22: a resume judged a peer dead from "dispatched, no report" plus one `ps` line without calling `ListAgents`, and re-dispatched the two reviews that live peer was still running. CLI sessions themselves run from the harness root, so `ps` only catches the commands and servers they start inside a worktree; a match whose path is no longer in `worktree list` is an orphaned process, not live work. Other CLIs: rely on the git and team-log evidence and say `ListAgents` was unavailable.

Call `/usr/bin/find` by path: a command-rewriting proxy (rtk) rejects `-prune`/`-mmin` and returns nothing, which reads as "not live". Only changed files are timed (the `awk` drops a rename's old-path record, which `-z` emits without a status prefix) — a fresh checkout or pull rewrites every tracked file and would otherwise look live.

**Live** = changed files written in the last hour, local commits from the last hour, a command running in the worktree, or a team-log event in the last few hours. Older dirty worktrees are **stale-unknown**: still someone's unsaved state (root §3), never yours to reuse or clean without confirmation, and they count as overlaps for planning.

## Separate your own work first

Exclude from the overlap set: worktrees and files this session created or edited, and — on a resume — the worktree the handoff note or progress log names, **once its author is shown to have stopped**: the author session is gone or idle in `ListAgents` where available, no `ps` match in it, no file written after the note's time, and no team-log event after the note. If that cannot be shown, treat it as a peer's. Reason: a carryover hands over a worktree that is still fresh, and without this step the survey would make a resume skip its own task.

## Held tasks (declared, not only edited)

A peer holds a task before its first edit lands, so edit evidence alone under-counts. Treat a task as held when any of these names it **and its author is not shown to have stopped** (the test in Separate your own work below — a declaration left by a session that has ended, such as a consumed-or-abandoned handoff, an old branch or a stale plan, holds nothing and is resumable): a peer's handoff or carryover note not yet consumed, a spec or plan under `_workspace/` or `docs/specs/`, a team-log task list, a work-tracker issue/progress comment marking it in progress or next, a branch or worktree named for it. A live peer (`ListAgents` busy, or a fresh worktree) whose branch, worktree, team-log or plan names the same spec or epic as your task, and whose declared scope you cannot read, holds that spec's or epic's unstarted tasks — report its scope as unverified rather than guessing it free; a live peer on unrelated work holds nothing of yours. A bare resume with no named task never selects "the next item" from state a still-live peer wrote or is acting on; resumable are this session's own work, a handoff or progress log whose author has stopped, and the user's named task — **unless a live peer holds that named task, in which case it is skipped like any held task and reported**.

## Plan against each in-flight item

| Overlap found | Plan |
|---|---|
| Same task or same worktree, or a task a peer has declared (see Held tasks) | Never take it over. Default: run the other ready tasks (dependencies done) that no peer holds and that overlap nothing in flight — in parallel where they do not overlap each other, sequentially on corporate Claude/Codex hosts (root §11) — and report the skipped task and its holder. When no such task exists — at the start, or later once the parallel work you took is finished — start nothing new, say in one line that no further parallel work is possible (each held task, its holder, what it waits on), and enter **Wait and watch** below instead of ending; asking the owning session via `SendMessage` interrupts a busy peer and is only for an answer that changes the plan. |
| Different task, overlapping files (compare your task's expected files with their `status --porcelain -uall`, `git diff --name-only origin/main...HEAD` in their worktree, and open PR file lists) | Serialize: start after their merge, or choose a non-overlapping task now; with no such task, Wait and watch for the merge. Note the rebase point in the plan. |
| Shared documents (ADRs, README, lockfile, shared config) | One session owns each such file; the other records its needed change as a follow-up for that owner. **Append-only records are not owned**: change-history rows, MOC/index rows, and ops-log lines that a rule requires in the same commit (root §5·§6) are added by each session for its own change, staged hunk-wise as metaskill describes. |
| Semantic dependency (their result can invalidate your premise) | Order your work after it, or proceed behind the existing adapter/contract and record the dependency as a re-check item. |
| Nothing in flight | Record "in-flight: none (evidence)" and proceed. |

## Wait and watch (nothing ready, held work remains)

Applies when the plan above leaves this session idle while the requested task (or the rest of its epic/spec) is held or serialized behind a peer — at the start, or after the parallel tasks you took are done. Watch the holders and take the task once it is released, rather than ending the turn. Reason: ending hands the re-check back to the user, who then has to notice the peer finished and re-issue "진행해줘".

1. **Check the stop conditions (step 5) first**; if one already holds, report instead of arming. Record the watch start time in the plan or `_workspace/<task>/` so a re-invoked session can tell when the limit has passed.
2. **Fingerprint only release signals** — not the holder's live edits, which change every few minutes while it works: its PR state (`gh pr view <n> --json state`), whether its branch exists on `origin` and is in `git branch -r --merged origin/main`, whether its worktree is still in `worktree list`, and `origin/main`'s head.
3. **Arm a watcher that exits on change.** Claude Code: a `Bash` call with `run_in_background` and a `timeout` above the loop length, running an `until` loop that does `git fetch -q` and recomputes the fingerprint every 3–5 minutes (`|| true` on network calls) and exits when it differs or after ~25 minutes — exit re-invokes you. Codex/Pi or any CLI without a background re-invoke: run the same loop in the foreground with a bounded timeout. A watcher that cannot be armed is reported as such and the session ends with the one-line report above.
4. **On every wake, re-run this whole survey** (with `ListAgents` where available); a fingerprint change is a hint, not a release. **Nothing is released while the re-survey still finds a live peer holding the task you would take** (Held tasks) — a merge of one of its PRs does not end its hold on the rest. Then decide by what you were waiting on:
   - **The requested task itself, or the unstarted tasks of an epic/spec a peer holds**: the task's own merge into `origin/main` means it is **done**, not free — report that and stop. It (or an epic/spec hold) is **released** only when its author is shown to have stopped (Separate your own work) and nothing carries it: no uncommitted edits, no unpushed commits, no open PR, no unmerged branch or worktree naming it.
   - **A different task, overlapping files, or a dependency**: released when the holder's change is merged into `origin/main`; rebase onto it, then proceed.
   - Anything else — a PR closed without merge, a worktree removed while its branch or PR remains, a stopped author who left edits or commits behind — is **not** a release: go to step 5.
   **Released → proceed** through the normal path for that task (orchestrate gate, spec, `branch-workflow`) and say in one line what released it. **Still held → re-arm** without a chat message; report only a change in what you wait on.
5. **Stop watching and report** — first terminating any armed watcher (`TaskStop` on Claude Code) and saying so — when: the user sends a message after the watch is armed (their message wins; a wake that arrives after a user message never proceeds); a stopped holder left uncommitted edits or unpushed commits on the task (stale-unknown, root §3 — never take them over; ask the user); the waited-on item ended without a release (merged-as-done, closed unmerged, spec revised); or about 4 hours pass since the recorded start. Name what was waited on and the last observed state.

Watching never edits, messages a busy peer, or claims the task early; it only re-reads state. Each wake costs one survey, so keep the interval at minutes, not seconds.

Record the survey result (items found, classification, chosen plan) in the user-visible plan or `_workspace/<task>/`, and repeat the newest-file and `status` checks after any long pause before writing — in-flight state changes while you plan. A source the survey could not run (no `gh`, no `ListAgents`) is reported as unverified for that source, not as "none".
