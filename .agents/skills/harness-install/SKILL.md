---
name: harness-install
description: "Bootstrap this harness after clone: verify symlinks, create untracked workspaces, scan projects, interview, and generate installation-specific REGISTRY.md. Use when REGISTRY.md is missing or for 하네스 설치, 초기 설정, 새 컴퓨터 세팅. Re-run: harness-install, install, bootstrap, setup, 설치, 초기화."
---

# harness-install — New Installation Site Bootstrap

## Why this skill

This harness is not complete by cloning alone. **The installation-site-specific elements (REGISTRY.md, `.agents/projects/`, `project/`, `_workspace/`) are intentionally absent from git** (ADR 002·005·006). Starting work without this procedure leaves no routing basis (REGISTRY.md), making cross-project judgment impossible, and produces the bypass where real files appear under `.claude/` while symlinks are broken.

**A session without REGISTRY.md is in an installation-incomplete state** — even when other work requests come in, guide the user to this skill first.

## Procedure

### 1. Symlink, line-ending, and git hook layer verification

- **Symlinks**: Verify `readlink .claude/agents .claude/skills` points to `../.agents/agents`, `../.agents/skills`. If broken, recreate (`ln -sfn`); in environments where symlinks are impossible, substitute a sync script and record that fact in an ADR (root AGENTS.md §11). On Windows, if the symlinks were cloned as **plain files containing the path string**, enable developer mode or run `git config core.symlinks true` and re-checkout.
- **git hook layer registration (tdd-gate tool-agnostic enforcement — ADR 014·015)**: Register `git config --global core.hooksPath <root absolute path>/.agents/githooks`. This is the **sole enforcement layer** of the §13 TDD gate (unification — ADR 015), so an unregistered machine is a gate-less state, and global git config does not propagate through the repository, so it must be caught at install time (subsequent gaps are watched by the harness-review weekly integrity check). **If a different value is already set, do not overwrite — confirm with the user** (possible conflict with an existing hook system). Verification: check `git config --global --get core.hooksPath`, then pass `python3 .agents/githooks/tdd-gate_test.py`.
- **Codex session hook verification (macOS·Linux; Windows unverified, ADR 031)**: project config trust and exact hook-definition hash trust are separate. Clone alone activates neither. If this site uses Codex: ① accept the normal repository trust prompt, ② open `/hooks`, review the tracked definitions, and trust their exact hashes (editing a definition invalidates that approval), ③ run `python3 .agents/hooks/integrity-check.py` to verify the canonical `hooks` key, 64KiB headroom, inline SessionStart·PreToolUse·PostToolUse handlers, and absence of `.codex/hooks.json`, then ④ open a new session and confirm the marker-absent SessionStart reminder reaches developer context. If the smoke is silent despite due markers, inspect `/hooks` first for an untrusted hash; ordinary silence is normal while markers are fresh and the tree is clean. If the site does not use Codex, skip the runtime smoke; config stays inert until both trust gates pass.
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
  1. Copy the single-source script: `cp .agents/skills/harness-install/references/claude-statusline.py ~/.claude/statusline.py` (python3 using only the standard library — guards against missing jq; same `python3` as the harness hooks). **jq being default-installed (3h) does not relax this** — that install is best-effort, so this per-render path must survive a skipped machine. Only the single source of the script is tracked by the harness.
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

#### 3f. GitHub CLI — gh (default)

**Harness procedures presume gh**: branch-workflow (`gh pr create`), work-tracker (GitHub Issues epic/progress), and the doc-writer PR flow all call it — a machine without gh forces fragile workarounds (e.g. extracting tokens from `~/.git-credentials` for raw curl, observed 2026-07-23, corporate machine — credential handling to avoid, §3-adjacent).

1. Check with `command -v gh`; **if missing, install**: macOS `brew install gh`; Linux via the official apt/dnf repo (docs: https://github.com/cli/cli#installation); Windows `winget install GitHub.cli`.
2. **Auth check**: `gh auth status`. If unauthenticated, **the user runs `gh auth login` themselves** (interactive browser/token flow — in a Claude session, suggest typing `! gh auth login`). Never extract or copy tokens from `~/.git-credentials` or elsewhere on gh's behalf (§3 — secrets are never recorded or moved by the harness); if `GH_TOKEN` is already exported, gh uses it as-is.
3. On failure, offline, network policy block, or user refusal: skip and note it in the completion report — PR steps then degrade to `git push` + manual PR creation guidance (branch-workflow's documented fallback), and work-tracker falls back to the repo's `docs/backlog.md` store (state this degradation in the report).

#### 3g. claude-video — `/watch` video comprehension skill (default)

A **direct-invocation-only** skill (MIT, bradautomates/claude-video) that lets Claude actually watch a video: `yt-dlp` fetches captions/downloads, `ffmpeg` extracts scene-aware frames (with a dedup pass + duration-scaled frame budget), and Claude `Read`s frames + a timestamped transcript. Handles URLs (YouTube/Loom/TikTok/X/…) and local files (`.mp4/.mov/.mkv/.webm`). Fills a genuine gap — no harness asset can watch video (defuddle=web text, context7=docs). Adoption design: docs/proposals/2026-07-25-claude-video-adoption.md.

1. Install (global — nothing enters the tracked repo, §11):
   - **Claude Code**: the two commands are interactive slash commands the **user runs**: `/plugin marketplace add bradautomates/claude-video` then `/plugin install watch@claude-video`. **Corporate/marketplace-blocked fallback** (사내 networks often block the plugin marketplace): `npx skills add bradautomates/claude-video -g` (the agentskills CLI also targets Claude Code's `~/.claude/skills`), or manual `git clone` + `ln -s <repo>/skills/watch ~/.claude/skills/watch`. If npm/GitHub are also blocked, skip with reason.
   - **Other CLIs**: `npx skills add bradautomates/claude-video -g` (global). Runtime deps `yt-dlp`·`ffmpeg` auto-install on first `/watch` (macOS `brew`; Linux/Windows print the exact commands). Proceed after user confirmation.
2. **Direct-invocation-only routing (mandatory — user decision 2026-07-25)**: `/watch` runs only on the user's explicit `/watch …`, **never auto-routed** (even when a video URL is pasted with a summarize request). Documented routing policy (we do not edit the external plugin's global frontmatter, §11), enforced by §7 precedence + the CLAUDE.md routing note. Reason: keeps the frame→image-token cost opt-in-per-use.
3. **§3 runtime caveat (state it at install)**: frames go to Claude (baseline, like any screenshot), but the **Whisper fallback egresses audio** to a third party (Groq `whisper-large-v3` / OpenAI `whisper-1`) when a video has no captions (local files, TikTok, some Vimeo). **사내 (corporate) profile or any sensitive/internal recording → run with `--no-whisper` (frames-only) or captions-only public videos** — do not ship internal-recording audio to an external Whisper API (§3). 개인 (personal) profile on public/own content → Whisper is acceptable. API keys live in `~/.config/watch/.env` (mode 0600) — never copy them elsewhere (§3).
4. On failure, offline, or user refusal: skip and note it in the completion report — absence is harmless (a direct-invocation convenience, not a harness dependency).

#### 3h. jq (default — JSON query)

The standard JSON query CLI. This procedure itself parses JSON to verify what it applied (3d's settings merge, and the settings cascade it validates by parsing), and ad-hoc config inspection recurs across sessions; without jq each key-scoped read becomes a throwaway script (measured 2026-07-26: one `/doctor` run authored 5,010 characters of python for reads jq answers in one line). Resident context cost is zero — a plain CLI binary loads nothing into the session, unlike a plugin or skill. **Session-history measurement is not this tool's job** — that is agentsview's (3a), which tool-audit and harness-review call directly.

1. Check with `command -v jq`; **if missing, install**: macOS `brew install jq`; Linux `apt install jq` / `dnf install jq`; Windows `winget install jqlang.jq`.
2. **Boundary with rtk (3e)**: both read files, so the axis is survey vs extraction — rtk's `json` shrinks a whole file to fit a look (`--keys-only` lists keys and masks values), jq answers a specific question about it. Reach for rtk when you do not yet know what is in the file, jq when you know which key you want. rtk's hook does not rewrite `jq` (absent from its command list), so the two never interfere.
3. **Does not relax the dependency-free invariant of always-run scripts**: `claude-statusline.py` (3d①) and the git-gate chain (`.agents/githooks/` POSIX-sh shims calling `.agents/hooks/*.py`) stay on the shell and standard-library python3 they already use, and must never be rewritten to call jq. Default-install is best-effort, so a machine that skipped this step would otherwise get a silent gate or render outage.
4. **Secrets caution (§3) — applies to the path, not the tool**: settings files and `~/.claude.json` carry `env`/`headers` values, and a whole-file read exposes them whichever tool prints it (`rtk json <file>` without `--keys-only` prints values too). Query only the keys the task needs; never dump a whole file.
5. On failure, offline, or user refusal: skip and note it in the completion report — absence is harmless (python3 remains the fallback).

### 4. Scan existing projects

List the subdirectories under `project/`, and for each collect observable facts (substructure, whether it is a git repository, harness presence — judged by existence of `.agents/projects/<name>/` (root AGENTS.md §12), stack clues). **Fill role/purpose by directly reading each project's README/docs and summarizing** — if there are no docs, write "미확인" (unconfirmed). **Do not fill by guessing** — mixing observation with guesswork makes the entire registry untrustworthy.

**Knowledge source detection (observation only — the connect/skip decision belongs to step 5)**: a recorded knowledge source lets design-stage work consult curated notes (root AGENTS.md §7 rule 8). Detect in three steps, because existence does not imply readability:

1. `test -L <known link>` — e.g. `~/nohdol-study/vault` at this author's sites. If the site keeps its root at a real directory instead, this simply reports "not detected" and step 5's question picks it up — a safe degradation, not a failure
2. `test -r <path>/index.md` — the link resolves and an entry point exists
3. `head -c 40 <path>/index.md` — **actual bytes come back** (wrap with a timeout; a placeholder file can block on a network fetch rather than fail fast)

**Step 3 is mandatory, never conditional.** You cannot know in advance whether a root is cloud-synced: macOS Google Drive is a FileProvider mount that never appears in `mount`, so the link and directory can look perfectly healthy while files are unreadable (offline, signed out, not yet mirrored). `test -r` is an `access()` permission check and passes on placeholders whose later read fails — only real bytes settle it. Note that this probes one file; cloud roots materialize selectively, so it rules out the trivially broken case rather than guaranteeing every entry point reads. Record what each step showed and connect nothing yet.

### 5. Clarification interview

Show the scan results (including role summaries read from docs) and confirm with the user: **installation profile (개인/사내, i.e. personal/corporate — root AGENTS.md §5)**, registry granularity (grouped vs individual), and this site's path convention (default: `project/<name>/` + independent git repositories). If the profile is **사내 (corporate)**, explain its meaning alongside — this repository (tracked harness files) is not modified/committed/pushed, and harness improvements are recorded in the `_workspace/harness-updates.md` pending queue to be applied at the personal installation site; **sub-project repositories are unaffected — they keep the normal commit/push flow on any profile** (root AGENTS.md §5). **Do not ask about roles** (already filled by document observation — reflect only user corrections). **Do not ask about related projects** — they are updated when projects are actually woven together in real work (root AGENTS.md §1). If there are no projects yet, start with an empty table.

**Corporate carry-in**: ask whether projects built at this install site get **carried into a corporate environment for follow-up work** (connecting internal model endpoints, registering on an on-prem cluster, wiring internal CI/CD and auth). This is not derivable from the profile — 개인 marks who may edit the harness, not where the output ends up, and a personal machine may hold purely personal projects, purely carry-in projects, or both. On yes, write the 「사내 반입 경계」 section in step 6 and confirm its classification table against the user's actual environment (**axes, not instances** — record "사내 LLM 엔드포인트", never a hostname, cluster name, or internal app name; public product names are fine; REGISTRY.md is untracked but the axes propagate into tracked specs). On no, omit the section: both downstream consumers key off its presence, so its absence is the off switch. Do not ask this per project — that question belongs to project creation (`metaskill` scaffold §1.1); here it is asked once for the site.

**Knowledge source**: present the step-4 detection result and ask **only whether to connect it**. The path is observable; the intent is not — that is what makes this a legitimate question under the ask-nothing-observable rule above. If nothing was detected, ask whether a knowledge root exists elsewhere: **any directory with a curated index file qualifies**. Obsidian is not required, neither is the study harness — accept an arbitrary path so sites that keep notes elsewhere are not shut out. If the user declines or no root exists, that is a **confirmed absence**, not an unknown; record it as such so later sessions stop re-asking. If the profile is **사내 (corporate)**, put the actual decision content in front of the user rather than a reassurance: content read from the root **enters this machine's model sessions**, and the triggers are document-producing ones, so it can reach specs, PRs, and issues unless the outbound contract below holds. The question is therefore whether that store's material may enter this machine's sessions at all — the user's call, never a default.

### 6. Generate REGISTRY.md

Generate with this structure: untracked-warning header → **installation profile (개인/사내 — if 사내, append the one-liner "하네스 수정·푸시 금지, 개선은 대기 큐")** → path convention (this site) → **「사내 반입 경계」 section (only if the interview answered yes)** → **knowledge source section** → registry table (name/path/stack/role/related projects/harness presence/반입) → change history (initial 1 row).

The **「사내 반입 경계」 section** records what gets built here versus what waits for the corporate environment: a classification table, the one-line decision rule (*"사내에 이미 구축된 상태를 봐야 정할 수 있는가?"*), and three handover principles — no corporate assumptions hardcoded, the cut built as an adapter seam rather than an omission, and unimplemented follow-up paths failing loudly with a README carry-in checklist. Close it with the outbound caution: the section's items are install-site data, so tracked harness files, specs, and commits carry only generalized axes, never internal stack names. Downstream consumers are `metaskill` `references/scaffold.md` §1.1 (the per-project question) and the doc-writer spec template (which places the three principles into 비목표 / 인터페이스 / 완료 기준). **Both skip silently when the section is absent**, so omitting it here is what makes an install site with no corporate carry-in stay unbothered — and, conversely, a site that needs it and lacks the section gets no boundary anywhere.

The **knowledge source section** records one of three states: **연결됨** (connected — with the path) / **없음(확인함)** (confirmed absent — §7 clause 8 never fires, and emits no notice either) / **미확인** (unconfirmed — not asked yet; resolved at the next `harness-install` run, which is the only executor, so do not promise a re-check that nothing performs). Splitting the last two matters for the same reason the role column splits them: a checked absence and an unchecked blank are different facts, and merging them makes every later session re-run the interview.

When connected, record the entry points (a curated index for design input; dated/topic curation for post-cutoff developments) and **all four clauses of the usage contract** — a site that ships fewer than four gets a weaker contract than the rule assumes:

1. **Evidence grade**: curated notes, summaries included, are scraped or model-generated text and are never evidence; an item's source URL must be followed before its claim is relied on (§13-2). **A note with no source has no URL to follow** — it may inform design and be cited nowhere.
2. **Outbound `<private>` by default (§3)**: the root informs judgment inside the session, but only the followed primary source is quotable in specs, PRs, issues, or commits — never note text, titles, or paths. Knowledge roots are personal stores that commonly carry work-context material, so treat untagged content as tagged. This clause is what makes the design-stage triggers safe, since they are precisely the document-producing ones.
3. **Envelope on injection (§3)**: excerpts carried into prompts, subagent instructions, or reports get the untrusted marker and the source path, exactly as web content does.
4. **Read scope**: the recorded entry points only — never the root's dotfiles (`.env` and friends), `.obsidian`, or vector/cache directories. A whole-root grep is how a secret ends up pasted into a report (§3).

Prefer recording a **stable symlink** over a deep absolute path when one exists (e.g. `~/nohdol-study/vault`): the owning harness stays the single source for the real location, and moving it there does not strand this file. **The initial value of the related-projects column is "미기록" (unrecorded)** — leave a footnote under the table saying it gets filled through real-work observation. Mark values that could not be confirmed explicitly as "미확인" (unconfirmed) and leave a warning against making routing assumptions from them.

### 7. Completion criteria

- [ ] 2 symlinks healthy (no real files under `.claude/`)
- [ ] Global `core.hooksPath` points to `.agents/githooks` (if unregistered/refused, the reason is in the completion report)
- [ ] (If Codex is used + macOS/Linux site) repository trust accepted, exact hook hashes reviewed/trusted via `/hooks`, R18 passed, and marker-absent SessionStart reminder confirmed in a new session. If Codex is unused or Windows, the unverified runtime smoke is stated in the completion report.
- [ ] SKILL.md line endings are LF — each skill's description appears in the `/skills` list (name-only means a CRLF/frontmatter problem)
- [ ] agentsview installed (default-install) + local SQLite DB (`~/.agentsview/` or `AGENTSVIEW_DATA_DIR`) creation confirmed + external DB sync unset + finding-history skill installed globally (if skipped, the reason is in the completion report)
- [ ] defuddle installed (default-install; if skipped, the failure/refusal reason is in the completion report — absence is harmless, the `defuddle` skill falls back to WebFetch)
- [ ] context7 MCP present in `claude mcp list` (user scope, default-install; if skipped, the reason is in the completion report — absence is harmless, the `context7` skill falls back to WebFetch/WebSearch). If SuperClaude leftovers magic·sequential-thinking exist, removal was offered
- [ ] Claude Code global recommended settings (3d) applied by default — ① always-on context display (`statusLine` in `~/.claude/settings.json` + `~/.claude/statusline.py`), ② transcript retention extension (`cleanupPeriodDays`, default 90). Already-set keys were kept; any user refusal/skip reason is in the completion report. For Codex, it was explained that context display is on by default and retention is indefinite by default (neither needs configuring)
- [ ] rtk installed (default-install) + telemetry disabled (`RTK_TELEMETRY_DISABLED=1`) + hook mode registered (`rtk init -g`, `rtk verify` passing) + evidence rule explained; if skipped, the reason is in the completion report — absence is harmless
- [ ] gh CLI installed (default-install) + `gh auth status` authenticated (auth is run by the user, never token-extracted on their behalf); if skipped, the reason and the PR/issue degradation note are in the completion report
- [ ] claude-video (`/watch`) installed (default-install; Claude Code = user runs the two `/plugin` commands, marketplace-blocked fallback = `npx skills add … -g` or manual clone+symlink; other CLIs = `npx skills add … -g`) + direct-invocation-only routing stated + Whisper §3 caveat stated (corporate/sensitive = `--no-whisper`/captions-only); if skipped, the reason is in the completion report — absence is harmless
- [ ] jq installed (default-install, `command -v jq` resolving) + the rtk boundary (survey vs extraction) and the key-scoped read rule (§3 — never dump a whole settings file with any tool) stated; if skipped, the reason is in the completion report — absence is harmless (python3 remains the fallback, and every always-run harness script stays python3 either way)
- [ ] REGISTRY.md exists + **installation profile (개인/사내)** + path convention + table + change history (if corporate profile, the no-modify/no-push meaning was explained)
- [ ] Corporate carry-in asked once for the site — on yes, the 「사내 반입 경계」 section carries the classification table, the decision rule, the three handover principles, and the outbound caution, and the registry table has the 반입 column; on no, the section is absent (its absence is the off switch, not an omission)
- [ ] Knowledge source recorded in one of the three states (연결됨 / 없음(확인함) / 미확인) — if 연결됨, the three-step read check passed (including actual bytes), the entry points are written, **all four usage-contract clauses are present** (evidence grade incl. the source-less case / outbound `<private>` / injection envelope / read scope — a section short of four ships a weaker contract than the rule assumes), and on a corporate profile the session-entry decision was put to the user
- [ ] REGISTRY.md·project/ do not appear in `git status` (ignore confirmed)
- [ ] Unconfirmed items are honestly marked "미확인"

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| New installation site | No REGISTRY.md → routing impossible, arbitrary work begins | Installation completed via a fixed procedure before work |
| Symlinks | Left broken → `.claude/` real-file bypass occurs | Verified/recovered in step 1 |
| Registry quality | Guesswork mixed in | Observation and interview separated; unconfirmed marked honestly |
