---
name: harness-install
description: Bootstrap this harness on a new machine after cloning. Verifies .claude symlinks, creates untracked workspace directories (project/, _workspace/), scans existing projects, interviews the user, and generates the installation-specific REGISTRY.md with path conventions. Use when the user says 하네스 설치, 초기 설정, 새 컴퓨터 세팅, REGISTRY.md 만들어줘, or when REGISTRY.md is missing at session start. Re-run keywords - install, bootstrap, setup, 설치, 초기화.
---

# harness-install — New Installation Site Bootstrap

## Why this skill

This harness is not complete by cloning alone. **The installation-site-specific elements (REGISTRY.md, `.agents/projects/`, `project/`, `_workspace/`) are intentionally absent from git** (ADR 002·005·006). Starting work without this procedure leaves no routing basis (REGISTRY.md), making cross-project judgment impossible, and produces the bypass where real files appear under `.claude/` while symlinks are broken.

**A session without REGISTRY.md is in an installation-incomplete state** — even when other work requests come in, guide the user to this skill first.

## Procedure

### 1. Symlink, line-ending, and git hook layer verification

- **Symlinks**: Verify `readlink .claude/agents .claude/skills` points to `../.agents/agents`, `../.agents/skills`. If broken, recreate (`ln -sfn`); in environments where symlinks are impossible, substitute a sync script and record that fact in an ADR (root AGENTS.md §11). On Windows, if the symlinks were cloned as **plain files containing the path string**, enable developer mode or run `git config core.symlinks true` and re-checkout.
- **git hook layer registration (tdd-gate tool-agnostic enforcement — ADR 014·015)**: Register `git config --global core.hooksPath <root absolute path>/.agents/githooks`. This is the **sole enforcement layer** of the §13 TDD gate (unification — ADR 015), so an unregistered machine is a gate-less state, and global git config does not propagate through the repository, so it must be caught at install time (subsequent gaps are watched by the harness-review weekly integrity check). **If a different value is already set, do not overwrite — confirm with the user** (possible conflict with an existing hook system). Verification: check `git config --global --get core.hooksPath`, then pass `python3 .agents/githooks/tdd-gate_test.py`.
- **Codex session hook verification (macOS·Linux only — experimental feature, Windows unsupported, ADR 019)**: Activation (`[features] codex_hooks = true` in `.codex/config.toml`) and registration (`.codex/hooks.json`) are **both tracked, so they are on immediately upon clone** (always active) — there is no per-machine enabling step. If this installation site **also uses the Codex CLI**, open a new Codex session and confirm the reminder is injected — however, **silence is normal when the markers are fresh and the tree is clean** (2026-07-16 noise re-revision — no status line before the due date). The definitive verification is whether the full-check instruction appears in the marker-absent state (first install) (the hook uses `$PWD` paths on the premise that SessionStart cwd = project root — if nothing appears, check that premise first). **Fallback**: because of a possible issue where repo-local config.toml activation does not take effect in interactive mode (openai/codex #17532), if nothing appears, merge `[features] codex_hooks = true` into `~/.codex/config.toml` (global, preserving existing keys) and re-check. If the installation site does not use Codex, skip (the files remain in a harmless inactive state).
- **Line-ending (CRLF) verification**: Confirm the first line of SKILL.md is `---` without CR — with CRLF, frontmatter parsing breaks so **every skill shows in the list as name-only (no description) and auto-triggering dies**. `.gitattributes` enforces LF, but repositories cloned before its introduction only pick it up after `git config core.autocrlf false` followed by re-checkout via `git rm -rf --cached . && git reset --hard`. Check: `git config core.autocrlf` (must be false/input), `file .agents/skills/metaskill/SKILL.md` (must show no CRLF marker).

### 2. Create untracked directories

Create `_workspace/`, and create the project space using **the default convention (`project/`) as the proposed value** (keep it if it already exists). If the step-5 interview chooses a different path convention, adjust accordingly and update `.gitignore` together — the `project/` entry in the shared `.gitignore` assumes the default convention. Confirm `.gitignore` covers the untracked elements + `REGISTRY.md` + `.agents/projects/`.

### 3. Auxiliary tool installation (default-install — install every missing item; the procedure continues even on failure)

**Every item below is installed by default when missing** — check first, and if absent, proceed straight to install without asking per item (user decision 2026-07-23). §3-derived prescriptions stay as stated per item: telemetry blocking and no-external-DB-sync are applied by default, while existing-config conflicts (e.g. a different `core.hooksPath`, already-set settings keys) still require user confirmation before overwriting. Only genuine blockers (offline, permission failure, or the user explicitly declining mid-run) turn an item into a skip, and every skip lands in the completion report with its reason.

#### 3a. agentsview (default)

A session-history search, cost-tracking, and secret-scanning tool. harness-review's signal measurement (repeated requests/failures) and post-hoc secret verification use it as the primary data source.

> **Caution — this tool is not in model knowledge**: agentsview is a recent tool (2026) and may be absent from training data. **Do not conclude from memory that "no such CLI exists"** — evidence of existence: https://github.com/kenn-io/agentsview (release binaries exist). Confirm by actually running the install commands.

1. Check whether installed: both `agentsview version` **and** `agentsview skills list` must succeed to count as "installed" — if they succeed, skip to step 3 (DB verification). **Two pitfalls**: ① the desktop app (dmg/AppImage/setup.exe) is a **separate artifact** from the CLI, so the `agentsview` command may be missing from PATH even with the app present — install the CLI additionally (they can coexist, sharing the same local DB). ② Old CLI versions lack the `skills` subcommand — update by re-running install.sh.
2. Install (**macOS·Ubuntu/Linux·Windows all supported**): macOS/Linux via `curl -fsSL https://agentsview.io/install.sh | bash` or `brew install --cask agentsview` (macOS); Windows via `powershell -ExecutionPolicy ByPass -c "irm https://agentsview.io/install.ps1 | iex"`. **If install.sh is blocked or fails, alternative path**: download the OS/architecture-matched binary (`linux_amd64.tar.gz`, `darwin_arm64.tar.gz`, `windows` zip/exe, etc.) from GitHub Releases (`https://github.com/kenn-io/agentsview/releases`), extract, and put it on PATH (sha256 checksums provided). Add `AGENTSVIEW_TELEMETRY_ENABLED=0` to the shell profile by default (session logs may contain company data — §3-consistent; if the user wants telemetry on, they say so).
3. **Local DB initialization/verification (defaults pinned)**: Run the first sync with `agentsview daemon start` and confirm the local SQLite DB was created at `~/.agentsview/` (if the location must change, `AGENTSVIEW_DATA_DIR` — either way, **inside this machine**). Subsequent syncs are automatic — **the SessionStart hook (`agentsview-daemon.py`) guarantees daemon startup whenever a session opens**, and the running daemon watches session files and syncs in real time (no manual sync needed). **Do not configure external DB sync (`pg push`, remote DuckDB/Quack)** — session logs may contain company data/secrets, so not sending them off-machine is consistent with the §3 guardrails. If `~/.agentsview/config.toml` already contains `[pg.*]` targets, notify the user.
4. Install the finding-history skill **globally**: `agentsview skills install` (targets `~/.claude/skills/`·`~/.agents/skills/`) — enables agents to search past sessions. **Do not install into this workspace with `--project`** (root AGENTS.md §11: external tool skills go global — prevents installation-site tool artifacts from becoming commits in the shared repository via the symlinks).
5. On install failure, offline, or user refusal, skip and note the fact in the completion report — harness-review still operates without agentsview using the existing observation methods.

#### 3b. defuddle (default — web content extraction)

The CLI used by the `defuddle` skill. It extracts only the main content from web pages, reducing tokens versus WebFetch (removes nav/ads/sidebars). Check with `command -v defuddle`; **if missing, install globally with `npm i -g defuddle`**.

- Failure is harmless: even uninstalled, the `defuddle` skill automatically falls back to WebFetch — so on offline, missing global npm permission, or user refusal, skip and note it in the completion report.
- Install **globally only** (`npm i -g`) — do not place it project-local in this workspace (external tools go global, consistent with root AGENTS.md §11).

#### 3c. context7 MCP (default — library documentation lookup)

The MCP server used by the `context7` skill. It queries **version-specific, up-to-date documentation** for libraries/frameworks/SDKs in real time, eliminating memory-based wrong answers (deprecated APIs, changed configuration).

- Check registration: see whether `context7` appears in `claude mcp list`. **If not, register at user scope (global)**: `claude mcp add context7 --scope user -- npx -y @upstash/context7-mcp`. It takes effect **from the next session** (the CLI loads MCP at session start).
- Failure is harmless: even unregistered, the `context7` skill automatically falls back to WebFetch/WebSearch (same nature as defuddle).
- Register at **user scope only** — do not commit it into this workspace as `.mcp.json` (project scope). MCP is an installation-site-specific element, so keeping it out of git like REGISTRY.md·`.agents/projects/` is consistent with ADR 005, and since this harness opens nearly every session at the root (§12), a global registration surfaces in any project's work.
- If offline, blocked by network policy, or refused by the user, skip and note it in the completion report.

> **SuperClaude leftover MCP caution**: if the `magic`·`sequential-thinking` MCP servers planted by SuperClaude in the past remain, they are removal targets under this installation site's policy (sequential-thinking is superseded by native thinking; magic has no confirmed real use — decided 2026-07-18). If found in `claude mcp list`, notify the user, and on approval remove with `claude mcp remove <name> --scope user`. Keep `playwright`·`context7`.

#### 3d. Claude Code global recommended settings (default)

Global settings that help session observability/retention. Put all of them in **`~/.claude/settings.json` (per-machine)** — they are personal display/retention preferences, not the tracked harness `settings.json` (policy) (same layer as hooksPath·global MCP registration). **Apply each unset item by default**, preserve existing keys, and validate the JSON by parsing after applying. **If a key is already set, do not overwrite — keep the existing value** (an existing value is a prior user choice). If the user declines an item mid-run, skip and note it in the completion report (leaving it unset is harmless).

**① Always-on context display (statusLine)** — Displays how much context (tokens) has accumulated in the session, near the input box at all times, so the user can tell at a glance whether auto-compact is approaching.
- **Codex**: tokens/context are **displayed at all times by default** in the TUI footer — nothing to configure (no related toggle in `config.toml`). Inform the user it is already on.
- **Claude Code**: **there is no native toggle**, so a statusLine script is needed. It reads `model.display_name`·`context_window.used_percentage`·`total_input_tokens`·`context_window_size` from the stdin JSON and prints a single line (falling back to `[claude]` without crashing on any input). To apply:
  1. Copy the single-source script: `cp .agents/skills/harness-install/references/claude-statusline.py ~/.claude/statusline.py` (python3 using only the standard library — guards against missing jq; same `python3` as the harness hooks). Only the single source of the script is tracked by the harness.
  2. Merge `statusLine` into `settings.json`: `{"type":"command","command":"python3 ~/.claude/statusline.py","padding":0}`.
  3. Pipe sample JSON in and confirm one-line output (normal·null·warning·broken input). Displays from the next render. Even unset, details are available via `/context`.

**② Transcript retention extension (cleanupPeriodDays)** — The auto-deletion period for session transcripts. The default **30 days** is short for audits/tracing past sessions; if unset, apply `"cleanupPeriodDays": 90` in `settings.json` by default (costs only a little more disk; adjust to 90–365 if the user names a period).
- **Codex**: retains sessions/history **in full, indefinitely, by default** — there is no extension setting at all (`[history] persistence` is only save-all/none). Instead, watch out for **bloat** of `~/.codex/sessions`·`~/.codex/log/codex-tui.log` (cleanup is a one-off chore, not a standing setting). Inform the user that retention needs no touching.

#### 3e. rtk (default — command output token compression proxy)

A Rust CLI where `rtk <cmd>` runs the command on your behalf and compresses the output (e.g. git status ~3,000→~600 tokens), reducing context consumption (Apache-2.0, adoption design: docs/proposals/2026-07-22-rtk-adoption.md). Its surface overlaps with this workspace, where kubectl·log·git·test output is heavy. Failure is harmless — nothing dies without it.

1. Check with `command -v rtk`; **if missing, install** (global — commit nothing to the workspace): macOS `brew install rtk` (core formula — README-verified path); Linux via GitHub Releases binaries or `cargo install --git https://github.com/rtk-ai/rtk` (beware the same-named unrelated package on crates.io — the README warning is real).
2. **Explicitly disable telemetry**: add `RTK_TELEMETRY_DISABLED=1` to the shell profile — the official docs contradict each other on the default (README opt-in vs DISCLAIMER collect-by-default), so explicit blocking is consistent with §3 (same prescription as agentsview).
3. Register hook mode: `rtk init -g` — adds a PreToolUse(Bash) rewrite hook to the global `~/.claude/settings.json` + an `@RTK.md` import to `~/.claude/CLAUDE.md` (global targets, unrelated to tracked harness files). Verify hook integrity with `rtk verify`. **Codex mode is on hold** — it is a global AGENTS.md behavioral-instruction patch rather than a hook, so effect/consistency are weak (judgment table in the proposal doc).
4. **Explain the evidence rule** (root §13-2): verification commands for completion evidence must be left as raw output, not compressed output — `rtk proxy <cmd>` (passthrough), or check the tee raw output auto-saved on failure (`~/.local/share/rtk/tee/`).
5. Three weeks after install, run tool-audit on `rtk gain` measurements to judge keep/remove (§8 ④). On failure/offline/refusal, skip and note it in the completion report.

### 4. Scan existing projects

List the subdirectories under `project/`, and for each collect observable facts (substructure, whether it is a git repository, harness presence — judged by existence of `.agents/projects/<name>/` (root AGENTS.md §12), stack clues). **Fill role/purpose by directly reading each project's README/docs and summarizing** — if there are no docs, write "미확인" (unconfirmed). **Do not fill by guessing** — mixing observation with guesswork makes the entire registry untrustworthy.

### 5. Clarification interview

Show the scan results (including role summaries read from docs) and confirm with the user: **installation profile (개인/사내, i.e. personal/corporate — root AGENTS.md §5)**, registry granularity (grouped vs individual), and this site's path convention (default: `project/<name>/` + independent git repositories). If the profile is **사내 (corporate)**, explain its meaning alongside — this repository (tracked harness files) is not modified/committed/pushed, and harness improvements are recorded in the `_workspace/harness-updates.md` pending queue to be applied at the personal installation site. **Do not ask about roles** (already filled by document observation — reflect only user corrections). **Do not ask about related projects** — they are updated when projects are actually woven together in real work (root AGENTS.md §1). If there are no projects yet, start with an empty table.

### 6. Generate REGISTRY.md

Generate with this structure: untracked-warning header → **installation profile (개인/사내 — if 사내, append the one-liner "하네스 수정·푸시 금지, 개선은 대기 큐")** → path convention (this site) → registry table (name/path/stack/role/related projects/harness presence) → change history (initial 1 row). **The initial value of the related-projects column is "미기록" (unrecorded)** — leave a footnote under the table saying it gets filled through real-work observation. Mark values that could not be confirmed explicitly as "미확인" (unconfirmed) and leave a warning against making routing assumptions from them.

### 7. Completion criteria

- [ ] 2 symlinks healthy (no real files under `.claude/`)
- [ ] Global `core.hooksPath` points to `.agents/githooks` (if unregistered/refused, the reason is in the completion report)
- [ ] (If Codex is used + macOS/Linux site) reminder injection confirmed in a new Codex session (full-check instruction when markers are absent — silence is normal with fresh markers + clean tree, 2026-07-16) — activation is committed in the repo (`.codex/config.toml`) so no separate registration; if nothing appears, `~/.codex/config.toml` fallback (#17532) (if Codex unused/Windows, the reason is in the completion report)
- [ ] SKILL.md line endings are LF — each skill's description appears in the `/skills` list (name-only means a CRLF/frontmatter problem)
- [ ] agentsview installed (default-install) + local SQLite DB (`~/.agentsview/` or `AGENTSVIEW_DATA_DIR`) creation confirmed + external DB sync unset + finding-history skill installed globally (if skipped, the reason is in the completion report)
- [ ] defuddle installed (default-install; if skipped, the failure/refusal reason is in the completion report — absence is harmless, the `defuddle` skill falls back to WebFetch)
- [ ] context7 MCP present in `claude mcp list` (user scope, default-install; if skipped, the reason is in the completion report — absence is harmless, the `context7` skill falls back to WebFetch/WebSearch). If SuperClaude leftovers magic·sequential-thinking exist, removal was offered
- [ ] Claude Code global recommended settings (3d) applied by default — ① always-on context display (`statusLine` in `~/.claude/settings.json` + `~/.claude/statusline.py`), ② transcript retention extension (`cleanupPeriodDays`, default 90). Already-set keys were kept; any user refusal/skip reason is in the completion report. For Codex, it was explained that context display is on by default and retention is indefinite by default (neither needs configuring)
- [ ] rtk installed (default-install) + telemetry disabled (`RTK_TELEMETRY_DISABLED=1`) + hook mode registered (`rtk init -g`, `rtk verify` passing) + evidence rule explained; if skipped, the reason is in the completion report — absence is harmless
- [ ] REGISTRY.md exists + **installation profile (개인/사내)** + path convention + table + change history (if corporate profile, the no-modify/no-push meaning was explained)
- [ ] REGISTRY.md·project/ do not appear in `git status` (ignore confirmed)
- [ ] Unconfirmed items are honestly marked "미확인"

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| New installation site | No REGISTRY.md → routing impossible, arbitrary work begins | Installation completed via a fixed procedure before work |
| Symlinks | Left broken → `.claude/` real-file bypass occurs | Verified/recovered in step 1 |
| Registry quality | Guesswork mixed in | Observation and interview separated; unconfirmed marked honestly |
