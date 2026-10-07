#!/usr/bin/env python3
"""Contract for persistent command evidence and a task-wide full-suite budget."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

class LongCommandContract(unittest.TestCase):
    def test_log_and_suite_policy(self):
        root = (ROOT / "AGENTS.md").read_text()
        self.assertIn("references/test-execution.md", root)
        self.assertIn("one post-change + one final run maximum per task across all agents", root)
        text = (ROOT / ".agents/skills/orchestrate/references/test-execution.md").read_text()
        for term in ("stdout/stderr", "exit code", "never overwrite", "display truncation",
                     "at most once after changes and once at final verification",
                     "shared across host/workers/reviewers", "targeted tests",
                     "timeout/cancellation", "do not reset", "unverified"):
            with self.subTest(term=term):
                self.assertIn(term, text)

    def test_review_uses_same_budget(self):
        text = (ROOT / ".agents/agents/reviewer.md").read_text()
        self.assertIn("task-wide full-suite budget", text)
        self.assertIn("§13-2", text)

if __name__ == "__main__":
    unittest.main()
