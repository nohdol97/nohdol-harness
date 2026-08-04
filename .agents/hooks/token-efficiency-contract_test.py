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
        self.assertIn("150k", text)
        self.assertIn("completed task boundary", text)
        self.assertIn("Never rotate mid-task", text)
        for phrase in ("evidence", "decisions", "next step", "unverified scope"):
            self.assertIn(phrase, text)

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
            "autoloop", "carryover", "context7", "defuddle", "doc-writer",
            "harness-review", "metaskill", "orchestrate", "release",
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
            "harness-review": ("진화", "하네스 리뷰"),
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
            "branch-workflow": ("never auto-merge", "never push directly to main"),
            "context7": ("Anthropic/Claude API", "model-ID", "general programming"),
            "harness-review": ("harness-native usage", "tool-audit"),
            "tool-audit": ("harness-native usage", "harness-review"),
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
                       "team-review", "metaskill", "Interview-first",
                       "comprehension", "QA/test-and-fix", "design → `architect`",
                       "mandatory §3 guardrail confirmations",
                       "diff reading guide"):
            self.assertIn(phrase, text)

    def test_budget_preserves_mandatory_safety_verification(self):
        text = read(".agents/skills/orchestrate/SKILL.md")
        for phrase in ("safety, security, infra, and spec verification remain mandatory",
                       "independence from the author requires a different owner"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
