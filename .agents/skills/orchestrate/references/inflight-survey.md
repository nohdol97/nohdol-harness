# In-flight work survey (orchestrate 0-2 item 7)

Run before the first write on a project under **every** Phase 0-1 verdict (direct included), before the spec is written (0-2 item 5) or `branch-workflow` creates a worktree, and again on every continuation or resume ("진행해줘", "계속", "이어서", work-tracker/carryover re-entry). Applies to every registered project and to the root harness itself. The survey is read-only: it never edits, stashes, resets, or removes anything it finds.

## Why

Several sessions (Claude, Codex, Pi, autoloop drivers) can work the same repository at once, and the user's belief about what another session is doing is not evidence. Observed 2026-11-21: the user believed a peer session was running PKI Phase 0; measurement showed it was implementing V01 T09/T11/T14 with uncommitted edits made within the last minute. A new session started on "the next phase" would have written into the same files. Worktree isolation separates working trees, not overlapping file edits, shared documents, or duplicated tasks.

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

On Claude Code also call `ListAgents` — it lists peer sessions on this machine with busy/idle state (measured 2026-11-21). It shows that a session exists, not what it edits; tie it to work through the worktree, team-log, and process evidence. CLI sessions themselves run from the harness root, so `ps` only catches the commands and servers they start inside a worktree; a match whose path is no longer in `worktree list` is an orphaned process, not live work. Other CLIs: rely on the git and team-log evidence and say `ListAgents` was unavailable.

Call `/usr/bin/find` by path: a command-rewriting proxy (rtk) rejects `-prune`/`-mmin` and returns nothing, which reads as "not live". Only changed files are timed (the `awk` drops a rename's old-path record, which `-z` emits without a status prefix) — a fresh checkout or pull rewrites every tracked file and would otherwise look live.

**Live** = changed files written in the last hour, local commits from the last hour, a command running in the worktree, or a team-log event in the last few hours. Older dirty worktrees are **stale-unknown**: still someone's unsaved state (root §3), never yours to reuse or clean without confirmation, and they count as overlaps for planning.

## Separate your own work first

Exclude from the overlap set: worktrees and files this session created or edited, and — on a resume — the worktree the handoff note or progress log names, **once its author is shown to have stopped**: the author session is gone or idle in `ListAgents` where available, no `ps` match in it, no file written after the note's time, and no team-log event after the note. If that cannot be shown, treat it as a peer's. Reason: a carryover hands over a worktree that is still fresh, and without this step the survey would make a resume skip its own task.

## Plan against each in-flight item

| Overlap found | Plan |
|---|---|
| Same task or same worktree | Do not start it. Default: run the other ready tasks (dependencies done) that overlap nothing in flight — in parallel where they do not overlap each other, sequentially on corporate Claude/Codex hosts (root §11) — and report the skipped task and its holder. Hand off instead only when no such task exists: ask the owning session via `SendMessage` (it interrupts a busy peer — only when the answer changes the plan) or tell the user who owns it. |
| Different task, overlapping files (compare your task's expected files with their `status --porcelain -uall`, `git diff --name-only origin/main...HEAD` in their worktree, and open PR file lists) | Serialize: start after their merge, or choose a non-overlapping task now. Note the rebase point in the plan. |
| Shared documents (ADRs, README, lockfile, shared config) | One session owns each such file; the other records its needed change as a follow-up for that owner. **Append-only records are not owned**: change-history rows, MOC/index rows, and ops-log lines that a rule requires in the same commit (root §5·§6) are added by each session for its own change, staged hunk-wise as metaskill describes. |
| Semantic dependency (their result can invalidate your premise) | Order your work after it, or proceed behind the existing adapter/contract and record the dependency as a re-check item. |
| Nothing in flight | Record "in-flight: none (evidence)" and proceed. |

Record the survey result (items found, classification, chosen plan) in the user-visible plan or `_workspace/<task>/`, and repeat the newest-file and `status` checks after any long pause before writing — in-flight state changes while you plan. A source the survey could not run (no `gh`, no `ListAgents`) is reported as unverified for that source, not as "none".
