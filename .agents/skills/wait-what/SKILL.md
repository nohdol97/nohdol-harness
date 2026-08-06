---
name: wait-what
description: "Re-explain the previous answer in plain language when it did not land, re-derived from the artifact rather than paraphrased. Slash-invoked only with /wait-what; never auto-route. Use for 무슨 말이야, 이해가 안 돼, 쉽게 다시, 다시 설명해줘. Not for producing new work, and not for re-checking whether a claim is true (team-review). Re-run: wait-what, re-explain, plain language, 쉽게 다시, 이해가 안 돼, 다시 설명."
---

# wait-what — re-pitch what did not land

## Why this skill

Root AGENTS.md §13 makes **user comprehension part of completion**, and ADR 041 deliberately removed the gate that used to enforce it — the pre-PR comprehension quiz — leaving comprehension as report content with nothing holding it. That decision removed the *push* side only. What was never built is the **pull** side: a way for the user to say "that did not land" and get a different explanation rather than the same one again.

Without it the default failure is a louder repeat: the model restates the same abstraction with more words, because it is re-reading its own summary instead of the thing the summary was about. Reason the skill is slash-only: an auto-trigger on confusion words would fire on ordinary questions and turn every follow-up into a re-explanation round.

## Procedure

1. **Find what did not land.** If the user named it, take that. Otherwise take the last substantive claim or decision you delivered, and say which one you picked in the first line — a re-pitch of the wrong thing wastes the round.

2. **Go back to the artifact, not to your own words.** Re-open the diff, file, command output, or document the explanation was about, and re-derive the point from it. Re-reading your previous message reproduces the same framing that already failed; the source has details the summary dropped, and those details are usually what makes it concrete.

3. **Re-pitch, in Korean (§15), by these levers:**
   - **One idea per sentence, short sentences.** Split anything with a subordinate clause carrying a second claim.
   - **Concrete before abstract.** Lead with a specific instance — this file, this line, this input producing this output — and let the general statement follow it. The first version almost certainly did the reverse.
   - **Name the thing the same way every time.** Pick one term per concept and keep it; synonyms read as new concepts.
   - **Gloss every term that is not plain Korean or a literal identifier** the first time it appears, in the sentence itself.
   - **Say what it is *not*** when a near neighbour is the likely confusion (`fetch` vs reading the remote-tracking ref, a gate vs a report line). Contrast fixes more misreads than definition.
   - **Keep code, commands, paths, and error text verbatim** — those are the anchor, and rewording them breaks the link to what the user will actually run or read.

4. **Do not smuggle in new claims.** This is a re-explanation of what you already said, not a second attempt at the work. If re-deriving from the artifact shows the original explanation was **wrong**, say that plainly as a correction and give the corrected version — do not quietly re-pitch a different claim as though it were the same one. If the original was **unverified**, say it is unverified; simplifying an uncertain claim makes it sound more settled than it is (§13-2).

5. **End with the fork, not with a summary.** §13's comprehension requirement is about decisions: state what was chosen versus what else was available, and why this one. If the answer contained no decision, say so instead of manufacturing one.

## Boundaries

- **Not a verification round.** "I don't understand this" is not "prove this is true" — if the user wants the claim checked, that is `team-review`.
- **Not a work round.** No edits, no new implementation. If the re-pitch reveals work to do, name it and stop; the request re-enters `orchestrate`.
- **Not a translator for the whole session.** Re-pitch the one thing that did not land, not everything said since.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Comprehension recovery | The user re-asks, and the model restates its own summary in more words — same framing, same miss | Re-derived from the artifact, so the second version carries details the first dropped |
| §13 comprehension | Push side removed by ADR 041, pull side absent — a thin report has no remedy the user can invoke | The user has one move that reliably produces a different explanation |
| Correction honesty | A re-explanation can quietly replace the original claim | A wrong or unverified original is called out as such rather than smoothed over |
