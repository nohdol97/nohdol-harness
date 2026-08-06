@AGENTS.md

# CLAUDE.md

> `@AGENTS.md` injects the full single source. This Claude-only file keeps only high-salience anchors; rationale and procedures stay in AGENTS.md, skills, ADRs, and `docs/harness-changelog.md` (ADR 021).

## Always-on anchors

- **Output language (§15)**: every user-facing chat, question, summary, report, PR body, and document is in **Korean**. Model-only dispatches, P2P, and interim `_workspace/` reports are English. Digest English agent results into Korean; never expose them verbatim to the user.

- **Routing (§7)**:
  - implementation, fixes, refactors, continuations, parallel/cross-project work → `orchestrate`
  - QA/test-and-fix → `orchestrate` (`troubleshooter`→`implementer`); design → `architect` after that gate
  - review, verification, security audit → `team-review`
  - harness creation/improvement → `metaskill`; routine review proposal → `harness-review`
  - specs, reports, READMEs, runbooks, PR bodies → `doc-writer`; the diagram those owe (ordered exchange, state machine, branch, 4+-component structure) → `diagram`
  - knowledge notes authored into the study vault → `vault-write` (reading it as design input stays §7 clause 8)
  - missing `REGISTRY.md`, install, bootstrap → `harness-install`
  - tracked multi-session work or resume → `work-tracker`; manual local handoff → `/carryover`
  - subproject branch/PR → `branch-workflow`; post-merge deploy → `release`
  - all-project status → `project-status`
  - supplied article/page URL → `defuddle`; library/framework docs → `context7`
  - installed external-tool usage → `tool-audit`; candidate adoption → `tool-eval`
  - unattended multi-session loop → `autoloop`
  - video → `claude-video` only on explicit `/watch`; sensitive audio uses captions/`--no-whisper`

- **Orchestration invariants (§7, ADR 028·032)**: implementation continuations, work-tracker/carryover resumes, and diagnosis→first product Edit all re-enter `orchestrate`. K8s/IaC goes through `infra-specialist`. Product changes of 3+ files use `implementer`; ≤2 low-risk files may be direct but still require independent review. Collection uses `explorer`, causation uses `troubleshooter`, verification uses `reviewer`. **All of that is off on a `사내` profile (§13-3, ADR 042)** — every dispatch is blocked at the call by `dispatch-gate`, `infra-specialist` alone excepted and no override marker exists; the main loop does the work sequentially and records that it ran without fan-out, so `orchestrate` always lands on 직접 수행 there. Record the expected Agent-call budget, reuse the same agent for delta work, and add agents only for a new independent risk axis or required independence. Dispatch independent work simultaneously; background is the default, with foreground only for ≲1-minute lookups needed in the same response.

- **Skill priority (§7)**: a matching specialized harness skill precedes `orchestrate`; harness skills precede built-in, plugin, and any other external skill or command pack on the same trigger. External tools are auxiliaries inside harness procedures. The user alone merges; never delegate to auto-merge/main-push skills.

- **Interview-first (§13-0)**: before non-trivial work, enumerate assumptions, missing constraints, decision criteria, and likely blockers; look up discoverable facts and batch the **frontier** — questions whose prerequisites are settled — up front, deferring any resting on a guessed premise to the round that settles it (a question may state its own condition and stay, but only if that premise is settled or asked in the same round) — **as a list the user sees before starting, or one line when nothing needs asking**. Once work starts, resolve forks autonomously and report the decision space. Only mandatory §3 guardrail confirmations and data-loss confirmations may interrupt execution.

- **User comprehension is completion (§13)**: correct output alone is not delivery. Provide an ordered diff reading guide and teach the non-obvious decisions (what versus what, why this one). **Nothing gates it** — the pre-PR comprehension quiz was removed 2026-08-04 (ADR 041), so this is report content, not a blocker.

- **Context/output economy (ADR 032)**: treat imported AGENTS.md as already read. Reopen only changed, compacted-away, or conflicting evidence; hand phases a delta packet. At a completed task boundary near 150k peak context, hand off evidence, decisions, next step, and unverified scope to a fresh session. Use targeted/`rtk` exploration while preserving raw final evidence. Default user updates to 1–2 sentences and completion to result, key evidence, and unverified scope.

## Harness: root

- Manage common rules, routing, and orchestration for this multi-project workspace. Route through REGISTRY.md and read the selected sub-project harness before project work.
