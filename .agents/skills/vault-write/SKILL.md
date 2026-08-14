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

Root AGENTS.md §7 clause 8 caps *consultation* to the entry points recorded in
REGISTRY.md, because a full-root grep can lift secrets into a report (§3).
REGISTRY.md owns only the install-site path and entry points. Authoring needs a
wider surface, and this skill takes exactly these five paths and no more:

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

4. **Read all three before drafting**, plus `<study-root>/AGENTS.md` **§2 through
   §5**. They are the contract; this file is only the procedure. Read the whole
   span rather than picking sections: several load-bearing rules live there and
   **nowhere in the three references** — what `hot.md` is for and how large it
   may get (§2-§3, and `hot.md` carries no blockquote of its own), and the ban on
   inventing a source, quote, relationship, or certainty level (§4). Nothing else
   would put those in front of you. §5 is not optional context: it
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

Write under `vault/wiki/<Title>.md` using `note-schema.md` verbatim — its
frontmatter field set, its H1 rule, and its body sections, taken from the file
you read in Phase 0 rather than from anything written here.

**The contract is the reference file, never the neighboring notes.** This is the
one place a baseline run actually failed (2026-07-28, sandbox copy of the vault,
subagent given the same task without this skill). It updated `index.md`,
`log.md`, and `hot.md` correctly and unprompted, and declined to put the atomic
note in index's 주제 list on its own. Two of those files state their own rules in
their bodies; `hot.md` does not and was still updated. So Phase 3's value is
**guarantee, not rescue** — Phase 4 verifies the landing instead of leaving it to
luck. What it got wrong was the note itself, and every error was an imitation of
the sibling notes it had just read:

- **`checked` omitted** — absent from the neighbors, though the claim was
  version-specific and the schema requires it exactly there.
- **`tags:` added** — a field the neighbors carry and the schema excludes.
- **`status: evergreen` on a first capture** — copied from neighbors; the schema
  grades a first capture otherwise.
- **`sources` filled with prose** describing a command run, which is not among
  the forms the schema admits.

The vault holds notes that predate the curated contract, so the nearest example
is often the wrong one. Read the schema and grade against it; when a neighbor
disagrees with the reference, the reference wins and the neighbor stays untouched
(migrating it is a separate request).

Two traps in the schema's own field rules are worth re-reading before drafting
rather than recalling: the one about a `/` in a title, and the one about how the
note-level `verification` value is graded.

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

### 3a. `index.md` — mandatory, one 「최근 갱신」 line

**Every write adds a 「최근 갱신」 line.** That is this skill's obligation and the
reason it exists; the rest of what goes in `index.md` — the recent-change cap,
when a topic earns a 주제 line, what a 주제 line may name, how a dangling entry
is handled — is **`index-policy.md`'s to state, and it is already in context from
Phase 0.** Apply it from there. Do not restate it here or reason from memory of
it: a paraphrase is how this file once introduced a threshold error the original
never had (2026-07-28 comprehension quiz), which is the drift ADR 034 exists to
prevent.

One point the policy does not cover, because it only arises when writing:
**the 주제 restriction never cancels the 「최근 갱신」 line.** That line names the
atomic note and is its sanctioned place. Dropping it to honor the 주제 rule
deletes the record this phase exists to make.

### 3b. `log.md` — mandatory, one row, append-only

Add one row at the **top** of the table (`| 날짜 | 변경 | 관련 노트 |`), newest
first. Say what changed and what it corrected or established, in enough detail
that a later session can reconstruct the decision. **Never alter or delete a row
already written** — newest-first is a reading order, not permission to edit.

### 3c. `hot.md` — refresh

Refresh it to what study `AGENTS.md` §2-§3 specify, size included.

## Phase 4 — verify before reporting

1. Frontmatter parses and carries **exactly the field set the schema lists** —
   count and names from the reference you read in Phase 0, never from this file
   or from a neighboring note. No extra `tags`, no plugin metadata. Every field's
   value is graded against the schema's own field rules, `status` and the date
   fields included, rather than against the neighbors.
2. Every `[[wikilink]]` resolves to a real file, and every `sources` entry is in
   one of the forms the schema admits and actually resolves.
3. Every material claim carries the status `evidence-check.md` assigns it, and
   the note-level value follows `note-schema.md`'s rule for combining them —
   the per-claim statuses and the aggregation rule live in different files.
4. `index.md` gained its line, `log.md` gained its row with no prior row changed,
   `hot.md` was refreshed, and no **pre-existing** `raw/` file changed (Phase 1
   may have added one). All three landings are checked, not two — an unverified
   `hot.md` is the one this procedure would otherwise let slide.
5. **No inline code span or bold marker straddles a line break** — a
   `code span` or **bold** marker whose opening and closing delimiter sit on
   different source lines is legal CommonMark (the line break normalizes to a
   space) but renders unreliably in Obsidian, breaking formatting from that
   point on. Neither the diagram checker nor `vault-gardening` catches this. A
   bare open/close count match is not enough — two unrelated delimiters can
   still pair across lines and still total even, so scan sequentially: which
   opening delimiter pairs with which closing one, and whether a line break
   falls between them. Reflow the sentence onto one line, even if long, rather
   than wrapping mid-span.
6. **If the note carries a diagram, run the study harness's checker** — a broken
   Mermaid block renders as an error while the source still looks complete, so
   no other step in this procedure catches it:

   ```sh
   python3 <study-root>/.agents/skills/diagram/scripts/check.py "<vault>/wiki/NOTE.md"
   ```

7. Optionally confirm the index has not started listing rather than orienting:

   ```sh
   python3 <study-root>/.agents/skills/vault-gardening/scripts/garden.py --vault <vault>
   ```

   **Neither script is checked in Phase 0, on purpose** — they are conditional
   and the note is already written by the time they run, so a missing one must
   not retroactively become a stop. If either path is absent or exits non-zero,
   say so in the report as an unverified item and finish. The three references
   are the opposite case: they gate the write, so they gate at Phase 0.

   `index-policy.md` documents what `garden.py` measures and how to read the
   number it prints; take the interpretation from there.

Report to the user in Korean (§15): the note path, the index line and log row
added, the verification status assigned and why, and anything left unverified.

## Quality gates

- One note, one central concept or claim.
- The title is specific enough to link without surrounding context.
- At least one existing note links **in**, or the report says why none does.
- Frontmatter carries the schema's field set and nothing else, counted from the
  reference rather than from this file.
- Nothing invented, per study `AGENTS.md` §4's note contract.
- `index.md` records this write; `log.md` records it permanently; neither lost a
  prior entry.
- `index.md` conforms to `index-policy.md` after the write.
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
| Evidence | Fluent prose hides what was never checked | Every claim graded, and the note graded by the schema's own aggregation rule |
