#!/usr/bin/env python3
"""harness-review-reminder 훅 회귀 테스트 — 스펙 완료 기준 C1~C7.

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
    def test_eight_days(self):
        self.assertEqual(hook.days_since("2026-07-06", TODAY), 8)

    def test_today_with_newline(self):
        self.assertEqual(hook.days_since("2026-07-14\n", TODAY), 0)

    def test_missing_or_garbage(self):
        self.assertIsNone(hook.days_since(None, TODAY))
        self.assertIsNone(hook.days_since("어제쯤", TODAY))
        self.assertIsNone(hook.days_since("", TODAY))


class DecideMode(unittest.TestCase):
    def test_weekly_overdue_wins(self):  # C1 — 전체가 일일보다 우선
        self.assertEqual(hook.decide_mode(7, 0), "full")
        self.assertEqual(hook.decide_mode(10, 5), "full")

    def test_no_weekly_record_is_full(self):  # C3
        self.assertEqual(hook.decide_mode(None, 0), "full")

    def test_daily_overdue(self):  # C2 — 주간 이내 + 일일 경과
        self.assertEqual(hook.decide_mode(3, 1), "daily")
        self.assertEqual(hook.decide_mode(3, None), "daily")

    def test_all_fresh_silent(self):  # C4
        self.assertIsNone(hook.decide_mode(3, 0))
        self.assertIsNone(hook.decide_mode(0, 0))


class BuildMessage(unittest.TestCase):
    def test_full_message(self):  # C1
        msg = hook.build_message("full", 8, 0)
        self.assertIn("전체", msg)
        self.assertIn("8일", msg)
        self.assertIn(".harness-review-last", msg)
        self.assertIn(".harness-review-daily-last", msg)  # 전체 완료 시 두 마커 갱신

    def test_full_message_no_record(self):  # C3
        self.assertIn("기록이 없습니다", hook.build_message("full", None, None))

    def test_daily_message(self):  # C2
        msg = hook.build_message("daily", 3, 1)
        self.assertIn("일일 경량", msg)
        self.assertIn(".harness-review-daily-last", msg)

    def test_status_line_when_fresh(self):  # C4 개정 — 기한 전에도 상태 한 줄
        msg = hook.build_message(None, 3, 0)
        self.assertIn("기한 전", msg)
        self.assertIn("3일 전", msg)
        self.assertIn("오늘", msg)  # 일일 0일 전은 "오늘"로 표기
        self.assertIn("harness-ops-log.md", msg)
        self.assertNotIn("지금 실행", msg)  # 점검 지시가 아님


def run_main_in(tmpdir):
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": tmpdir}), \
         contextlib.redirect_stdout(out):
        rc = hook.main()
    return rc, out.getvalue()


class MainFlow(unittest.TestCase):
    def _write(self, tmpdir, relpath, content):
        os.makedirs(os.path.join(tmpdir, "_workspace"), exist_ok=True)
        with open(os.path.join(tmpdir, relpath), "w", encoding="utf-8") as f:
            f.write(content)

    def test_c1_weekly_stale_full_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            old = (datetime.date.today() - datetime.timedelta(days=8)).isoformat()
            today = datetime.date.today().isoformat()
            self._write(d, hook.WEEKLY_MARKER, old)
            self._write(d, hook.DAILY_MARKER, today)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("전체", out)

    def test_c2_daily_stale_daily_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            recent = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            self._write(d, hook.WEEKLY_MARKER, recent)
            self._write(d, hook.DAILY_MARKER, yesterday)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("일일 경량", out)

    def test_c3_no_markers_full_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("기록이 없습니다", out)

    def test_c4_all_fresh_status_line(self):  # C4 개정 — 침묵 대신 상태 한 줄
        with tempfile.TemporaryDirectory() as d:
            today = datetime.date.today().isoformat()
            self._write(d, hook.WEEKLY_MARKER, today)
            self._write(d, hook.DAILY_MARKER, today)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("기한 전", out)
            self.assertNotIn("지금 실행", out)

    def test_c5_garbage_weekly_marker_full(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, hook.WEEKLY_MARKER, "not-a-date")
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("전체", out)

    def test_c8_cp949_stdout_still_outputs(self):  # C8 — 한글 Windows 콘솔(cp949)에서 em dash
        with tempfile.TemporaryDirectory() as d:
            buf = io.BytesIO()
            cp949 = io.TextIOWrapper(buf, encoding="cp949")
            with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": d}), \
                 contextlib.redirect_stdout(cp949):
                rc = hook.main()  # 마커 부재 → 전체 모드 메시지(em dash 포함)
            cp949.flush()
            self.assertEqual(rc, 0)
            # cp949였다면 print가 예외를 던지고 fail-open이 삼켜 무출력이 됐다 —
            # UTF-8 재구성 후에는 메시지가 실제로 출력되어야 한다.
            self.assertIn("리마인더".encode("utf-8"), buf.getvalue())

    def test_c6_exception_fail_open(self):
        with mock.patch.object(hook.os.path, "isfile", side_effect=RuntimeError), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hook.main(), 0)
            self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
