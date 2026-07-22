---
name: carryover
description: "Save selected work from the current session to a local _workspace carryover note (Markdown) so a later same-machine session can resume it, and load an existing note to continue. Slash-invoked only (/carryover) — the user manually triggers save or resume; this skill is intentionally NOT part of harness auto-routing. Save mode: enumerate this session's work (changed files, decisions, done/open items, blockers), let the user pick which to keep, write a resume-ready template to _workspace/carryover/backlog/YYYY-MM-DD-<topic>.md. Resume mode: scan backlog/ (queued) + progress/ (in-flight), list notes, load the chosen one (moving it backlog→progress) and continue, deleting it on completion. Do NOT use for cross-session/cross-machine epics or multi-PR work tracked in git (→ work-tracker: GitHub Issues/backlog.md) — carryover is local, gitignored, lightweight, same-machine only. Re-run keywords - carryover, 이월 노트, 세션 이월, 카리오버, 이어받기."
---

# carryover — session carryover notes

## Why this skill

Session context and `_workspace/` do not automatically carry over across sessions. Yet "the few things from this session I want to pick up next time" — not big enough to open a GitHub issue — get lost every time. This skill fills exactly that gap: the user **personally picks the work to keep**, it is written in a resume-ready format under local `_workspace/carryover/`, and the next session picks a note and takes over.

**Boundary with work-tracker (important — coexistence, not replacement)**:

| | work-tracker | **carryover (this skill)** |
|---|---|---|
| Storage | GitHub Issues / `docs/backlog.md` (git-tracked, cross-machine) | `_workspace/carryover/{backlog,progress}/*.md` (gitignored, **same-machine local**) |
| Target | Multi-PR, multi-day epics, formal | This-session→next-session **lightweight handoff memo** |
| Invocation | Auto-routing + slash | **Slash-only**, no auto-routing |

→ If formal tracking is needed, send it to work-tracker. carryover is a local scratch handoff. Reason: mixing the two either creates an issue graveyard (everything into GitHub) or leaves important cross-machine work stranded locally and lost.

**This skill is invoked only via slash (`/carryover`)** — it is not registered in harness routing (CLAUDE.md anchor, §7). Reason: it is a tool that must act only at the moment the user explicitly decides "I will save now / I will resume now."

## Mode dispatch (first decision)

Determine the mode from the invocation arguments.

- If the arguments contain a **resume signal** (`재개`·`resume`·`이어서`·`이어받`·`불러와`·`load`) → **resume mode**.
- Otherwise (including no arguments) → **save mode**. However, on entering save mode, if existing notes are present in `backlog/`·`progress/` (or as top-level unmigrated flat notes), notify in one line: "기존 이월 노트 N개가 있습니다(재개하려면 `/carryover 재개`)".

**Directory structure** (two-way split — so the resume list is not blurred by completed/in-flight notes):
- `_workspace/carryover/backlog/` — queued (save mode writes here)
- `_workspace/carryover/progress/` — in flight (moved from backlog on resume)
- Completed notes are **deleted** (no done/ archive — this is gitignored scratch, so accumulation is cruft; persistent records are work-tracker's job).

## Save mode

Keep only the work the user picks from this session as a local note.

1. **Collect candidates**: enumerate this session's work as candidate items.
   - Check changed/uncommitted files with `git status --short` and `git diff --stat` (in the subproject's repository if the target is a subproject).
   - Extract the **decisions** made in conversation, **what was completed**, **in-progress / next actions**, and **blockers**.
   - Express each candidate as a one-line gist (e.g. `sona_app 로그인 리팩토링 — AuthProvider 분리 완료, 테스트 미작성`).
   - **If there is nothing worth carrying over** (no changes, decisions, or open items), do not save; notify "이월할 작업이 없습니다" and stop — an empty note is debt.

2. **User selection** (the core — the user must choose):
   - If there are **4 or fewer** candidates, present them with `AskUserQuestion` (multiSelect: true) and let the user pick.
   - If there are **5 or more**, present a numbered list in chat and have the user answer with the numbers to keep (or "전부"/all) — AskUserQuestion caps at 4 options, so this method is accurate for long lists.
   - If nothing is selected, do not save and stop (an empty note is debt).

3. **Fix the topic**: build a short slug from the common topic of the selected items (confirm once with the user, or proceed if self-evident). If several unrelated topics are mixed, ask the user whether to split into per-topic files.

4. **Write the file**: write to `_workspace/carryover/backlog/YYYY-MM-DD-<topic-slug>.md` using the template below. Get the date with `date +%F` (no guessing). Create `backlog/` if missing.
   - If a same-day same-topic file already exists, do not overwrite — append a session-delimited section or add `-2` to the slug (prevents losing previously carried-over content).

5. **Report**: tell the user the written file path, and **present the next session's start prompt as a copy-paste code block** (same format as wrapup step 5 — same experience in standalone invocation): `/carryover 재개 — <주제슬러그> 노트. 첫 행동: <first item of "In progress · Next">`. Take the "first action" verbatim from the note (do not invent it).

### Note template (skeleton for resuming)

```markdown
# Carryover: <title>

- Date: YYYY-MM-DD
- Target project/repo: <name or path>
- One-line summary: <what this note is about — this line appears in the resume-mode list>

## Done
- …

## In progress · Next
- …

## Blockers · Unresolved
- …

## References (file:line, commands, paths, issues/PRs)
- `path/to/file.ts:120` — …
- Command run: `…`

## How to resume
- Where and how to pick up. Name the skill to re-enter
  (orchestrate gate re-entry for continued implementation, team-review for review, etc.).
```

**The "One-line summary" must always be filled** — the resume-mode list distinguishes notes by this line (same principle as skill description triggers: list quality hinges on this line).

## Resume mode

Pick an existing carryover note and take over.

1. **Scan**: list `*.md` in `backlog/` and `progress/`. Build a list from each note's filename, date, and "One-line summary", tagging **state (queued / in flight)** (in flight = progress goes on top). If there are no notes, notify "이월 노트가 없습니다" and stop.
   - **Legacy migration (one-time)**: if flat notes (`*.md`) remain directly under `_workspace/carryover/` (saved before the two-way split), move them to `backlog/` and list them together.

2. **Select**: if 4 or fewer notes, use `AskUserQuestion`; if more, use a numbered list, letting the user pick one (or several).

3. **Load, digest + move**: read the chosen note and report the situation (done / next / blockers / references) **digested into Korean** (not pasted verbatim — summarized so it is easy to continue now). If the chosen note is in `backlog/`, **move it to `progress/`** — this session has picked it up, so keep the next scan's "queued" list clean. If already in `progress/`, leave it.

4. **Re-entry**: continue along the path the note's "How to resume" points to — if it is new implementation or behavior change, **step through the orchestrate gate again** (§7 item 3; continuation also re-enters the gate). The gate **also rules on the implementation owner** (3+ files → dispatch implementer; high risk → team ruling — orchestrate implementation-owner rule): a session heading straight into direct implementation right after resume, without a gate ruling, is a bypass signal (real case 2026-07-21). Review → team-review; documents → doc-writer. carryover itself performs no work — it only hands over the re-entry point.

5. **Cleanup (optional)**: if the work is finished and the note is no longer needed, **delete** the note (in `progress/`) after confirming with the user — completion means deletion, not a move to done/ (see structure above). If unfinished, leave it in `progress/` for the next session to take over.

## Preservation convention (it's `_workspace/` — why isn't it cleaned up?)

`_workspace/` is session output and in principle a cleanup target (root AGENTS.md §4), but `_workspace/carryover/` (including `backlog/`·`progress/`) is **on the cleanup-exclusion list** (same treatment as harness-updates.md, harness-ops-log.md, and review markers) — being taken over across sessions is its reason to exist. It remains gitignored, so takeover works **on the same machine only**. If cross-machine carryover is needed, this is the wrong tool → send it to work-tracker (git-tracked).

## Cautions

- **Extension of the secrets/`<private>` ban**: do not write credentials into notes (§3). Content that would be wrapped in `<private>` (sensitive paths, internal URLs, etc.) is excluded from the note or wrapped in the tag — though `_workspace/` is local scratch, not a publication, so the critical filter is at export time (promotion to work-tracker, etc.).
- **No done/pass claims**: a note is only a record of "what was done"; completion verdicts come only from §13 fresh evidence (test output). If verification is incomplete, say so under "Next".
- **No destructive operations**: this skill only writes, reads, moves (backlog→progress), and (after confirmation) deletes note files. It does not touch code or infrastructure.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Session handoff | Work not worth an issue is lost every session | Only chosen work carried over as a local note |
| Selectivity | Keep everything (graveyard) or lose everything | The user selects only what to keep |
| Resume | Manually reconstruct what the last session did | Pick a note and get the re-entry point instantly |
| work-tracker boundary | Even lightweight memos become GitHub issues → graveyard | Lightweight = local carryover, formal = work-tracker |
