#!/usr/bin/env python3
"""agentsview-daemon 훅 회귀 테스트 — 스펙 완료 기준 C1~C4.

스펙: docs/specs/2026-07-14-agentsview-daemon-hook.md
"""
import contextlib
import importlib.util
import io
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

    def test_real_running_output(self):  # C2 — 실제 CLI(v0.38.1) 실행 중 문구
        self.assertTrue(hook.daemon_running(
            0, "agentsview running at http://127.0.0.1:4664 pid: 1234 version: 0.38.1 uptime: 3h"
        ))

    def test_not_running_phrase(self):  # C3 — rc 0이어도 'not running'이면 미실행
        self.assertFalse(hook.daemon_running(0, "daemon not running"))

    def test_real_stopped_output(self):  # C3 — 실제 CLI(v0.38.1) 정지 문구 (2026-07-14 오판정 장애)
        # "running"을 포함하지만 부정문("No ... is running.")이다 — 긍정 substring
        # 단독 판정은 이 문구를 실행 중으로 오판해 재기동을 영원히 건너뛴다.
        self.assertFalse(hook.daemon_running(0, "No agentsview daemon is running."))

    def test_stopped_phrase(self):  # C3 — 버전별 문구 변형 방어
        self.assertFalse(hook.daemon_running(0, "daemon stopped"))

    def test_nonzero_rc(self):  # C3 — 비정상 종료는 미실행
        self.assertFalse(hook.daemon_running(1, "running"))

    def test_empty_output(self):
        self.assertFalse(hook.daemon_running(0, ""))


def run_main():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = hook.main()
    return rc, out.getvalue()


class MainFlow(unittest.TestCase):
    def test_c1_missing_binary_status_line(self):  # C1 개정 — 미설치도 상태 한 줄
        with mock.patch.object(hook.shutil, "which", return_value=None), \
             mock.patch.object(hook, "start_daemon") as start:
            rc, out = run_main()
            self.assertEqual(rc, 0)
            start.assert_not_called()
            self.assertIn("미설치", out)

    def test_c2_running_no_start(self):
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(hook.subprocess, "run") as run, \
             mock.patch.object(hook, "start_daemon") as start:
            run.return_value = mock.Mock(returncode=0, stdout="daemon is running", stderr="")
            rc, out = run_main()
            self.assertEqual(rc, 0)
            start.assert_not_called()
            self.assertIn("실행 중", out)

    def test_c3_stopped_starts_once(self):
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(hook.subprocess, "run") as run, \
             mock.patch.object(hook, "start_daemon") as start:
            run.return_value = mock.Mock(returncode=1, stdout="", stderr="daemon not running")
            rc, out = run_main()
            self.assertEqual(rc, 0)
            start.assert_called_once()
            self.assertIn("기동", out)

    def test_c3_real_stopped_output_starts(self):  # C3 — 실제 정지 문구(rc 0)에서 재기동
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(hook.subprocess, "run") as run, \
             mock.patch.object(hook, "start_daemon") as start:
            run.return_value = mock.Mock(
                returncode=0, stdout="No agentsview daemon is running.\n", stderr=""
            )
            rc, out = run_main()
            self.assertEqual(rc, 0)
            start.assert_called_once()
            self.assertIn("기동", out)

    def test_c4_status_exception_fail_open(self):  # 예외 경로는 무출력 유지
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(
                 hook.subprocess, "run",
                 side_effect=hook.subprocess.TimeoutExpired(cmd="x", timeout=10),
             ), \
             mock.patch.object(hook, "start_daemon") as start:
            rc, out = run_main()
            self.assertEqual(rc, 0)
            start.assert_not_called()
            self.assertEqual(out, "")

    def test_c4_start_exception_fail_open(self):
        with mock.patch.object(hook.shutil, "which", return_value="/usr/bin/agentsview"), \
             mock.patch.object(hook.subprocess, "run") as run, \
             mock.patch.object(hook, "start_daemon", side_effect=OSError):
            run.return_value = mock.Mock(returncode=1, stdout="", stderr="")
            rc, out = run_main()
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_c5_cp949_stdout_no_crash(self):  # C5 — 한글 Windows 콘솔(cp949)에서 em dash
        buf = io.BytesIO()
        cp949 = io.TextIOWrapper(buf, encoding="cp949")
        with mock.patch.object(hook.shutil, "which", return_value=None), \
             contextlib.redirect_stdout(cp949):
            rc = hook.main()  # 크래시 없이 exit 0이어야 한다 (2026-07-14 cp949 장애)
        cp949.flush()
        self.assertEqual(rc, 0)
        self.assertIn("미설치".encode("utf-8"), buf.getvalue())  # 상태 줄이 살아있음


if __name__ == "__main__":
    unittest.main(verbosity=2)
