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

    def test_kst_offset(self):  # C9 — 경과 판정의 '오늘'은 KST(UTC+9) 기준
        self.assertEqual(hook.KST.utcoffset(None), datetime.timedelta(hours=9))
        self.assertEqual(hook.today_kst(), datetime.datetime.now(hook.KST).date())

    def test_kst_deterministic_across_date_boundary(self):
        # C9 보강 — UTC 날짜와 KST 날짜가 갈리는 고정 시각으로 검증한다.
        # now(KST) 비교만으로는 UTC 00~15시에 date.today() 회귀를 못 잡는다(감사 HOOK-F3).
        utc = datetime.timezone.utc
        self.assertEqual(
            hook.today_kst(datetime.datetime(2026, 7, 15, 16, 0, tzinfo=utc)),
            datetime.date(2026, 7, 16))  # UTC 15일 16시 = KST 16일 01시
        self.assertEqual(
            hook.today_kst(datetime.datetime(2026, 7, 15, 14, 59, tzinfo=utc)),
            datetime.date(2026, 7, 15))  # UTC 15일 14:59 = KST 15일 23:59


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
        # 서브에이전트 위임 실행 — 메인 루프가 직접 점검하면 첫 응답이 점검에
        # 점유되어 사용자 요청이 밀린다(2026-07-14 사용자 확정)
        self.assertIn("첫 응답에서", msg)
        self.assertIn("서브에이전트", msg)
        self.assertIn("발행", msg)
        self.assertIn("병행", msg)  # 사용자 요청 병행 처리

    def test_full_message_no_record(self):  # C3
        self.assertIn("기록이 없습니다", hook.build_message("full", None, None))

    def test_daily_message(self):  # C2
        msg = hook.build_message("daily", 3, 1)
        self.assertIn("일일 경량", msg)
        self.assertIn(".harness-review-daily-last", msg)
        self.assertIn("첫 응답에서", msg)
        self.assertIn("서브에이전트", msg)

    def test_silent_when_fresh(self):  # C4 재개정(2026-07-16) — 기한 전엔 무출력(노이즈 제거)
        self.assertIsNone(hook.build_message(None, 3, 0))
        self.assertIsNone(hook.build_message(None, 0, 0))


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
            old = (hook.today_kst() - datetime.timedelta(days=8)).isoformat()
            today = hook.today_kst().isoformat()
            self._write(d, hook.WEEKLY_MARKER, old)
            self._write(d, hook.DAILY_MARKER, today)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("전체", out)

    def test_c2_daily_stale_daily_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            recent = (hook.today_kst() - datetime.timedelta(days=2)).isoformat()
            yesterday = (hook.today_kst() - datetime.timedelta(days=1)).isoformat()
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

    def test_c4_all_fresh_silent(self):  # C4 재개정(2026-07-16) — 기한 전엔 무출력
        with tempfile.TemporaryDirectory() as d:
            today = hook.today_kst().isoformat()
            self._write(d, hook.WEEKLY_MARKER, today)
            self._write(d, hook.DAILY_MARKER, today)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_c5_garbage_weekly_marker_full(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, hook.WEEKLY_MARKER, "not-a-date")
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("전체", out)

    def test_c10_unreadable_marker_treated_as_no_record(self):
        # C10 — 마커가 존재하나 읽기 실패(권한 등)면 "기록 없음"으로 취급해
        # 점검을 유도해야 한다(R2 실패 방향). 예외가 main까지 새면 리마인더가
        # 영구 침묵한다(감사 HOOK-F6 — exit 0이라 발견도 안 되는 침묵 사망).
        with tempfile.TemporaryDirectory() as d:
            self._write(d, hook.WEEKLY_MARKER, "2026-07-01")
            self._write(d, hook.DAILY_MARKER, "2026-07-01")
            with mock.patch("builtins.open", side_effect=PermissionError):
                self.assertIsNone(hook.read_marker(d, hook.WEEKLY_MARKER))
                rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("기록이 없습니다", out)  # 침묵이 아니라 전체 모드 유도

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
