#!/usr/bin/env python3
"""agentsview-daemon 훅 회귀 테스트 — 스펙 완료 기준 C1~C4.

스펙: docs/specs/2026-07-14-agentsview-daemon-hook.md
"""
import importlib.util
import os
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "agentsview_daemon_hook", os.path.join(HERE, "agentsview-daemon.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


class DaemonRunningJudgement(unittest.TestCase):
    def test_running_output(self):  # C2 판정부
        self.assertTrue(hook.daemon_running(0, "daemon is running (pid 123)"))

    def test_not_running_phrase(self):  # C3 — rc 0이어도 'not running'이면 미실행
        self.assertFalse(hook.daemon_running(0, "daemon not running"))

    def test_nonzero_rc(self):  # C3 — 비정상 종료는 미실행
        self.assertFalse(hook.daemon_running(1, "running"))

    def test_empty_output(self):
        self.assertFalse(hook.daemon_running(0, ""))


class MainFlow(unittest.TestCase):
    def test_c1_missing_binary_noop(self):
        with mock.patch.object(hook.shutil, "which", return_value=None), \
             mock.patch.object(hook, "start_daemon") as start:
            self.assertEqual(hook.main(), 0)
            start.assert_not_called()

    def test_c2_running_no_start(self):
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(hook.subprocess, "run") as run, \
             mock.patch.object(hook, "start_daemon") as start:
            run.return_value = mock.Mock(returncode=0, stdout="daemon is running", stderr="")
            self.assertEqual(hook.main(), 0)
            start.assert_not_called()

    def test_c3_stopped_starts_once(self):
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(hook.subprocess, "run") as run, \
             mock.patch.object(hook, "start_daemon") as start:
            run.return_value = mock.Mock(returncode=1, stdout="", stderr="daemon not running")
            self.assertEqual(hook.main(), 0)
            start.assert_called_once()

    def test_c4_status_exception_fail_open(self):
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(
                 hook.subprocess, "run",
                 side_effect=hook.subprocess.TimeoutExpired(cmd="x", timeout=10),
             ), \
             mock.patch.object(hook, "start_daemon") as start:
            self.assertEqual(hook.main(), 0)
            start.assert_not_called()

    def test_c4_start_exception_fail_open(self):
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(hook.subprocess, "run") as run, \
             mock.patch.object(hook, "start_daemon", side_effect=OSError):
            run.return_value = mock.Mock(returncode=1, stdout="", stderr="")
            self.assertEqual(hook.main(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
