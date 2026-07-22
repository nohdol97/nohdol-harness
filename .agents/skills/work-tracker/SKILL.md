---
name: work-tracker
description: "Persist work state across sessions using GitHub Issues (ccpm pattern) - register multi-session epics with spec-linked task checklists, log progress when pausing, resume from open issues, close via PR Closes #N. Falls back to docs/backlog.md in the project repo when there is no GitHub remote. Use when work will span multiple sessions or PRs, or when the user says 작업 등록, 백로그에 넣어줘, 이어서 하자, 하던 작업 뭐였지, 진행 상황 기록해줘, checkpoint, save progress, where was I (these route here, not to external checkpoint skills). Do NOT use for continuing an in-progress implementation step in the SAME session (진행해줘/계속 → orchestrate gate re-entry) - this skill resumes REGISTERED cross-session work. Re-run keywords - work-tracker, backlog, issue, epic, resume, 작업 등록, 백로그, 이어서, 재개."
---

# work-tracker — Session-Persistent Work Tracking (ccpm pattern)

## Why this skill

`_workspace/` and session context are **not preserved** (root AGENTS.md §4) — when a session ends, "how far we got and what comes next" is recorded nowhere, so the next session must reverse-engineer the state from git history alone. This skill adopts the ccpm pattern and puts **the persistent store for work state in the project repository itself** (GitHub Issues, or `docs/backlog.md` if none). Reason: state must live in the same place as the code to stay consistent, and it travels along even when the installation site changes (ADR 005 portability).

## Registration criteria (no overuse)

**Register only work that will not finish in one session** — work split across multiple PRs, multi-day epics, or work the user explicitly asked to register ("등록해줘"). Reason: registering everything creates an issue graveyard nobody reads — the same philosophy as the lazy-creation principle (ADR 007). For work that finishes in one session, that session's PR/commits are sufficient state handoff without registration.

## Store selection (based on the project repository)

1. **GitHub remote + `gh` available** → GitHub Issues (default).
2. **No remote, or not GitHub** → record in the project repository's `docs/backlog.md` with the same structure (epic section + task checklist + progress log) and commit.
3. Long-running work on the root harness repository uses the same rule (GitHub Issues).

## Flow 1 — Register (at work start)

```bash
gh issue create --title "<간결한 작업명>" --label epic --body "$(cat <<'EOF'
## 배경
<한 단락 — 왜 이 작업인가>

## 스펙
<docs/specs/... 경로 또는 "스펙 작성 예정(13절)">

## 태스크
- [ ] <완료 기준 단위의 태스크 1>
- [ ] <태스크 2>

## 진행 로그
(세션이 끝나거나 중단할 때 코멘트로 추가)
EOF
)"
```

(The issue title/body are user-read external artifacts — keep them in Korean per root §15; the template above is the literal text to use.)

- Split tasks **by the spec's completion-criterion (C-number) units** (§13 SDD) — each checkbox must correspond to one verifiable state change so the resume point is unambiguous.
- For code work, continue into the `branch-workflow` start procedure, and reference the issue number in the branch name/commits (e.g. `feat/login-oauth` + commit body `#12`).
- **Never write secrets/credentials into the issue body** (guardrail §3) — issues are external artifacts that persist outside the repository (on GitHub) as well.

## Flow 2 — Progress log (at session end/interruption)

When closing a session without finishing the work, leave this **without fail** — this comment is the next session's starting point:

```bash
gh issue comment <번호> --body "$(cat <<'EOF'
### 진행 로그 (YYYY-MM-DD)
- 완료: <이번 세션에 끝낸 것 — 커밋/PR 링크>
- 다음: <바로 이어서 할 구체적 첫 행동>
- 막힘: <블로커와 원인, 없으면 생략>
EOF
)"
```

(Comments are user-read — write them in Korean using the template above.)

At the same time, update the task checkboxes in the body (`gh issue edit`). Among `_workspace/` intermediate artifacts, conclusions the next session needs are **summarized and moved into a comment** — the originals are not preserved. When moving, **exclude anything marked `<private>…</private>`** (sensitive paths, internal URLs, personal information — root AGENTS.md §3 guardrail). Issues/comments are external artifacts that persist outside the repository, so uphold this exclusion together with the secrets prohibition (guardrail §3).

After recording, **present the next-session start prompt as a copy-paste code block** (same format as wrapup step 5 and carryover save mode — the same experience even when invoked standalone): `이어서 하자 — #<번호> <이슈 제목>. 첫 행동: <방금 남긴 진행 로그의 "다음" 항목>`. Take the "첫 행동" (first action) verbatim from the progress log (do not invent it — if they diverge, there are two resume points).

## Flow 3 — Resume ("이어서 하자", "하던 작업 뭐였지")

```bash
gh issue list --state open --label epic   # 대상 프로젝트 저장소에서
gh issue view <번호> --comments           # 마지막 진행 로그 확인
```

The "다음" (next) item of the last progress log is the starting point. For code work, confirm the branch exists (`git branch -a`); if missing or merged, start over from the branch-workflow start procedure. If the project is ambiguous, query open epic issues in REGISTRY.md registry order and report.

**If the resumed work is new implementation or a behavior change, re-enter the orchestrate gate (0-1)** — a session does not continue implementing directly just "because it's a resume". The gate also judges the implementation owner (3+ files → dispatch implementer; high-risk → team judgment — orchestrate implementation-owner rule; real case 2026-07-21: a resume session went straight to direct implementation without the gate). This skill only hands over the starting point; it does not decide the implementation path.

## Flow 4 — Complete

- Put `Closes #<번호>` in the PR body (branch-workflow finishing procedure) — the issue closes automatically at merge time (by the user), so state and code get cleaned up at the same moment.
- For work that ends without a PR (docs, research, etc.), leave a conclusion comment and `gh issue close <번호>`.
- With the `docs/backlog.md` approach, move the item to the "완료" (done) section and commit.

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Session boundary | State lost with the context — reverse-engineered from git history | Immediate resume from the progress-log comment |
| State location | Session-local devices like checkpoint — cannot cross installation sites | Persisted in the project repository (issues) — queryable anywhere |
| Completion consistency | Work done but the tracking item left open | PR `Closes #N` closes code and state together |
| Noise | Recording everything creates an issue graveyard | Only multi-session work registered (fixed criteria) |
