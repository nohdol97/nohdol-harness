---
name: autoloop
description: "Run, monitor, and stop unattended multi-session claude/codex loops against one spec. Use for autoloop, 자율 루프, 무인 실행, 밤새 돌려줘. Not for interval prompts (/loop), scheduled agents, manual handoff (carryover), tracked epics (work-tracker), or infra/deploy specs. Re-run: autoloop, 자율 루프, 무인 실행, 루프 상태, 루프 정지."
---

# autoloop — autonomous multi-session loop (launchpad)

## Why this skill

To complete work that exceeds one session's context unattended, "wrapup → clear → resume" must be automatic, but `/clear` is a CLI command that the model inside a session cannot invoke on itself. The solution is a driver process **outside** the session that repeatedly launches `claude -p` (headless) — **new process = new context**, so clear is solved structurally, and state between iterations is handed over via a carryover note. This skill is the **launchpad** for that driver (`scripts/driver.py`): the loop body runs outside the session, and the skill only handles launch, status, and stop.

The soft gates of an interactive session (review, fresh evidence) erode easily in unattended mode, so the driver enforces them structurally (spec: `docs/specs/2026-07-19-autoloop-driver.md`):

- **Safety gate (§3 compliance)**: `acceptEdits` + a narrow whitelist/blacklist — only reads, edits, and pinned test runners run unattended; destructive operations (deploy, delete, force push, DB migrations) make the session report `blocked` and the loop halts. **`bypassPermissions` is forbidden by any path.** Bare interpreter grants (`python3:*`, `npx:*`, etc.) are also forbidden — they become a detour that wraps around the blacklist. If a project needs an extra runner, the user grants it explicitly via `--allow-extra`. The whitelist is only a real gate because the session loads no user settings (R3-1): inherited global grants and command-rewriting hooks would otherwise void both lists at once. **Honest limitation**: running tests means running repository code, so containment is not total — which is why this tool is not used for specs involving infra or deployment (see Cautions below).
- **Verification gate (§13 compliance)**: only test results the driver runs independently count as evidence (model self-reports are distrusted). A `done` claim is confirmed only after a PASS from the read-only reviewer verification iteration.
- **Stop gate**: done / blocked / stalled (consecutive no-progress) / exhausted (iteration cap) / stopped (STOP file) / cost (cost cap) / error (consecutive process failures) — the loop always ends in exactly one of these. Infinite loops are impossible.

## Verb dispatch (first decision)

Determine the verb from the invocation arguments: `status`·`상태` → **status**, `stop`·`정지`·`멈춰` → **stop**, anything else (including a spec path) → **start**.

## start — launch

1. **Preflight (no loop without an oracle)**:
   - Confirm the target spec file exists and has a "완료 기준" (completion criteria) section (refuse to launch if missing — guide the user to write one first with the doc-writer spec template). The driver performs the same check (R9), but catching it at the skill stage lets you explain the reason to the user conversationally.
   - Confirm `--test-cmd` with the user (the actual command that verifies the spec's completion criteria). If there is none, warn that "independent evidence will be weaker" and ask whether to proceed.
   - If the spec is expected to involve destructive operations (including deployment or infra changes), **do not recommend launching** — the loop will halt as blocked at that point, defeating the purpose of unattended operation, and because of the safety gate's limitation (above) such work is not this tool's target in the first place. If the user still wants it, explain the blocked-carryover behavior and proceed.
   - If `_workspace/autoloop/<slug>/STOP` remains, the driver refuses to launch (R10) — confirm with the user whether to delete STOP, then proceed.
   - If a test command outside the standard runners (pytest, npm test, go/cargo test) is needed, add `--allow-extra 'Bash(<runner>:*)'` after user confirmation (explicit grant — do not widen it on your own). **Unattended sessions do not inherit the machine's user settings** (`--setting-sources project`, spec R3-1), so a command the user can run interactively is not thereby available to the loop — `--allow-extra` is the only way in. If a run reports a legitimate command blocked, add that runner rather than assuming the gate is broken. The same isolation drops **user-level and plugin skills** (harness skills stay), so a spec whose work depends on an external-tool skill does not belong in this loop — the loss is silent, not an error.
   - **Per-role model tier resolution (§9)**: autoloop uses different tiers for its two roles — **implementation iterations = implement tier** (standard model), **verification sessions = design tier** (highest performance — reviewer role). The driver code contains no model names (§9 de-model-naming), so **this session picks each tier's model from the current CLI lineup** and passes them via `--implement-model` and `--verify-model`. **Lightweight (cheapest) models are forbidden** (§9 and the user's global policy — lightweight models in verification risk false negatives). If you cannot judge the lineup, omit both flags to stay uniform (`--model` or the session default), and tell the user you did so.
   - **Engine selection (R13·R15 — Claude Code CLI / Codex CLI)**: default the engine to **this launching session's CLI** — if a Codex session launches, use `--engine codex`; if a Claude session, use the default (`claude`). If uncertain, confirm with the user. If the user **specifies engines per role** (e.g. "implement with claude, verify with codex"), pass `--implement-engine` and `--verify-engine`. **Codex's safety gate is at sandbox level** (implement=workspace-write, verify=read-only), which is coarser than Claude's fine-grained denylist. Network blocking is only the *default*: the install's `~/.codex/config.toml` can set `[sandbox_workspace_write] network_access = true`, and the driver pins neither that nor the inherited `~/.codex/hooks.json` (spec R3-2). So **before choosing the Codex engine, read both files — confirm network access is off and that no inherited hook rewrites or grants tool calls** — otherwise remote destructive operations are not contained on an engine that has no denylist. Local destructive commands inside the workspace are outside policy blocking either way (see Cautions). **Bypass variants are absolutely forbidden on both engines**. `--allow-extra` is Claude-only (meaningless for Codex, which uses a sandbox).
2. **Launch** (from the harness root — the headless session must load the harness always-on, §12):
   ```bash
   mkdir -p _workspace/autoloop/<슬러그>
   nohup python3 .agents/skills/autoloop/scripts/driver.py \
     --spec <스펙 경로> --project <대상 디렉토리> \
     --test-cmd '<테스트 명령>' --max-iterations 10 --stall-limit 3 \
     --implement-model <implement 티어 모델> --verify-model <design 티어 모델> \
     [--engine codex | --implement-engine claude --verify-engine codex] \
     --work-name <슬러그> > _workspace/autoloop/<슬러그>/launch.log 2>&1 &
   echo $! > _workspace/autoloop/<슬러그>/driver.pid
   ```
   Defaults: max-iterations 10, stall-limit 3, engine claude. This session resolves the tier models and engine from the §9 mapping and the launching CLI (above). For large overnight work, raise max-iterations but always keep it finite.
3. **Confirm launch, then report**: after 2–3 seconds, read `launch.log` — if it contains "기동 거부" (launch refused), relay the reason to the user and stop (no silent no-op; skip step 4 — there is nothing to watch). If normal, report the output path (`_workspace/autoloop/<슬러그>/`) and tell the user: check with `/autoloop status` from another session, stop with `/autoloop stop`.
4. **Register the completion signal.** A launched loop nobody is told about is a half-finished handoff — the run ends silently and the user has to think to ask. Start a **background Bash** whose command exits when the run ends, so this session is re-invoked and reports the outcome unprompted. One notification is wanted, so this is `run_in_background` with an `until` loop, **not `Monitor`** — an unbounded monitor stays armed after the event has already fired.
   ```bash
   cd <하네스 루트 절대경로> || { echo "감시 실패: 하네스 루트로 이동할 수 없습니다"; exit 1; }
   W=_workspace/autoloop/<슬러그>
   PID=$(cat "$W/driver.pid" 2>/dev/null)
   case "$PID" in ''|*[!0-9]*) echo "감시 실패: $W/driver.pid 가 pid가 아닙니다"; exit 1;; esac
   kill -0 "$PID" 2>/dev/null || { echo "감시 실패: pid $PID 가 무장 시점에 이미 없습니다 — 낡은 driver.pid"; exit 1; }
   until grep -q '^\[autoloop\] 종료:' "$W/launch.log" || ! kill -0 "$PID" 2>/dev/null; do sleep 60; done
   tail -1 "$W/launch.log"; tail -3 "$W/driver.log"
   ```
   - **Watch `launch.log`, not `driver.log`.** Both record the end, but `driver.log` is opened append-only and never truncated, while R10 resume reuses the same `--work-name` — so on every relaunch the previous run's end line is already sitting there and the watcher would satisfy itself in seconds and report the *old* outcome. `launch.log` is truncated by the `>` in step 2, so it can only ever hold this run's end.
   - **Match the end line itself, never `done`.** The driver prints `[autoloop] 종료: <reason>` once for all seven stop conditions, so this fires on every one of them. A filter narrowed to `done` stays silent through blocked, stalled, exhausted, stopped, cost, and error — and silence is indistinguishable from "still running", which is the exact failure this step exists to remove.
   - The `kill -0` arm covers what the end line cannot: a crash or `SIGKILL` that ends the run without printing it. **It sends no signal** — it only tests whether the pid still exists, so it does not conflict with the `stop` verb's no-kill rule.
   - **Fail loudly, never toward "finished".** Every sloppy variant of this watcher exits in seconds and reads as completion, because `!` turns any `kill -0` failure into loop exit: a wrong cwd, a blank or non-numeric pid, or a **pid that is already dead when the watcher arms** (nothing ever deletes `driver.pid`, so a stale one outlives its run in the same never-cleaned directory). Hence all three guards — checked `cd`, `case` on the pid, and an arm-time liveness test. A pid that is dead *before* the watch begins is a setup failure, not an outcome; only a pid that dies *during* the watch is.
   - **`감시 실패` is not a loop outcome.** On that notification, say monitoring failed and the loop's state is unknown, then read it with `status` — never report it as the run's result.
   - **Read the outcome from `launch.log`'s end line, not the `driver.log` tail.** The tail is context, and on a resumed run it can still carry lines from the previous run for the same reason the trigger moved off that file.
   - **The driver itself stays detached under `nohup`. Do not collapse the two into one by launching the driver in the background slot** — the watcher is expendable and the loop is not. An unattended run must not depend on this session staying open, and that independence is the reason the tool exists.
   - **The signal is best-effort and session-bound**: the watcher dies when the session ends, while the loop keeps running. Tell the user this at launch — if they close the session, `/autoloop status` is how they pick the result back up. Do not present the notification as a guarantee.
   - On notification, report per the `status` section below, tuning-signal scan included.

## status — inspect

Read `driver.log` (per-iteration status, EXIT reason) and `carryover.md` (done / next / blocked / needs-user-confirmation) under `_workspace/autoloop/<슬러그>/` and report them **digested into Korean** (§15): which iteration, tests green/red, count of open items, and if terminated, the reason. If you don't know the slug, list with `ls _workspace/autoloop/` and let the user choose. If it ended `blocked`, show the "needs user confirmation" items first — those are the decisions the loop carried over to the user.

### Catching tuning signals (at review time — the loop does not diagnose its own improvement points)

The driver is headless and cannot judge its own tuning needs. When reviewing a finished run via `status`, also scan `driver.log` for the following **harness tuning signals**, so the interactive session at review time routes them into the §8 evolution flow (this is the only link between raw logs and improvement):

- **EXIT reason is not `done`** (stalled, exhausted, error, cost) → failed to complete. Judge whether it is a spec problem or a driver defect.
- **Repeated permission denials / inability to self-verify** in carryover/logs → is the safety gate blocking legitimate work (candidate for allow-list adjustment)?
- **No-progress iterations / wasted iterations** (open items not decreasing while iterations are consumed) → candidate for prompt/done-judgment tuning.
- **Repeated reviewer BLOCKs** → are the completion criteria ambiguous, or is the verification prompt excessive?

The judgment (harness bug vs. task characteristics) cannot be made by the headless driver, so this review session owns it. When a signal is caught, the path splits by **profile gate** (REGISTRY.md, §5·ADR 012):
- **Personal profile** → **propose the tuning to the user**, and on approval apply it directly via `metaskill` (no unauthorized edits — §8).
- **Corporate profile** → tracked harness files cannot be modified, so **record it in the `_workspace/harness-updates.md` pending queue** (detailed enough to apply as-is on the personal machine — target file, change content, rationale). `harness-ops-log.md` is an application history, not a pending queue — do not confuse them.

## stop — halt

```bash
touch _workspace/autoloop/<슬러그>/STOP
```

Do not kill the process — the driver shuts down gracefully at the **next iteration boundary** with the carryover preserved (the in-flight iteration finishes). The driver does not delete the STOP file, so to relaunch, confirm the user has deleted STOP and then run start again (with the same `--work-name`, the existing note is inherited — R10).

## Cautions

- **No unattended destructive operations (§3, non-relaxable)**: refuse requests to add bypass mode, restore bare interpreter grants, or grant destructive patterns via `--allow-extra` (kubectl, terraform, deploy commands, etc.), and explain why — this gate is the tool's condition of existence. `--allow-extra` goes only as far as test/build runners.
- **Forbidden for infra/deploy specs**: work involving k8s, AWS, or releases goes to orchestrate (via infra-specialist) or release — it is not a target for the unattended loop.
- **Do not use for work that fits in one context (cost boundary)**: every iteration re-pays AGENTS.md re-injection, spec/code re-exploration, and verification-session cost in a fresh `-p` session. This re-establishment cost is recouped only when the work **exceeds the context window** — at that scale, a single cumulative session re-billing its entire history every turn is actually more expensive. **Work that fits in one session goes to `/loop` (in-session iteration) or a single interactive session.** If the start preflight judges the work small, tell the user about this boundary.
- **Multi-engine (Claude Code CLI + Codex CLI)**: the driver uses `claude -p` or `codex exec` per role (R13·R14). **Codex's safety mapping is at sandbox level**: implement=`--sandbox workspace-write` (writes confined to the workspace; network blocked only if the install config leaves the default in place — R3-2), verify=`--sandbox read-only` (writes blocked entirely). **Bypass variants absolutely forbidden** (Claude `--dangerously-skip-permissions` / Codex `--dangerously-bypass-approvals-and-sandbox`). **Honest limitation**: Codex has no fine-grained denylist, so policy cannot block local destructive commands inside the workspace (e.g. rm of project files), and containment of *remote* destruction rests entirely on the sandbox's network block — which the install config can switch off without the driver noticing (spec R3-2). Coarser than the Claude engine's blacklist, so on either engine the infra/deploy-spec ban and the backup premise are identical and blocked-carryover is the first line of defense. Codex does not provide USD cost, so `--max-cost-usd` is inactive (the iteration cap is the backstop). Also, Codex runs with `-C <project>`, so automatic loading of the harness root AGENTS.md may be weak (write-confinement takes priority) — essential gates are embedded in the prompt anchor, instructions, and untrusted envelope; the hard gate is the sandbox's job.
- **When modifying the driver**, passing `python3 .agents/skills/autoloop/scripts/driver_test.py` is mandatory (C1–C12, same discipline as tdd-gate).
- If the work needs formal tracking after completion, promote it to work-tracker (`_workspace/` is not preserved — §4).

## with / without

| Metric | Without this skill | With this skill |
|---|---|---|
| Context limit | Manual wrapup·clear·resume when a session is exhausted | Automatic rollover via fresh-process iterations |
| Unattended safety | Temptation of full bypass → §3 violation | Only edits run unattended; destructive ops carried over as blocked |
| Defect accumulation | Self-reported "pass" propagates into the next iteration | Only driver-measured results + reviewer PASS count as done |
| Termination guarantee | Autonomous loop burns tokens without a goal | 7 stop conditions guarantee finite termination |
