# New-project scaffolding procedure

Follow this procedure on a "프로젝트 새로 만들어줘" request. Never create a project without a harness — project creation and harness creation are one body.

## 1. Clarification interview (mandatory)

Minimum items to confirm:

| Item | Why needed |
|---|---|
| **Transferred to a deployment site for follow-up?** | Ask **first** — it gates the deployment question below (see 1.1) |
| Stack (language, framework, package manager) | Determines scaffolding tool and initial skills |
| Deployment method (k8s? serverless? static?) | Determines guardrail scope and skill-candidate recording |
| Expected recurring tasks | Initial skill/agent candidates |
| Whether to create a GitHub repo — owner & visibility | Determines remote linkage & work-tracker (Issues) basis (see 2.5 below) |

Read documents such as README before asking about role/purpose (observation first). **Do not ask about related projects** — they get updated when projects are woven together in real work (root AGENTS.md §1).

### 1.1 Deployment-site handoff question (ask once, first — only when REGISTRY.md has a 「배포처 이관 경계」 section)

One question: *"이 프로젝트, 다른 곳(배포처)으로 이관해서 후속 작업할 건가요?"* The answer goes into the REGISTRY.md registry row's 이관 column (`배포처` / `로컬`), and never defaults — an unasked project is recorded `미확인`, because guessing `로컬` for a deployment-site project yields a spec with no boundary and the error only surfaces at the deployment site.

**This question ranks above the deployment-method item and rewrites it.** On `배포처`, deployment target, CI/CD, and auth are by definition decided against deployment-site state that cannot be seen from here, so do not press the user for them — record deployment as "배포처 후속(미결정)" and treat the guardrail scope as local-execution only. Asking both without this ordering either duplicates the question or produces a contradictory pair (deployment `k8s` + handoff `배포처`) with no rule saying which wins. On `로컬`, ask the deployment question as usual.

If the section is absent from REGISTRY.md, skip this step silently — it is install-site-specific, and its absence covers **two** sites that both make this export-side question wrong to ask here: one with no handoff at all, and a `배포처` site, which is the receiving end rather than the side that draws the boundary (`harness-install` step 5). Do not create the section here; `harness-install` owns it.

**On `배포처`, the sub AGENTS.md gets a "where the work belongs" section** (§3 below writes the file; this is one more required section in it). **It carries exactly one thing: which side *this installation* is** — `공용` (the side that builds the shared core) or `배포처` (a side that adapts and deploys it). That is the only genuinely installation-specific fact here, which is why it lives in this untracked file (ADR 005) and why a copy on another installation is *expected* to disagree. **Everything else — the area→files map, the fallback sentence, the stop-and-report gate — goes into the project repository** at `project/<이름>/docs/ownership.md`, because that rule must read *identically* on both sides and only git delivers sameness (measured: `agent-eval-gate` kept it here until 2026-07-28 and the copies drifted silently). **The repository copy uses neutral vocabulary** — `공용`/`배포처`, never terms naming a particular installation — so the product repository carries no installation distinction (user decision 2026-08-02). Do not re-derive the role from the REGISTRY 설치처 프로필: that value is set for harness-edit rights, and reading it as the ownership role couples two unrelated axes. If the machine actually in use contradicts what this file records, the machine wins and the session says which it used. The repository-side document then carries ② an **area→files map** for this project, derived from the registry classification table and the actual layout. State the 공용 row as **the default** ("every tracked path that does not match a row below"), not as a list of today's directories, or the first new top-level directory falls through every row. The 배포처 rows restrict the 배포처 side to **creating** files, never converting a shared-core-owned file — but say explicitly that created files **stay** deployment-site-owned, or the gate blocks the deployment-site side from maintaining its own adapter (a deployment-site edit to a file the shared-core repository also owns is what turns every later `git pull` into a conflict; a deployment-site side blocked from its own files is the gate defeating its own purpose) ③ **any deployment-site workflow the boundary exists to enable** — without provision for it the gate stops the one task it was built for. **Prefer splitting the file over carving an exception inside it**: a row claiming part of a file makes two machines co-own one file, which is the state this boundary exists to prevent, and a partial claim then needs its own fallback rule saying where the unclaimed sections land. The deployment-site setup checklist is the worked example — it lived as a README exception row (widened once from one section to three) until 2026-08-02, when it moved to its own deployment-site-owned `docs/site-setup.md` and the exception row was deleted. **Splitting the file is not the end of it**: the single commit that added the declaration "no row currently claims part of a file", claimed the new file wholly for the deployment site, **and edited that file** shipped with a shared-core-authored intro still in it — so the declaration was false the moment it was written, and it took the next commit to make the row true. Read the file, not just the table: the commit that declares whole-file ownership is exactly the one positioned to contradict it. A file claimed wholly by one side must actually be wholly that side's — provenance and rationale belong in the ownership table, which both machines read anyway. Carve an exception row only when the content genuinely cannot be separated, and then state the fallback explicitly ④ the registry's decision sentence as the fallback for anything unlisted ⑤ a **symmetric stop-and-report gate**: when the request does not match the machine, name the file or capability, say which side owns it, give the shorter path, and **proceed only on an instruction given after that report** — the triggering request is never itself the override, or no request ever stops. Both directions, since shared-core guesses at deployment-site state get redone anyway ⑥ **two boundaries on the gate**: it fires on mismatch only (a request plainly on the right side just gets done), and a request that is genuinely neither side is not a free pass — lean, say why, do the unambiguous part, hold the rest. Put the two-remote wiring in the Git section (`origin` = local side, `upstream` = the other side, pulled from and never pushed to). The boundary has to ride in the document because routing loads it on every entry into the project, while a boundary stated in chat dies at the next context reset.

**Then give the file a short section saying how it reaches the other machine — by hand, and only by hand.** It rides in no repository (ADR 005·006) and the root harness repo may be public (`gh repo view --json visibility` if unsure), so the transfer is the user copying it into the same `.agents/projects/<name>/` path over there. **Do not wire up a hosted mirror to save that step** (a secret-gist mirror was built and withdrawn the same day, 2026-07-26 — ADR 006): a standing channel between the two sides carries deployment-site content toward the shared-core side exactly as easily as the reverse, no mechanical guard exists for it the way `set-url --push … DISABLED` guards the git path, and every rule written to make it one-way collided with a rule already in place — the direction rule against the change-history row, the resulting exemption against the same-task logging obligation elsewhere. The section should also name the freshness check, since nothing automatic performs it: compare the last change-history row across the two machines, and when they differ, tell the user which side is behind.

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

| Name | Path | Stack | Role | Related projects | Harness | 이관 |
|---|---|---|---|---|---|---|
| web | `project/web/` | Next.js | user web (based on README observation) | 미기록 | ✅ | 로컬 |

Related projects start as "미기록" (unrecorded) — the session that weaves them together in real work updates it (root AGENTS.md §1). The 이관 column carries the step-1.1 answer (`배포처` / `로컬`), or `미확인` when the section does not exist and the question was skipped — never a guess.

## 5. Wrap-up

- Add 1 row to the root REGISTRY.md change history (REGISTRY.md is untracked, so not a commit target).
- Self-verify with the metaskill completion checklist.
- Commit & push on work completion (root AGENTS.md §5 — standing user approval).
