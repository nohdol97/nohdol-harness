#!/usr/bin/env python3
"""평가 독립성 리뷰 계약 회귀 — 스펙 2026-08-26."""
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def evaluation_section():
    text = read(".agents/skills/team-review/SKILL.md")
    heading = "**Evaluation-independence check (Tests perspective only)**"
    self = text.split(heading, 1)[1]
    return self.split("**Infra domain specialization", 1)[0]


class EvaluationIndependenceContractTest(unittest.TestCase):
    def test_tests_perspective_fires_only_for_validation_design(self):
        skill = read(".agents/skills/team-review/SKILL.md")
        tests_row = next(line for line in skill.splitlines() if line.startswith("| Tests |"))
        self.assertIn("evaluation-independence check below", tests_row)
        text = evaluation_section()
        for phrase in ("eval", "metric", "experiment", "benchmark", "scorer", "holdout"):
            self.assertIn(phrase, text)
        self.assertIn("only when", text)

    def test_tests_perspective_maps_roles_to_external_truth(self):
        text = evaluation_section()
        for phrase in ("model", "scorer", "designer", "dataset", "independent external ground truth"):
            self.assertIn(phrase, text)

    def test_tests_perspective_names_observed_circularity_patterns(self):
        text = evaluation_section()
        for phrase in ("rubric/category", "private recipe", "labeler pool", "curation recipe", "hypothesis", "validator prompt/data"):
            self.assertIn(phrase, text)

    def test_check_reuses_tests_perspective_without_more_calls(self):
        text = evaluation_section()
        self.assertIn("does not add a perspective, reviewer, or fan-out call", text)

    def test_korean_view_exposes_the_boundary(self):
        text = read(".agents/skills/README.ko.md")
        for phrase in ("평가 독립성", "외부 정답", "추가 reviewer 호출 없음"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
