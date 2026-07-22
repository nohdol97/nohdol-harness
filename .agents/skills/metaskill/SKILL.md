---
name: metaskill
description: Create, scaffold, audit, improve, and evolve project harnesses (AGENTS.md, CLAUDE.md pointer, agents, skills, ADRs). Use when the user says 하네스 만들어줘, 프로젝트 새로 만들어줘 (scaffold project WITH its harness), 하네스 개선, 하네스 구조 점검·개선, or when evolution triggers fire (3+ repeated requests, 2+ repeated failures, harness bypass observed). Handles both new-harness creation and existing-harness improvement. Do NOT use for the routine daily/weekly evolution-signal scan or proposal-only review (→ harness-review) - metaskill APPLIES changes (create/improve/retire) while harness-review OBSERVES signals and proposes. Re-run keywords - metaskill, harness, scaffold, audit, evolve, 하네스, 하네스 개선.
---

# metaskill — the skill that builds harnesses

## Why this skill

Building harnesses ad hoc gives every project a different structure, breaking routing, inheritance, and symlinks. This skill enforces that every harness shares the same skeleton (AGENTS.md single source, change history, ADRs — root: CLAUDE.md `@AGENTS.md` import + always-on anchors (ADR 021) + `.agents/` symlinks; sub-projects: centrally managed under `.agents/projects/<name>/`). Reason: a harness's value comes not from individual files but from **consistency** — an agent entering any project must find the same rules in the same place.

## Mode fork (first decision)

If the target path **already has an `AGENTS.md` → improvement mode**; **if not → new-creation mode**.

- **Improvement mode**: Respect the existing structure. Fix only the defects instead of rewriting wholesale, and record every change in that AGENTS.md's change-history table. For structural changes (pattern transition, 8+ agents, etc.) also leave an ADR. **Verification proportionality**: independent verification (reviewer) of harness changes scales with risk — **normative changes** (rules, procedures, gates, trigger boundaries, agent permissions, hook code) require independent reviewer verification; **non-normative diffs** (wording polish, pointers, typos, history rows — nothing that changes judgment or behavior) are covered by self-verification (reference/conflict check) + history record. Reason: if verification cost (~100k tokens and several minutes per run — measured: 2026-07-17 session, average of 6 reviewer runs) stays fixed regardless of diff risk, it becomes overconsumption relative to output (root §8 ④). **When judgment is ambiguous, lean toward verification** — a false pass is more dangerous than a false block (reviewer §2). Pressure testing (common rule 7) applies only to newly created or revised behavioral disciplines — skipping verification/tests with proportionality as an alibi is exactly the "omitted code" that §16 forbids. **After completing a root-harness improvement**, report in chat what was improved and append one line `- YYYY-MM-DD [개선] <content> (PR/commit)` to `_workspace/harness-ops-log.md` (the ops log is user-facing — written in Korean) — the single place to check "what was improved" across sessions.
- **Install-site profile gate (mandatory before modifying any tracked harness file — root AGENTS.md §5)**: Check the install-site profile in REGISTRY.md. If **corporate**, do not modify tracked files at all; record the intended change in `_workspace/harness-updates.md` as a `대기` (pending) item (item format: under `## YYYY-MM-DD title`, status (대기/적용됨) / target files / change content / rationale — the change content must be detailed enough to apply as-is on the personal machine, ADR 012). If the profile is unrecorded, confirm with the user, record it in REGISTRY.md, then proceed (remote PR sessions are treated as personal). Untracked areas (`.agents/projects/`, REGISTRY.md, `_workspace/`) may be modified regardless of profile — they never touch git.
- **New-creation mode**: follow the procedure below.

## Clarification interview (mandatory before proceeding when anything is ambiguous)

If the project has any ambiguity, do not proceed — actively question the user: stack, deployment method, recurring tasks (record as skill candidates — creation is deferred). Reason: a harness built without an interview gets bypassed on first real use, and a bypassed harness never gets read again. However, **read project documents such as README before asking about role/purpose** (observation first), and **never ask about related projects** — they are filled in through real-work observation (root AGENTS.md §1).

## New-project creation scenario ("프로젝트 새로 만들어줘")

1. Clarification interview
2. Create directory & basic scaffolding → **see `references/scaffold.md`**
3. Create the harness (see "Deliverable requirements" below)
4. **Do not create skills/agents (deferred creation — root AGENTS.md §12)**: initial deliverables are documents only (AGENTS.md, adr/). Recurring-procedure candidates from the interview's "expected recurring tasks" answer and from the stack (build/test/deploy etc., see the candidate reference table in `references/scaffold.md`) are **only recorded in the sub AGENTS.md "skill candidates" section**. Actual creation happens solely via the "sub skill/agent creation scenario" below. Reason: skills made in advance diverge from real use and get bypassed — build only what proven need demands.
5. **Add a new row to the project registry in root REGISTRY.md** — role based on document/interview observation; related projects start as "미기록" (unrecorded — updated through real-work observation, root AGENTS.md §1)
6. Update the REGISTRY.md change history

Also update the registry on project **deletion/move**. A registry out of sync with reality skews all routing.

## Sub skill/agent creation scenario (deferred creation — the only creation path)

Trigger: **when a recurring task is observed, or a procedure/role appears mid-work that seems worth registering as a skill/agent** (including the 4 evolution-trigger signals). Procedure:

1. Propose the candidate to the user (no unauthorized creation). Items recorded in the sub AGENTS.md "skill candidates" section are first-priority candidates.
2. On approval, create at **`.agents/projects/<name>/skills/<skill>/SKILL.md`** or **`.agents/projects/<name>/agents/<agent>.md`** — `.agents/projects/` is untracked, so it never enters git. Format is identical to root (all 8 "skill common rules" below, agent-rules.md 10 sections).
3. **List the skills/agents and their paths in the sub AGENTS.md** — this location is not auto-discovered by the CLI, so routing reading the sub AGENTS.md is the only path that loads them. Put the actual commands in the body (a skill without commands is worse than none).
4. Promote to root `.agents/skills/` (tracked) only skills that generalize across projects/install sites (after removing project-specific content).

## Pending-queue application scenario (personal install site — "하네스 업데이트 적용해줘")

The path for actually applying improvement items carried over from a corporate install site on a personal install site. Trigger: the user supplies queue content (paste/file copy), or `대기` (pending) items are found in `_workspace/harness-updates.md` (including via harness-review integrity checks).

1. Confirm the profile is **personal** (corporate cannot run this scenario — items stay in the queue).
2. Review each item's target files/change content and apply — if the file has diverged since recording (already applied, target section changed), do not apply verbatim; translate the intent to the current structure, and confirm with the user when judgment forks.
3. Finish per the usual rules: update the file's change history, ADR for structural decisions, commit & push (§5), append an `[개선]` item to the ops log (`harness-ops-log.md`).
4. Update applied items' status to `적용됨` (applied, + application date) — the queue becomes history and prevents double application.

## Deliverable requirements (must be included in a new harness)

- **Root harness only**: `CLAUDE.md` has first-line **`@AGENTS.md`** import (always-on injection of the full single source at session start — ADR 021) + Claude-only **always-on anchors** (`## Harness: {domain}` section + **output language** + **routing summary** (skill names such as orchestrate) + **skill priority**). **No change-history table in CLAUDE.md** (root change history lives in `docs/harness-changelog.md`). Do not copy full rules into CLAUDE.md — only one-line top-priority anchors per turn (re-bloat prevention — root AGENTS.md §11). **Do not create CLAUDE.md for sub-projects** — no session ever starts at that path, so it is a dead file with no loader (root AGENTS.md §12).
- **When installing the root harness on a new workspace**: always create `REGISTRY.md` (install-site-specific project registry — untracked by git). Follow the `harness-install` skill. Never create one for sub-project harnesses.
- First line of `AGENTS.md` states inheritance from the root AGENTS.md (sub-projects). **Sub-project AGENTS.md** has a change-history table at the bottom (initial 1 row). **Root AGENTS.md separates change history into `docs/harness-changelog.md`** (ADR 021 — it is always-on injected via `@AGENTS.md`, so the audit log is removed from the import footprint).
- **Root harness only**: shared directories `.agents/agents/`, `.agents/skills/` + `.claude/agents`, `.claude/skills` symlinks. If symlinks are impossible in the environment, substitute a sync script and record it in an ADR.
- **Sub-project harnesses use central management (root AGENTS.md §12, ADR 006/007)**: create the original and only copy at root `.agents/projects/<name>/` — composition: `AGENTS.md` (including a "skill candidates" section), `adr/`, and lazily created `skills/`/`agents/`. `<name>` must match the REGISTRY.md registry row. **Never place harness files in `project/<name>/` or its git repository** (including symlinks/copies) — routing (REGISTRY.md → read the original) makes the connection, so no distribution mechanism is needed. `.agents/projects/` is install-site data and untracked.
- **Sub-project skills/agents are lazily created** — the "sub skill/agent creation scenario" above is the only creation path. No initial creation. If a hook is needed, put it only in root `.claude/settings.json` as a path-branching hook.
- **Agent/skill files must be created in the `.agents/` originals — `.claude/` is a symlink, so never create directly under it.** When a root agent is created/renamed/retired, synchronize the thin `.codex/agents/<name>.toml` adapter in the same change (do not duplicate the role body — only preload the full Markdown, ADR 027). If a symlink is replaced by a real file or a Codex adapter drifts, the two CLIs see different roles (root AGENTS.md §11).
- orchestrate integration: state that implementation/multi-step work passes root orchestrate's team-necessity judgment (Phase 0-1), and multi-project/team work forms teams via orchestrate (ADR 010).
- ADR directory (NNN-title.md on structural decisions): root harness → `docs/adr/`, sub-projects → `.agents/projects/<name>/adr/`.
- **Document map (MOC) sync (root harness only)**: when an ADR, spec (`docs/specs/`), or proposal (`docs/proposals/`) is created at root or changes state (superseded/implemented/rejected), **update the corresponding row in the `docs/README.md` index in the same commit** (root AGENTS.md §6). Same reason as the REGISTRY.md update obligation — an index out of sync with reality loses trust as a navigation basis.
- **Root README.md asset-list sync (root harness only — repeated-omission spot)**: when a skill/agent is **created, renamed, or retired** under root `.agents/skills/`/`.agents/agents/`, **update the root `README.md` directory tree (one-line skill/agent description list) in the same commit** — this list update was repeatedly missed when adding new skills (signal ②; changelog 2026-07-16 and 07-18 "README stale sync" are traces of after-the-fact resyncs). The MOC above (`docs/README.md`) is the ADR/spec/proposal index while **this tree is the skill/agent list — separate files**; confusing them and updating only one leaves the other stale. Sub-project skills/agents update **the list in the sub AGENTS.md** (§12), not the root README.
- When creating an agent, follow **the 10-section template in `references/agent-rules.md`**.
- When creating a skill, follow the "Skill common rules" below.
- When pattern selection is needed, see **the flowchart in `references/patterns.md`**.

## Conditional details (read only when needed)

- **k8s/infra project** → see `references/k8s.md`
- **New-project scaffolding** → see `references/scaffold.md`
- **Creating an agent definition** → see `references/agent-rules.md`
- **Choosing an orchestration pattern** → see `references/patterns.md`

## Skill common rules (apply to every skill in this workspace)

1. **frontmatter is mandatory (spec violation makes the skill appear with no description)**: SKILL.md must start **from line 1** with `---` YAML frontmatter containing `name` (matching the directory name) and `description`. The CLI reads **only the frontmatter description** for listing and automatic trigger matching — a description written only in the body shows the bare name and fails to catch user input. Write the description as a single line; if the value contains YAML special characters such as colons (`: `) or quotes, **wrap the whole value in double quotes** (otherwise the entire frontmatter fails to parse). **Verify right after creation**: check line-1 `---`, the closing `---`, and description presence with `head -6`.
2. **description (written in English, ≤800 chars recommended — must stay within the CLI hardcap of ~1024 chars; Pushy formula — 3 elements + negative triggers)**: ① verb enumeration ("PDF-related work" ✗ → "read, extract, merge, OCR PDFs" ✓) ② explicit trigger situations ("use this skill when the user mentions ~") ③ **re-run keywords included** — so it is auto-invoked again in new sessions. **Korean trigger keywords are recommended alongside** the re-run keywords (they must match the user's request phrasing). ④ **negative triggers (recommended when boundaries overlap with adjacent skills/tools)**: state easily confused adjacent situations as `Do NOT use for …` to actively block misrouting — e.g. defuddle's `Do NOT use for URLs ending in .md (→ WebFetch)`. Reason: with positive triggers only, boundary-overlapping requests match both skills and routing wobbles — a negative boundary settles the match to one side (a low-cost remedy for repeatedly observed misrouting failures; kepano/obsidian-skills convention ported 2026-07-16). **Negative triggers outrank the length target**: skills with overlapping boundaries may run long to fit negative triggers but stay within 800 chars; if truly over, trim the positive verb enumeration but never delete the negative boundary — blocking misrouting is worth more than a few tokens (raised from a fixed 500 after measurement showed many skills exceeding it due to the negative-trigger convention, 2026-07-16 asset review).
3. **Progressive Disclosure**: SKILL.md body within 500 lines. Split into three layers — metadata → body → `references/` — and move conditional detail into `references/`. Reason: the longer the always-read body, the higher every invocation's cost and the more the core rules get buried.
4. **Why-First**: Do not list rules alone; include the reasons. Attaching a reason widens a rule's applicable range — the LLM can keep judging in edge cases.
5. **with/without**: State the difference with/without this skill (metric evaluation) at the bottom of the skill.
6. **Effective timing**: Skill additions/edits take effect **from the next session** (the CLI loads at session start). To use a just-created skill immediately, open a new session or invoke it explicitly with `/skill-name` — include this fact in the creation completion report.
7. **Pressure testing (behavioral disciplines only — ported from superpowers writing-skills, ADR 022)**: For discipline skills/rules that aim to change the model's default behavior (gates, prohibitions, forced procedures), do not declare completion from the static checklist alone — **first observe a pressure scenario (baseline) where a subagent actually violates without the skill**, write the skill targeting the rationalization phrases observed there, then confirm the same scenario turns into compliance (observe failure → write → confirm compliance — the documentation application of root AGENTS.md §13 TDD). If new rationalizations appear during confirmation, plug those holes and re-confirm. Reason: a rule that has never seen baseline failure blocks imagined violation points, not real ones. **Reference/procedural skills (command collections, templates) are out of scope** — for documents with no 'behavior' to resist pressure, this procedure is pure cost (root AGENTS.md §16 minimalism).
8. **English-first authoring (ADR 030)**: New harness assets (AGENTS.md files, agent definitions, SKILL.md, references) are **authored in English by default** — they are model-loaded assets, and English cuts input tokens on every load (root §15 rationale applied to load frequency). The Korean summary views (`.agents/agents/README.ko.md`, `.agents/skills/README.ko.md`, `AGENTS.ko.md`) **must be updated in the same commit** whenever their source assets are created, renamed, or retired — a stale summary view misleads the user the way a stale REGISTRY.md misleads routing. This is part of the completion checklist below.

## Evolution triggers (automatic conditions that invoke this skill)

The 4 signals of root AGENTS.md §8 — ① same request type 3+ times ② same failure 2+ times (including same correction 2+) ③ observed harness bypass ④ shrink/efficiency (skills/agents unused 3+ weeks, token-overconsumption pattern 2+ times — weekly check only) — when detected, **propose** creation/improvement/**retirement/consolidation to the user**, and execute with this skill on approval. No unauthorized creation or retirement: the harness is the user's operating asset.

## Completion checklist (self-verification after create/improve)

- [ ] **Root harness only**: CLAUDE.md has the first-line **`@AGENTS.md`** import + `## Harness: {domain}` section + always-on anchors (output language, routing skill names, priority) (sub-projects have no CLAUDE.md)
- [ ] **Change history:** sub-project AGENTS.md has the bottom table (initial 1 row); **root has the table in `docs/harness-changelog.md`** (ADR 021 — no table at the bottom of CLAUDE.md/root AGENTS.md, pointer only)
- [ ] Orchestrator description includes re-run keywords
- [ ] Orchestrator's initial Phase has `_workspace/` detection logic
- [ ] Every agent definition has a "re-invocation guide" section
- [ ] **Root agents:** `.agents/agents/*.md` and `.codex/agents/*.toml` stem sets, `name`, `description` match 1:1; TOML preloads the corresponding full Markdown and pins no model/sandbox (ADR 027)
- [ ] Operating habit of observing the 4 evolution-trigger signals is stated (expansion ①–③ daily, shrink/efficiency ④ weekly)
- [ ] **Root harness only**: `.claude/agents`, `.claude/skills` point at the shared directories (symlink verification)
- [ ] **Sub-project only**: the harness original lives at root `.agents/projects/<name>/`, and `project/<name>/` and its git repository contain no harness files. REGISTRY.md has a row with the same name
- [ ] **Sub-project only**: no initial skills/agents created (deferred-creation principle); sub AGENTS.md has a "skill candidates" section. Any lazily created skills/agents live in `.agents/projects/<name>/skills/`/`agents/` and are listed with paths in the sub AGENTS.md
- [ ] **Root harness only**: REGISTRY.md has the project registry table (row added for a new project). Sub-project harnesses hold no registry (root-single principle)
- [ ] **Root harness only**: if root skills/agents were created/renamed/retired, the corresponding list rows in the root `README.md` directory tree were updated in the same commit (repeated-omission spot — a separate file from the `docs/README.md` MOC)
- [ ] **English-first (ADR 030)**: new/renamed/retired harness assets are authored in English, and the affected Korean summary views (`.agents/agents/README.ko.md`, `.agents/skills/README.ko.md`, `AGENTS.ko.md`) were updated in the same commit
- [ ] Destructive-work user-confirmation guardrail exists in root AGENTS.md
- [ ] Every SKILL.md is within 500 lines and has with/without metrics at the bottom
- [ ] Every SKILL.md frontmatter starts at line 1 with `---`, has `name` (matching directory) and `description`, valid YAML (double-quoted if special characters) — verified with `head -6`
- [ ] ADR exists (001 for initial setup)
- [ ] `_workspace/` is in gitignore, and harness files are not

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Structural consistency | Different harness structure per project, broken routing | Every project shares the same skeleton |
| Registry | Registration missed after project creation → routing impossible | Registry update built into the creation procedure |
| Evolution | Manual response to every repeated failure | 4-signal detection → proposal → approval → create/retire |
| Verification | Build and done | Completion judged by the 18-item checklist |
