#!/usr/bin/env python3
"""Contract: blind liveness sources are reported as unverified, and session files stay out of the
stopped test until it is redesigned (2026-11-27 Windows/Pi case; two drafts keyed on session files
made every Claude/Codex resume fail — spec 2026-11-28-inflight-stopped-test-cli-class).
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SURVEY = ".agents/skills/orchestrate/references/inflight-survey.md"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def stopped_test_sentence(text):
    return [l for l in text.split("\n") if l.startswith("Exclude from the overlap set:")][0]


class InflightSurveyContract(unittest.TestCase):
    def test_blind_source_is_unverified_not_none(self):
        text = read(SURVEY)
        for phrase in ("Codex and Pi peers never appear in it",
                       "is reported \"unverified for that class\", never \"none\"",
                       "Get-CimInstance Win32_Process",
                       "It is not a conjunct of the stopped test"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_stopped_test_does_not_key_on_session_files_or_unrecorded_cli(self):
        sentence = stopped_test_sentence(read(SURVEY))
        for banned in ("session file", "which CLI", "last 30 minutes", "after the note's time, and no session"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, sentence)

    def test_pending_redesign_spec_exists(self):
        self.assertTrue((ROOT / "docs/specs/2026-11-28-inflight-stopped-test-cli-class.md").is_file())

    def test_infra_review_names_review_mode_for_tier_gate(self):
        self.assertIn("The issuing prompt states `review mode` verbatim",
                      read(".agents/skills/team-review/SKILL.md"))
        self.assertIn("review-tier: design", read(".agents/agents/infra-specialist.md"))


if __name__ == "__main__":
    unittest.main()
