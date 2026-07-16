#!/usr/bin/env python3
"""worklog-reminder 훅 회귀 테스트 — 스펙 완료 기준 C1~C7.

스펙: docs/specs/2026-07-16-worklog-reminder-hook.md
"""
import contextlib
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "worklog_reminder_hook", os.path.join(HERE, "worklog-reminder.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _init_repo(d):
    """user 설정까지 마친 임시 git 저장소에 커밋 1개(a.txt) 생성."""
    def g(*a):
        return subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)
    g("init", "-q")
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "t")
    with open(os.path.join(d, "a.txt"), "w", encoding="utf-8") as f:
        f.write("one\n")
    g("add", "a.txt")
    g("commit", "-qm", "init")
    return g


class BuildMessage(unittest.TestCase):
    def test_c1_dirty_with_branch(self):  # C1
        msg = hook.build_message("feat/login", 3)
        self.assertIn("work-tracker", msg)
        self.assertIn("흐름 2", msg)
        self.assertIn("흐름 3", msg)
        self.assertIn("feat/login", msg)
        self.assertIn("3개", msg)
        self.assertIn("멀티세션", msg)

    def test_c1_dirty_without_branch(self):  # C1 — detached HEAD 등
        msg = hook.build_message(None, 1)
        self.assertIsNotNone(msg)
        self.assertIn("1개", msg)
        self.assertNotIn("브랜치", msg)  # 브랜치 없으면 위치 문구 생략

    def test_c2_clean_is_silent(self):  # C2
        self.assertIsNone(hook.build_message("main", 0))

    def test_c3_git_failure_is_silent(self):  # C3
        self.assertIsNone(hook.build_message(None, None))


class GitProbe(unittest.TestCase):
    def test_c4_clean_zero(self):  # C4
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            self.assertEqual(hook.dirty_count(d), 0)
            self.assertTrue(hook.current_branch(d))  # main/master 등 비어있지 않음

    def test_c4_modified_one(self):  # C4
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            with open(os.path.join(d, "a.txt"), "w", encoding="utf-8") as f:
                f.write("two\n")
            self.assertEqual(hook.dirty_count(d), 1)

    def test_c4_untracked_excluded(self):  # C4·R2 — 미추적은 세지 않는다
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            with open(os.path.join(d, "new.txt"), "w", encoding="utf-8") as f:
                f.write("x\n")
            self.assertEqual(hook.dirty_count(d), 0)

    def test_c4_non_repo_none(self):  # C4 — 비저장소는 None(침묵)
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(hook.dirty_count(d))


def run_main_in(tmpdir):
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": tmpdir}), \
         contextlib.redirect_stdout(out):
        rc = hook.main()
    return rc, out.getvalue()


class MainFlow(unittest.TestCase):
    def test_c4_main_silent_when_clean(self):  # C4
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_c4_main_outputs_when_dirty(self):  # C4
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            with open(os.path.join(d, "a.txt"), "w", encoding="utf-8") as f:
                f.write("changed\n")
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("리마인더", out)
            self.assertIn("흐름 2", out)

    def test_c5_cp949_stdout_still_outputs(self):  # C5 — 한글 Windows 콘솔(cp949)
        with tempfile.TemporaryDirectory() as d:
            _init_repo(d)
            with open(os.path.join(d, "a.txt"), "w", encoding="utf-8") as f:
                f.write("changed\n")
            buf = io.BytesIO()
            cp949 = io.TextIOWrapper(buf, encoding="cp949")
            with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": d}), \
                 contextlib.redirect_stdout(cp949):
                rc = hook.main()
            cp949.flush()
            self.assertEqual(rc, 0)
            # cp949였다면 print가 예외를 던지고 fail-open이 삼켜 무출력이 됐다 —
            # UTF-8 재구성 후에는 메시지가 실제 출력되어야 한다.
            self.assertIn("리마인더".encode("utf-8"), buf.getvalue())

    def test_c6_exception_fail_open(self):  # C6
        with mock.patch.object(hook, "build_message", side_effect=RuntimeError), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hook.main(), 0)
            self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
