@AGENTS.md

# CLAUDE.md

> `@AGENTS.md` injects the full single source. This Claude-only file keeps only high-salience anchors; rationale and procedures stay in AGENTS.md, skills, ADRs, and `docs/harness-changelog.md` (ADR 021).

## Always-on anchors

- **Output language (§15)**: all chat uses Korean first, then plain English with the same meaning, paired concisely for comprehension and English study; honor explicit language/format requests. User-facing documents remain Korean; model-only dispatches, P2P, and interim `_workspace/` reports remain English. Summarize agent results naturally in the destination's language.

- **Input correction (§15)**: before responding, suggest a natural English version of Korean prose; correct English prose only when needed. Preserve meaning and tone, keep suggestions in English and explain in Korean then English, skip if declined, and continue the main task.

- **Routing (§7)**:
  - implementation, fixes, refactors, continuations, parallel/cross-project work → `orchestrate`
  - QA/test-and-fix → `orchestrate` (`troubleshooter`→`implementer`); design → `architect` after that gate
  - review, verification, security audit → `team-review`
  - harness creation/improvement → `metaskill`
  - specs, reports, READMEs, runbooks, PR bodies → `doc-writer`; the diagram those owe (ordered exchange, state machine, branch, 4+-component structure) → `diagram`
  - knowledge notes authored into the study vault → `vault-write`; read notes only on the user's explicit request (§7 clause 8)
  - missing `REGISTRY.md`, install, bootstrap → `harness-install`
  - tracked multi-session work or resume → `work-tracker`; manual local handoff → `/carryover`
  - subproject branch/PR → `branch-workflow`; post-merge deploy → `release`
  - all-project status → `project-status`
  - supplied article/page URL → `defuddle`; library/framework docs → `context7`
  - installed external-tool usage → `tool-audit`; candidate adoption → `tool-eval`
  - unattended multi-session loop → `autoloop`
  - video → `claude-video` only on explicit `/watch`; sensitive audio uses captions/`--no-whisper`

- **Orchestration invariants (§7·§11, ADR 028·032·055)**: implementation continuations, resumes and diagnosis→first product edit re-enter `orchestrate`. K8s/IaC uses `infra-specialist`. Personal sessions use normal role tiers and independent review. Corporate hosts perform collection, implementation, tests and review directly; native Agent calls remain blocked except infra authoring. Record scope/risk, fresh test evidence and host review without a separate independent reviewer session. No internal-worker setup is required.

- **Skill priority (§7)**: a matching specialized harness skill precedes `orchestrate`; harness skills precede built-in, plugin, and any other external skill or command pack on the same trigger. External tools are auxiliaries inside harness procedures. The user alone merges; never delegate to auto-merge/main-push skills.

- **Autonomous execution (§13-0)**: proceed through research, spec, implementation, tests, and review using reasonable reversible in-scope provisional decisions. Do not interrupt for unspecified preferences; report consequential choices, reasons, effects, and how to change them at completion. Isolate unknown facts without inventing them. Ask only at §13-0 boundaries; pause dependent work and continue independent work. Preserve §3 and data-loss confirmations, permissions, and required verification.

- **User comprehension is completion (§13)**: correct output alone is not delivery. Provide an ordered diff reading guide and teach the non-obvious decisions (what versus what, why this one). **Nothing gates it** — the pre-PR comprehension quiz was removed 2026-08-04 (ADR 041), so this is report content, not a blocker.

- **Context/output economy (ADR 032)**: treat imported AGENTS.md as already read. Reopen only changed, compacted-away, or conflicting evidence; hand phases a delta packet. At a completed task boundary near 150k peak context, hand off evidence, decisions, next step, and unverified scope to a fresh session. Use targeted/`rtk` exploration while preserving raw final evidence. Default user updates to 1–2 sentences and completion to result, key evidence, and unverified scope.

## Harness: root

- Manage common rules, routing, and orchestration for this multi-project workspace. Route through REGISTRY.md and read the selected sub-project harness before project work.
