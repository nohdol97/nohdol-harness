#!/usr/bin/env python3
"""harness-review-reminder 훅 회귀 테스트 — 스펙 완료 기준 C1~C5.

스펙: docs/specs/2026-07-14-harness-review-reminder-hook.md
"""
import contextlib
import datetime
import importlib.util
import io
import os
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "harness_review_reminder_hook", os.path.join(HERE, "harness-review-reminder.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

TODAY = datetime.date(2026, 7, 14)


class DaysSince(unittest.TestCase):
    def test_eight_days(self):  # C1 판정부
        self.assertEqual(hook.days_since("2026-07-06", TODAY), 8)

    def test_today(self):  # C2 판정부
        self.assertEqual(hook.days_since("2026-07-14\n", TODAY), 0)

    def test_missing_or_garbage(self):  # C3·C4 판정부
        self.assertIsNone(hook.days_since(None, TODAY))
        self.assertIsNone(hook.days_since("어제쯤", TODAY))
        self.assertIsNone(hook.days_since("", TODAY))


class BuildMessage(unittest.TestCase):
    def test_due_has_instruction(self):  # C1
        msg = hook.build_message(8)
        self.assertIn("harness-review", msg)
        self.assertIn("8일", msg)

    def test_not_due_silent(self):  # C2
        self.assertIsNone(hook.build_message(0))
        self.assertIsNone(hook.build_message(6))

    def test_no_record_has_instruction(self):  # C3
        self.assertIn("기록이 없습니다", hook.build_message(None))


def run_main_in(tmpdir):
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": tmpdir}), \
         contextlib.redirect_stdout(out):
        rc = hook.main()
    return rc, out.getvalue()


class MainFlow(unittest.TestCase):
    def _write_marker(self, tmpdir, content):
        os.makedirs(os.path.join(tmpdir, "_workspace"), exist_ok=True)
        with open(os.path.join(tmpdir, hook.MARKER_RELPATH), "w", encoding="utf-8") as f:
            f.write(content)

    def test_c1_stale_marker_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            old = (datetime.date.today() - datetime.timedelta(days=8)).isoformat()
            self._write_marker(d, old)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("harness-review", out)

    def test_c2_fresh_marker_silent(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_marker(d, datetime.date.today().isoformat())
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_c3_no_marker_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("기록이 없습니다", out)

    def test_c4_garbage_marker_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_marker(d, "not-a-date")
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("harness-review", out)

    def test_c5_exception_fail_open(self):
        with mock.patch.object(hook.os.path, "isfile", side_effect=RuntimeError), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hook.main(), 0)
            self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
