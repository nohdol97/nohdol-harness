# New-project scaffolding procedure

Follow this procedure on a "프로젝트 새로 만들어줘" request. Never create a project without a harness — project creation and harness creation are one body.

## 1. Clarification interview (mandatory)

Minimum items to confirm:

| Item | Why needed |
|---|---|
| Stack (language, framework, package manager) | Determines scaffolding tool and initial skills |
| Deployment method (k8s? serverless? static?) | Determines guardrail scope and skill-candidate recording |
| Expected recurring tasks | Initial skill/agent candidates |
| Whether to create a GitHub repo — owner & visibility | Determines remote linkage & work-tracker (Issues) basis (see 2.5 below) |

Read documents such as README before asking about role/purpose (observation first). **Do not ask about related projects** — they get updated when projects are woven together in real work (root AGENTS.md §1).

## 2. Directory & basic scaffolding

- Create the `project/<name>/` directory (path convention — root REGISTRY.md, install-site-specific). Use the stack's standard scaffolder (e.g. `npm create vite`, `uv init`). If no scaffolder exists, create only the minimal structure by hand.
- git: `git init` in `project/<name>/` as an **independent repository** (ADR 002). The root repository does not track `project/`, and **no harness files go into the project directory or its repository** — the harness is centrally managed in root `.agents/projects/` (root AGENTS.md §12, ADR 006).
- Create the stack-standard `.gitignore`, then make the **initial commit** of the scaffolding output (`gh repo create --source=. --push` presupposes a commit, so one must exist before repo linkage). Commit convention: root AGENTS.md §5 (Conventional Commits, project name in scope).

## 2.5 GitHub repo linkage (optional — perform if the interview said "create")

Repo creation is an **externally publishing operation** (root AGENTS.md §3), so confirmation immediately before execution is mandatory. Skip this section if the interview said "local only".

1. **Pre-check**: Verify authentication/account with `gh auth status`. If unauthenticated, guide the user to `gh auth login` and stop with only the local repository in place (repo linkage later).
2. **Confirm owner & visibility (every time, no default — user-confirmed 2026-07-18)**: Immediately before repo creation, confirm the **owner** (personal account vs org) and **visibility** (`--public`/`--private`) with the user. This is the gate that prevents sensitive information accidentally landing in a public repo — never skip it.
3. **Create, link, push** (with the confirmed values):
   ```
   gh repo create <owner>/<project-name> --private|--public --source=. --remote=origin --push
   ```
   `--source=.` uses the current local repository, `--remote=origin` registers origin, and `--push` pushes the initial commit — all in one step (initial commit must precede — §2 above).
4. **Verify**: Confirm the origin link with `git remote -v` and the creation result (URL, visibility) with `gh repo view --json url,visibility`, then report.
5. **Once the repo exists**, work-tracker can manage session-spanning work via GitHub Issues (root AGENTS.md §14) — mention this if there is work that will span sessions. If not, do not register (prevent an issue graveyard).

## 3. Harness creation (central management — root AGENTS.md §12, ADR 006/007)

**The harness is created in root `.agents/projects/`, not in the project directory. There is no distribution (symlink/copy) — routing (REGISTRY.md → read the original) connects project and harness.**

```
.agents/projects/<project-name>/   # original and only copy — untracked by git (install-site data)
├── AGENTS.md          # first line: "This document inherits the root AGENTS.md." + "skill candidates" section
├── adr/               # structural decision records for this project
├── skills/            # deferred creation — not created initially (deferred-creation principle below)
└── agents/            # deferred creation — not created initially

project/<project-name>/            # code only — no harness files
```

- `<project-name>` must match the "name" of the REGISTRY.md registry row — routing finds the original by this name.
- **Do not create a sub CLAUDE.md** — no session ever starts at that path, so it is a dead file with no loader.
- The sub AGENTS.md holds **domain-specific rules only**. Common concerns (git, documents, guardrails, routing) live in root and are inherited — do not copy them. Reason: copies drift when root is updated.
- Do not create project-local `.agents/`/`.claude/` under `project/`. Hooks go only into root `.claude/settings.json` as path-branching hooks.
- **Deferred skill/agent creation**: create nothing initially. Only **record** the interview's "expected recurring tasks" and matching entries from the reference table below in the sub AGENTS.md "skill candidates" section; actual creation happens on observed repetition / discovered registration value via metaskill's "sub skill/agent creation scenario" → creation location `.agents/projects/<project-name>/skills/`/`agents/`.

## 3.5 Skill/agent candidate reference table (consulted at deferred-creation time)

**Principle**: "recurring procedures that run/verify/deploy" become skills; "roles requiring domain judgment" become agents. This is for candidate recording and future naming/scoping reference — not an initial creation list.

| Domain | Skill candidates | Agent candidates |
|---|---|---|
| Web (Next.js etc.) | `dev` (local run & check), `test` (tests & lint), `deploy` (deployment procedure) | UI reviewer if needed |
| App (Flutter, Android) | `build` (build & emulator run), `release` (signing & store procedure) | — |
| Backend/tools (Go, Python) | `run` (run & verify), `test`, `release` | — |
| k8s/infra | `plan` (diff & dry-run — pre-apply check), `apply` (guardrail-linked apply procedure) | manifest verifier (see `references/k8s.md`) |
| Bots/automation | `run`, `monitor` (log & status check) | — |

Candidates are a starting point, not the answer — at creation time, check the project's actual commands (build/test/deploy) and put the concrete commands in the skill body. A skill without commands is worse than none.

## 4. Root registry update (must not be missed)

Add a row to the root REGISTRY.md project registry:

| Name | Path | Stack | Role | Related projects | Harness |
|---|---|---|---|---|---|
| web | `project/web/` | Next.js | user web (based on README observation) | 미기록 | ✅ |

Related projects start as "미기록" (unrecorded) — the session that weaves them together in real work updates it (root AGENTS.md §1).

## 5. Wrap-up

- Add 1 row to the root REGISTRY.md change history (REGISTRY.md is untracked, so not a commit target).
- Self-verify with the metaskill completion checklist.
- Commit & push on work completion (root AGENTS.md §5 — standing user approval).
