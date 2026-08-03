---
name: doc-writer
description: "Write specs, work reports, READMEs, runbooks, and PR bodies from fixed templates; also use when SDD requires a spec. Triggers: 문서 작성, 스펙, 리포트, README, PR 본문. Not for ADRs/change-history rows or team-mode architect drafting. Re-run: doc-writer, document, spec, PR, 문서 작성, 스펙, PR 본문."
---

# doc-writer — consistent-format document writing

## Why this skill

When every document has a different format, the reading cost is paid anew each time — where the completion criteria are, where the decision rationale is, must be re-found per document, and eventually nobody reads them. The goal of this skill is that **the same kind of document always comes out in the same format**. With a fixed format, both humans and agents jump straight to the section they want, and cross-document comparison, search, and reuse become possible.

## Procedure

1. **Determine the type**: map the request to the table below. If ambiguous, ask the user for the purpose (who reads this document, and when).
2. **Load the template**: read only that type's section from `references/templates.md`.
3. **Draft**: follow the template's section structure and order exactly. Do not add, delete, or reorder sections arbitrarily — for an inapplicable section, do not delete it; leave "해당 없음" (not applicable) plus a one-line reason (so the next reader does not have to judge whether it is an omission). **One closed exception: the sections template 3A explicitly lists as conditional are omitted outright when their condition is not met.** The 해당 없음 rule serves a reader auditing a document for gaps; a repository README's reader is deciding whether to use the thing, and a column of 해당 없음 lines defeats the first screen it exists to build. The exception covers only those listed sections — every mandatory section still applies, template 3B has no conditional sections, and no other template gains this.
4. **Self-check**: verify against the checklist at the bottom of the template, then declare done. **If the document carries a diagram, run `python3 .agents/skills/diagram/scripts/check.py <path>` before declaring done** — a Mermaid parse error replaces the whole diagram with an error block and a label mistake renders as `Unsupported markdown`, neither of which is visible in the source, so the first person to see it is the reader you wrote it for. It is a pre-check, not a renderer: passing does not guarantee rendering. **For a PR body or an issue body there is no file to check** — draft it to a scratchpad file **with an `.md` extension** (the checker rejects any other suffix), run the check there, then submit.

**Diagram obligation (templates 1 and 5)**: it lands in the spec's design/boundary section — `## 인터페이스 / 설계 개요` in the template, but **key on the section that plays that role, not on its title**, because root harness specs use their own numbered structure and 6 of 22 specs here have no section by that name — and in the PR body's `## 변경 내용`. Each of the four conditions carries a **threshold** (3+ messages with a non-reply among them; 3+ states with a non-linear transition; 2+ decisions, settled by the deciding test; 4+ components with 3+ relations that are not a single linear chain): meeting one requires a Mermaid diagram, and **meeting none forbids adding one**. The thresholds are the rule — the bare shapes are in every technical document, so an unthresholded condition mandates noise (measured: the first draft fired on every governed section in this repository). Single source, including tool choice and the label rules: `diagram` skill §1. Reason for having a condition at all: "use a diagram when it helps" loses to whatever is faster today (root §8 signal ②, user report 2026-08-03).

## Type → template mapping

| Type | When | Location |
|---|---|---|
| **Spec** | Before feature additions/behavior changes (root AGENTS.md section 13 SDD, mandatory) | Target project repo `docs/specs/YYYY-MM-DD-<제목>.md` |
| **Work report** | Team/phase deliverables | `_workspace/<작업명>/phase{N}_{에이전트명}_{내용}.md` |
| **README (repository root)** | The first screen of a repository someone can clone or install | Repository root — template 3A |
| **README (directory / internal)** | A directory or module below that root | That directory — template 3B |
| **Runbook (operational procedure)** | Recurring ops procedures (deploy, recovery, inspection) | Target project repo `docs/runbooks/` |
| **PR body** | On PR creation (branch-workflow finish procedure, step 5) | `gh pr create --body` input |

ADRs and change-history tables are not this skill's target — the single source of their format is root AGENTS.md section 6 (keeping it in two places makes them drift).

## Common style rules (all types)

- Korean, declarative sentences. One claim per sentence. **Exception**: `_workspace/` internal team reports (the work-report template) are written in English (root AGENTS.md section 15 — model-only internal deliverables; the section structure is identical). Documents the user reads directly (specs, runbooks, READMEs, PR bodies, integrator final reports, proposals) stay in Korean.
- **Why-First**: attach a reason to every rule and decision.
- No section with a heading but no content. Mark guesses honestly as "미확인" (unverified).
- Code, commands, and paths in backticks. Dates as YYYY-MM-DD.
- Change-history table at the bottom (날짜/변경 내용/대상/사유 — date/change/target/reason) — **specs and runbooks only**. One-off reports are excluded, and so are **READMEs**: root harness README changes are already recorded in `docs/harness-changelog.md` (root AGENTS.md section 6, ADR 021) and sub-project README changes ride that repository's own git history, so a table inside the file would be a third place recording the same change — the state root AGENTS.md section 5 calls untrustworthy. Verified 2026-07-28: neither the root `README.md` nor `project/agent-eval-gate/README.md` carries such a table, while changelog rows name `README.md` in their 대상 column — the previous wording was declared and never implemented.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Format consistency | Different structure per document, re-learn how to read each time | Same type = same section structure |
| SDD linkage | Spec format varies each time, completion criteria go missing | Completion-criteria section always in the same place |
| Omission detection | Cannot tell an empty section from a non-applicable one | "해당 없음" + reason rule |
