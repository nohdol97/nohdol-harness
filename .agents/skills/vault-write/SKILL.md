---
name: vault-write
description: "Write or revise curated knowledge notes in the study vault on request, recording what was written in index.md, log.md, and hot.md and enforcing the note schema. Use for vault에 작성, vault에 기록, 노트로 정리, 지식으로 저장. Not for project docs or specs (doc-writer), session handoff notes (carryover), or reading the vault as design input (AGENTS.md §7 clause 8 — that contract is read-only). Re-run: vault-write, vault note, knowledge note, vault에 작성, vault 기록, 노트 정리."
---

# vault-write — authoring into the study vault

## Why

REGISTRY.md registers the study vault as a **read-only design input** (root
AGENTS.md §7 clause 8). Nothing in this harness describes writing into it, so a
root session asked to "vault에 정리해줘" grades the note against whichever file it
read last. A measured baseline (2026-07-28, see Phase 2) settles what actually
breaks: the three record surfaces held, and the **note contract** did not — the
new note copied its neighbors' pre-contract frontmatter and inherited their
defects. That is the degradation this skill exists to stop, and it is invisible,
because a note shaped like its neighbors looks correct.

The rules that prevent this already exist and are already maintained, in the
`nohdol-study` harness. This skill does not restate them. It resolves that
harness from the path REGISTRY.md already records, reads its note contract at
run time, and applies it from here. **One original, no second copy to drift**
(ADR 034).

## Scope boundary against the read contract

REGISTRY.md's 지식 소스 「사용 계약」 caps *consultation* to the recorded entry
points, because a full-root grep can lift secrets into a report (§3). Authoring
needs a wider surface, and this skill takes exactly these five paths and no more:

| Touched | Never touched |
|---|---|
| `vault/wiki/**`, `vault/raw/**` | root dotfiles (`.env`), `.obsidian/` |
| `vault/index.md`, `vault/log.md`, `vault/hot.md` | `.ocr*/`, `.smtcmp_*` vector and cache trees |

Search with `rg` scoped to `vault/wiki/`. Never sweep the vault root.

**§3 still binds and cannot be relaxed**: no credential, token, private key, or
secret-bearing value enters a note, and none enters `index.md`/`log.md`/`hot.md`
either. No other outbound boundary applies — the vault is the user's personal
knowledge root, not a publication (decided with the user, 2026-07-28).

## Phase 0 — preflight (stop conditions before any write)

1. **Resolve the study harness from REGISTRY.md.** Read the 지식 소스 section
   and take the recorded vault path. Do not copy that path into this file: it is
   installation data (ADR 005), and a second copy here is one more thing to
   drift. The harness root is that path's **parent**, because the recorded path
   is a symlink living inside the study repository. Confirm the derivation before
   trusting it: `<parent>/AGENTS.md` must exist and identify itself as the study
   harness. If it does not, stop and ask — a wrong root silently reads the wrong
   rules.

2. **Confirm the vault actually reads.** The knowledge root is Google
   Drive-synced, so a live symlink does not mean live bytes, and `mount` cannot
   settle it. Read `vault/index.md`. On failure, report the one line and stop —
   do not write a note whose index update cannot land.

3. **Confirm the rule originals are present:**

   ```
   <study-root>/.agents/skills/note-writer/references/note-schema.md
   <study-root>/.agents/skills/note-writer/references/index-policy.md
   <study-root>/.agents/skills/note-writer/references/evidence-check.md
   ```

   If any is missing, **stop** and say which. Do not write the note from memory
   of the schema and do not reconstruct the reference here. A note written to a
   guessed contract is worse than no note: it looks conforming, so nothing
   later flags it.

4. **Read all three before drafting**, plus `<study-root>/AGENTS.md` §5. They are
   the contract; this file is only the procedure. §5 is not optional context: it
   carries the guardrails this procedure cannot restate correctly from memory —
   no credential enters the vault, no vault material goes to an additional
   external service without the user's approval, legacy notes outside the curated
   layer are not normalized, and **destructive knowledge changes, link
   replacement, and migrations require explicit user confirmation.**

## Phase 1 — decide what the note is

1. Search `vault/wiki/` for a note that already carries this concept or claim
   (`rg` on the term, then on likely synonyms). Improving an existing note beats
   adding a near-duplicate; wording differences alone do not justify a new file.

   **Rewriting is destructive here and asks first.** Adding sections, links, or a
   frontmatter field to an existing note is ordinary revision, and so is bumping
   `updated`/`checked` — Phase 4 requires that. Replacing or deleting **prose the
   user already wrote** is not ordinary: the knowledge root has no
   version control (the study REGISTRY records `vault Git: absent`) and Drive
   version history is the only recovery, so an overwrite is effectively final.
   Name what would be removed and get confirmation before removing it — this is
   the data-loss confirmation root §3 never lets a skill skip.
2. Keep one note to one central concept or claim. A session that produced three
   separable claims produces three notes, not one topic dump.
3. If a source must be retained, copy it **unchanged** under `vault/raw/` first.
   Never edit source material so a conclusion fits.
4. Apply `evidence-check.md` to every material claim. Model output — including
   this session's own reasoning — is not a source. Agreement between models is
   not corroboration.

## Phase 2 — write the note

Write under `vault/wiki/<Title>.md` using `note-schema.md` verbatim: flat YAML
frontmatter (`type`, `status`, `created`, `updated`, `related`, `sources`,
`verification`, `checked`), H1 matching the filename exactly, and the body
sections that keep sourced fact, synthesis, inference, hypothesis, and open
questions distinguishable.

**The contract is the reference file, never the neighboring notes.** This is the
one place a baseline run actually failed (2026-07-28, sandbox copy of the vault,
subagent given the same task without this skill). It updated `index.md`,
`log.md`, and `hot.md` correctly and unprompted, and declined to put the atomic
note in index's 주제 list on its own. Two of those files state their own rules in
their bodies; `hot.md` does not and was still updated. So Phase 3's value is
**guarantee, not rescue** — Phase 4 verifies the landing instead of leaving it to
luck. What it got wrong
was the note itself, and every error was an imitation of the sibling notes it
had just read:

- **`checked` omitted** — absent from the neighbors, though the claim was
  version-specific and the schema requires it exactly there.
- **`tags:` added** — a field the neighbors carry and the schema excludes.
- **`status: evergreen` on a first capture** — copied from neighbors; the schema
  reserves `evergreen` for stable maintained knowledge and gives a first capture
  `seed`.
- **`sources` filled with prose** describing a command run, where the schema
  admits only exact URLs or `raw/` paths.

The vault holds notes that predate the curated contract, so the nearest example
is often the wrong one. Read the schema and grade against it; when a neighbor
disagrees with the reference, the reference wins and the neighbor stays untouched
(migrating it is a separate request).

Two further failure modes, both from the schema reference:

- **`/` in a title cannot be a filename** — the filesystem reads it as a path
  separator. Use a space in the filename, H1, and every `[[wikilink]]`, and state
  the real spelling in the first body line.
- **`verification` summarizes the weakest material claim, not the strongest.**
  One unresolved central claim caps the whole note.

Add `[[wikilinks]]` in both directions. **At least one inbound link from an
existing note is required**, or an explicit statement of why none fits: the
vault's own `log.md` records a note that sat unreachable because every link
pointed outward, and the correction it needed was already sitting in a note
nobody had connected it to. Index and log entries are a record, not reachability
— they age out of 「최근 갱신」 and sink down `log.md`, while a wiki-to-wiki link
does not.

Record uncertainty, contradictions, and gaps as explicit callouts rather than
smoothing them into confident prose. Leaving a required detail **blank and
labeled** beats writing a plausible-looking one — a fabricated command or field
name reads as verified and is the failure most notes are written to prevent.

## Phase 3 — record what was written

A note nobody can reach is not knowledge. All three surfaces update, in this
order, in the same turn as the note.

**Before touching any of them, check for sync conflict copies.** The knowledge
root has a second writer (Google Drive), and a conflict duplicates a file whose
existing entries are meant to be preserved rather than rewritten. Modification
times can be rewritten by the sync client, so freshness read from them is a
hint, not proof (study AGENTS.md §5).

### 3a. `index.md` — mandatory, one line

`index.md` answers "where do I start", not "what exists" (`index-policy.md`).
Two distinct edits, and most writes need only the first:

- **「최근 갱신」 — always.** Add one line at the top naming the note and, in a
  sentence, what it now settles. Keep roughly the five most recent and drop the
  overflow; `log.md` is the record, and a hand-trimmed second copy only drifts
  from it.
- **「주제」 — only when a hub exists or is now due.** A 주제 line always names a
  **hub note**, never an atomic one. A topic being new is not the trigger; the
  trigger is the cluster reaching **more than two or three notes** without a
  hub, and then you write the hub (`type: topic`) rather than adding index
  lines. **A first note in a new topic therefore gets no 주제 line at all** —
  only its 「최근 갱신」 line. Creating a hub for a single note builds a map of
  one place, and the index grows by notes again, which is the one thing the
  policy exists to prevent.

  (The 「최근 갱신」 line above does name the atomic note — that is the
  sanctioned place for it, and dropping that line to honor the 주제 prohibition
  would delete the record this phase exists to make.)

A dangling `[[wikilink]]` in the entry point is reported, not left: write the
note, mark the entry as having none, or remove the line.

### 3b. `log.md` — mandatory, one row, append-only

Add one row at the **top** of the table (`| 날짜 | 변경 | 관련 노트 |`), newest
first. Say what changed and what it corrected or established, in enough detail
that a later session can reconstruct the decision. **Never alter or delete a row
already written** — newest-first is a reading order, not permission to edit.

### 3c. `hot.md` — refresh, roughly ≤500 tokens

Carry only current focus, recently learned durable points, open questions, and
next actions. It is a cache: on conflict the note and its source win, never
`hot.md`.

## Phase 4 — verify before reporting

1. Frontmatter parses and carries **exactly** the schema's eight fields — no
   extra `tags`, no plugin metadata, `checked` present. `created` unchanged on a
   revision, `updated` moved only if meaning changed, `status` graded against the
   schema's definitions rather than against the neighbors.
2. Every `[[wikilink]]` resolves to a real file; every `sources` entry is a real
   URL or an existing `raw/` path.
3. Every material claim maps to inspected evidence or is labeled `unverified`,
   inference, hypothesis, or contested.
4. `index.md` gained its line, `log.md` gained its row, no prior row changed,
   no **pre-existing** `raw/` file changed (Phase 1 may have added one).
5. **If the note carries a diagram, run the study harness's checker** — a broken
   Mermaid block renders as an error while the source still looks complete, so
   no other step in this procedure catches it:

   ```sh
   python3 <study-root>/.agents/skills/diagram/scripts/check.py "<vault>/wiki/NOTE.md"
   ```

6. Optionally confirm the index has not started listing rather than orienting:

   ```sh
   python3 <study-root>/.agents/skills/vault-gardening/scripts/garden.py --vault <vault>
   ```

   **Neither script is checked in Phase 0, on purpose** — they are conditional
   and the note is already written by the time they run, so a missing one must
   not retroactively become a stop. If either path is absent or exits non-zero,
   say so in the report as an unverified item and finish. The three references
   are the opposite case: they gate the write, so they gate at Phase 0.

   `garden.py` counts distinct wikilink targets in `index.md` against a default
   budget of 15. That is a smell threshold, not a law, and the capped 「최근 갱신」
   lines legitimately count toward it — what the number should never absorb is
   atomic notes accumulating in the 주제 list.

Report to the user in Korean (§15): the note path, the index line and log row
added, the verification status assigned and why, and anything left unverified.

## Quality gates

- One note, one central concept or claim.
- The title is specific enough to link without surrounding context.
- At least one existing note links **in**, or the report says why none does.
- Frontmatter carries the schema's eight fields and nothing else.
- No invented source, quote, relationship, or confidence level.
- `index.md` records this write; `log.md` records it permanently; neither lost a
  prior entry.
- No atomic note was added to `index.md`'s 주제 list.
- No secret entered any of the five touched paths (§3).
- Legacy notes outside the curated layer were not **normalized or migrated**.
  Adding a backlink to one is allowed and often necessary — 214 of 231 notes
  carry the pre-contract marker, so the natural donor usually is a legacy note.
  What the ban forbids is reshaping it to the contract while passing through
  (study `AGENTS.md` §5 scopes it to installation and normalization).

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Format | Graded against whichever note was read last — measured baseline: extra `tags`, missing `checked`, `evergreen` on a first capture, prose in `sources` | The study harness's note contract, read at run time |
| Discoverability | Index/log/hot did survive the baseline, but nothing guaranteed it — two of the three state their rules in their own bodies, `hot.md` does not | Index line + permanent log row + hot refresh, verified in Phase 4 |
| Rule drift | Root copy diverges from the study original | One original in `nohdol-study`, no copy here (ADR 034) |
| Evidence | Fluent prose hides what was never checked | Verification status set by the weakest claim |
