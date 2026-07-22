---
name: doc-writer
description: Write project documents in one consistent format - specs, work reports, READMEs, runbooks, PR bodies. Picks the template from references/templates.md, drafts in Korean (internal team reports in English per root AGENTS.md 15), then self-checks against the template checklist. Use when the user says 문서 작성, 문서 만들어줘, 스펙 써줘, 리포트 정리, README 써줘, PR 본문 써줘, when creating a PR (branch-workflow finish), or when section 13 (SDD) requires a spec before coding. Do NOT use for ADR or change-history-table entries - those follow root AGENTS.md section 6 directly, not this template. In orchestrate team mode, SDD spec drafting belongs to the architect agent (which uses this skill's template) - route standalone doc requests here. Re-run keywords - doc, doc-writer, document, spec, PR, 문서, 문서 작성, 스펙, PR 본문.
---

# doc-writer — consistent-format document writing

## Why this skill

When every document has a different format, the reading cost is paid anew each time — where the completion criteria are, where the decision rationale is, must be re-found per document, and eventually nobody reads them. The goal of this skill is that **the same kind of document always comes out in the same format**. With a fixed format, both humans and agents jump straight to the section they want, and cross-document comparison, search, and reuse become possible.

## Procedure

1. **Determine the type**: map the request to the table below. If ambiguous, ask the user for the purpose (who reads this document, and when).
2. **Load the template**: read only that type's section from `references/templates.md`.
3. **Draft**: follow the template's section structure and order exactly. Do not add, delete, or reorder sections arbitrarily — for an inapplicable section, do not delete it; leave "해당 없음" (not applicable) plus a one-line reason (so the next reader does not have to judge whether it is an omission).
4. **Self-check**: verify against the checklist at the bottom of the template, then declare done.

## Type → template mapping

| Type | When | Location |
|---|---|---|
| **Spec** | Before feature additions/behavior changes (root AGENTS.md section 13 SDD, mandatory) | Target project repo `docs/specs/YYYY-MM-DD-<제목>.md` |
| **Work report** | Team/phase deliverables | `_workspace/<작업명>/phase{N}_{에이전트명}_{내용}.md` |
| **README** | Project/directory introduction | Root of the target directory |
| **Runbook (operational procedure)** | Recurring ops procedures (deploy, recovery, inspection) | Target project repo `docs/runbooks/` |
| **PR body** | On PR creation (branch-workflow finish procedure, step 4) | `gh pr create --body` input |

ADRs and change-history tables are not this skill's target — the single source of their format is root AGENTS.md section 6 (keeping it in two places makes them drift).

## Common style rules (all types)

- Korean, declarative sentences. One claim per sentence. **Exception**: `_workspace/` internal team reports (the work-report template) are written in English (root AGENTS.md section 15 — model-only internal deliverables; the section structure is identical). Documents the user reads directly (specs, runbooks, READMEs, PR bodies, integrator final reports, proposals) stay in Korean.
- **Why-First**: attach a reason to every rule and decision.
- No section with a heading but no content. Mark guesses honestly as "미확인" (unverified).
- Code, commands, and paths in backticks. Dates as YYYY-MM-DD.
- Change-history table at the bottom (날짜/변경 내용/대상/사유 — date/change/target/reason) — living documents only (specs, runbooks, READMEs). One-off reports are excluded.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Format consistency | Different structure per document, re-learn how to read each time | Same type = same section structure |
| SDD linkage | Spec format varies each time, completion criteria go missing | Completion-criteria section always in the same place |
| Omission detection | Cannot tell an empty section from a non-applicable one | "해당 없음" + reason rule |
