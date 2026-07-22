# Agent definition rules — 10-section template

Agent definition files live at `.agents/agents/<name>.md` (`.claude/agents` is a symlink). metaskill and orchestrate follow this template when defining team members.

## frontmatter (4 mandatory fields)

```yaml
---
name: <name>
description: <Pushy formula — verb enumeration + trigger situations + re-run keywords (+ when boundaries overlap with adjacent roles, negative triggers like "Do NOT …" / "excluding ~" recommended — actively blocks misrouting). Written in English; Korean re-run keywords (e.g. 하네스, 리뷰) recommended alongside>
tools: <allowed tool whitelist — least privilege>
tier: design | implement | explore   # model mapping: the table in root AGENTS.md §9 is the only source
---
```

**The CLI does not interpret `tier`** — actual application happens when the orchestrator specifies the `model` parameter per the §9 table at team-member creation (Agent call) time (orchestrate "tier application" rule). Why no concrete model name is pinned in the definition file: model names change over time, but roles do not (§9).

## Codex custom-agent adapter (mandatory for root agents)

Root agents pair the original `.agents/agents/<name>.md` with `.codex/agents/<name>.toml` (ADR 027). The TOML holds only Codex's mandatory fields `name`, `description`, `developer_instructions`, and `developer_instructions` instructs finding the corresponding Markdown from the current working directory upward and **reading the full text before working**. `name` and `description` must exactly match the original frontmatter.

Do not copy the role body, `tools`, or `tier` into the TOML. In particular, do not set `model`, `model_reasoning_effort`, or `sandbox_mode` — pinning them would split the §9 dynamic tiers and the parent session's permissions into a separate source of truth. After creation, verify Markdown↔TOML 1:1, metadata, and contract references with `python3 .agents/hooks/integrity-check.py`.

**The tools field is the number-one guardrail.** Least privilege, minimal tools, explicit exclusion. Reason: a prompt's "don't do it" can be violated, but an absent tool cannot be used. However, **usage-scope restrictions on retained tools (e.g. "Write only for `_workspace/`") are prompt-level constraints, not full enforcement** — do not overstate the guarantee level in the definition document.

**⑨ Supplementary — repository state invariance (citation label: "agent-rules ⑨" — this paragraph is the single source)**: For inspection/verification roles (no Edit — explorer, reviewer, troubleshooter, etc.), Bash must leave repository state (working tree, index, HEAD) unchanged: `git stash`, `checkout/restore`, `reset`, `clean` for comparison purposes are forbidden — even if "stash pop restores it, so it's harmless" seems true, the orchestrator's or parallel work's uncommitted changes may coexist in the same working tree (measured twice on 2026-07-21 — reviewer repeatedly stashing during stacked-branch work). Do before/after comparison with `git diff <ref>..<ref>` and `git show <commit>:<path>`; **diagnosis requiring HEAD movement (`git bisect` etc.) runs in a `git worktree add` isolated copy** and removes it afterward (worktree add/remove leaves the main tree unchanged). Implementation roles (with Edit) are equally forbidden from **comparison-purpose tree manipulation (stash) of anything other than their own deliverables**.

## Mandatory body sections

1. **Core role — scoping**: State what it does together with the boundary of **what it does not do**. (e.g. "the reviewer does not modify code")
2. **Working principles — decision criteria**: Which side to take when two options conflict. (e.g. speed vs accuracy → accuracy) Reason: an agent without decision criteria gives a different answer in every conflict.
3. **I/O protocol**: The inter-agent API contract. Input format, output format, intermediate deliverables at `_workspace/<task>/phase{N}_{agent}_{content}.md`. Specify not only the file output language but also **the language of the final text returned to the orchestrator** — the default is English (root §15, a model-only channel); a Korean exception exists only when the agent's deliverable is a document delivered to the user as-is, i.e. **file = return content** (e.g. integrator final integration report. **architect is not an exception** — only the spec file is Korean; the return text is an English path notice).
4. **Team communication protocol**: To whom, what, and when. SendMessage must state the finding plus the action the recipient should take. Fixed message format (JSON): `{type, severity, file, line, claim, request}`
5. **Error handling — termination conditions**: Concrete failure scenarios and max retry counts. Default: 1 retry; on 2nd failure state the omission and proceed; if 2+ team members fail, disband the team and report to the user.
6. **Collaboration — position in the team**: Who it connects to and in what order (position in the dependency graph).
7. **Quality self-verification**: Self-check checklist before returning output.
8. **Re-invocation guide**: So the harness auto-invokes it again in new sessions — state in which situations/keywords this agent must be used again.
9. *(satisfied by the frontmatter tools)* — reinforce in the body with one line on why tool usage is constrained.
10. *(satisfied by the frontmatter tier)* — reinforce with one line on the tier-choice rationale.
