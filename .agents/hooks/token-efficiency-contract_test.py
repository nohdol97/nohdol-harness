#!/usr/bin/env python3
"""토큰 효율 규범 회귀 — 스펙 2026-07-25-token-efficiency-contract."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def description(rel):
    match = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", read(rel), re.M)
    if not match:
        raise AssertionError("description missing: %s" % rel)
    return match.group(1)


def section(rel, start, end):
    text = read(rel)
    body = text.split(start, 1)[1]
    return body.split(end, 1)[0]


class TokenEfficiencyContractTest(unittest.TestCase):
    def test_orchestrate_declares_budget_reuse_and_mandatory_verification(self):
        text = read(".agents/skills/orchestrate/SKILL.md")
        for phrase in ("Agent-call budget", "Reuse the existing agent thread",
                       "new independent risk axis", "mandatory verification first",
                       "≤2-file low-risk direct implementation=1 reviewer",
                       "3+-file generate-verify=1 implementer + 1 reviewer"):
            self.assertIn(phrase, text)

    def test_delta_packet_and_read_once_contract(self):
        text = section(
            ".agents/skills/orchestrate/SKILL.md",
            "9. **Read once, then pass a Delta packet**",
            "10. **Bound tool and visible output**",
        )
        for phrase in ("already injected root `AGENTS.md`", "content changed",
                       "compaction", "evidence conflicts", "goal", "decisions",
                       "changed files", "diff text/path", "latest test output",
                       "unverified scope"):
            self.assertIn(phrase, text)

    def test_session_rotation_is_only_at_completed_boundary(self):
        text = read(".agents/skills/orchestrate/SKILL.md")
        self.assertIn("**100k tokens or higher**", text)
        self.assertIn("completed task boundary", text)
        self.assertIn("Never rotate mid-task", text)
        for phrase in ("evidence", "decisions", "next step", "unverified scope"):
            self.assertIn(phrase, text)

    def test_session_end_continuation_until_user_stop(self):  # C10 (R4)
        text = section(".agents/skills/orchestrate/SKILL.md",
                       "## Completed-task context rotation", "## Final response format")
        for phrase in ("**Continuation at session end (any context size)**",
                       "whether or not the threshold was reached",
                       "**A stop from the user ends it**",
                       "a successor prompt never re-grants work the user stopped",
                       "or a user stop of the chain",
                       "does not carry over",
                       "This session completed at least one task"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        root = read("AGENTS.md")
        self.assertIn("opens a successor at any context size, until the user stops the chain", root)

    def test_continues_below_threshold_on_every_project(self):  # ADR 064
        text = section(".agents/skills/orchestrate/SKILL.md",
                       "## Completed-task context rotation", "## Final response format")
        for phrase in ("**Continuous run (every project, every installation profile)**",
                       "take the next ready task in this same session",
                       "names one task ends when that task does",
                       "stops only what depends on it", "no peer holds", "§3 confirmation — stops",
                       "ends the run at once", "covers all remaining ready work"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        for path in (".agents/skills/orchestrate/SKILL.md",
                     ".agents/skills/orchestrate/references/inflight-survey.md"):
            self.assertNotIn("sequentially on corporate", read(path))

    def test_session_merge_gate(self):  # ADR 064
        text = section(".agents/skills/branch-workflow/SKILL.md",
                       "## Session merge", "## Worktree cleanup")
        for phrase in ("every installation profile", "PASS on the PR's final head",
                       "could not run → do not merge", "full suite green",
                       "Do not wait for CI", "caused by this change", "--match-head-commit",
                       "never `--admin`", "never `--auto`", "triggers a production deploy",
                       "needs the §3 confirmation first", "stops only what depends on it",
                       "Merge only PRs this session owns", "Clean up in the same turn",
                       "Host self-review does not count", "PR patch is unchanged",
                       "delta review", "never loop", "cause undetermined", "shown unrelated",
                       "unknown trigger on a deployable project → treat as deploying",
                       "are respected", "a precondition fails twice", "a live peer holds overlapping files",
                       "touches credentials or migrates user data",
                       "shows its author stopped", "`headRefOid`"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        cleanup = section(".agents/skills/branch-workflow/SKILL.md", "## Worktree cleanup", "## Edge cases")
        steps = [cleanup.index(c) for c in ("worktree remove <abs-path>   #", "merge --ff-only origin/main   #",
                                            "branch -d <branch>\n")]
        self.assertEqual(steps, sorted(steps))
        self.assertIn("branch --show-current)\" = main &&", cleanup)
        root = read("AGENTS.md")
        self.assertIn("§3 still binds a merge that deploys", root)
        self.assertIn("The owning session merges its own sub-project PR", root)
        for stale in ("let the user merge", "merge stays with the user", "PRs and user merge stay"):
            self.assertNotIn(stale, root)
        self.assertNotIn("The user alone merges", read("CLAUDE.md"))

    def test_tool_and_user_output_contract(self):
        text = section(
            ".agents/skills/orchestrate/SKILL.md",
            "9. **Read once, then pass a Delta packet**",
            "Fixed message format",
        )
        for phrase in ("Keep raw logs in `_workspace/`", "conclusion",
                       "finding index", "evidence pointers", "unverified scope",
                       "`rtk`", "targeted ranges/filters",
                       "raw or tee-preserved output", "1–2 sentences",
                       "result, key evidence, and unverified scope",
                       "safety decisions", "failure analysis"):
            self.assertIn(phrase, text)

    def test_team_review_reuses_same_reviewer_for_delta(self):
        text = read(".agents/skills/team-review/SKILL.md")
        for phrase in ("Agent-call budget", "same reviewer thread",
                       "delta re-verification", "new independent risk axis"):
            self.assertIn(phrase, text)

    def test_every_agent_has_context_economy_contract(self):
        agent_dir = os.path.join(ROOT, ".agents", "agents")
        for filename in sorted(os.listdir(agent_dir)):
            if not filename.endswith(".md") or filename.startswith("README"):
                continue
            text = read(os.path.join(".agents/agents", filename))
            with self.subTest(agent=filename):
                self.assertIn("Context economy", text)
                self.assertIn("already injected root `AGENTS.md`", text)
                self.assertIn("content changed", text)
                self.assertIn("compaction", text)
                self.assertIn("unverified scope", text)

    def test_skill_descriptions_keep_routing_contract(self):
        skill_dir = os.path.join(ROOT, ".agents", "skills")
        bounded = {
            "carryover", "context7", "defuddle", "doc-writer",
            "metaskill", "orchestrate", "release",
            "team-review", "tool-audit", "tool-eval", "work-tracker", "wrapup",
        }
        for name in sorted(os.listdir(skill_dir)):
            rel = ".agents/skills/%s/SKILL.md" % name
            if not os.path.isfile(os.path.join(ROOT, rel)):
                continue
            desc = description(rel)
            with self.subTest(skill=name):
                self.assertIn("Re-run:", desc)
                if name in bounded:
                    self.assertIn("Not for", desc)

    def test_skill_descriptions_keep_representative_positive_routes(self):
        samples = {
            "branch-workflow": ("push to main", "PR 생성"),
            "context7": ("library", "라이브러리 문서"),
            "project-status": ("what changed across projects", "전체 현황"),
            "tool-audit": ("harness-native", "사용 실측"),
            "work-tracker": ("where was I", "하던 작업 뭐였지"),
        }
        for name, triggers in samples.items():
            desc = description(".agents/skills/%s/SKILL.md" % name)
            for trigger in triggers:
                with self.subTest(skill=name, trigger=trigger):
                    self.assertIn(trigger, desc)

    def test_adjacent_routing_boundaries_remain_explicit(self):
        samples = {
            "branch-workflow": ("never --auto/--admin", "never push directly to main"),
            "context7": ("Anthropic/Claude API", "model-ID", "general programming"),
            "tool-audit": ("harness-native usage", "metaskill"),
        }
        for name, boundaries in samples.items():
            desc = description(".agents/skills/%s/SKILL.md" % name)
            for boundary in boundaries:
                with self.subTest(skill=name, boundary=boundary):
                    self.assertIn(boundary, desc)

    def test_claude_keeps_required_anchors(self):
        text = read("CLAUDE.md")
        self.assertTrue(text.startswith("@AGENTS.md\n"))
        for phrase in ("## Harness: root", "Korean", "orchestrate",
                       "team-review", "metaskill", "Autonomous execution",
                       "comprehension", "QA/test-and-fix", "design → `architect`",
                       "Preserve §3 and data-loss confirmations",
                       "diff reading guide"):
            self.assertIn(phrase, text)

    def test_budget_preserves_mandatory_safety_verification(self):
        text = read(".agents/skills/orchestrate/SKILL.md")
        for phrase in ("safety, security, infra, and spec verification remain mandatory",
                       "independence from the author requires a different owner"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
