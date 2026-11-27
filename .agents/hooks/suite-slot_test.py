#!/usr/bin/env python3
"""Behavior of the machine-wide full-suite slot limiter."""
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "suite-slot.py")

# Windows has no fcntl. This runner hides fcntl and supplies a msvcrt stand-in
# (backed by the real flock) so the Windows lock path runs on POSIX; each call
# appends to FAKE_MSVCRT_LOG to prove that path was the one taken.
NO_FCNTL = r"""
import fcntl, os, runpy, sys, types
import subprocess  # noqa: F401 -- loaded first: it probes msvcrt to detect Windows
def locking(fd, mode, nbytes):
    assert mode == m.LK_NBLCK and nbytes == 1 and os.lseek(fd, 0, os.SEEK_CUR) == 0
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    open(os.environ["FAKE_MSVCRT_LOG"], "a").write("lock\n")
m = types.ModuleType("msvcrt"); m.LK_NBLCK = 2; m.locking = locking
sys.modules["msvcrt"], sys.modules["fcntl"] = m, None
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def prefix(env):
    return [sys.executable, "-c", NO_FCNTL] if "FAKE_MSVCRT_LOG" in env else [sys.executable]


def run(args, slot_dir, **env):
    e = {k: v for k, v in os.environ.items() if k != "SUITE_SLOT_HELD"}
    e.update({"SUITE_SLOT_DIR": slot_dir, "SUITE_SLOT_POLL": "0.1", **env})
    return subprocess.run([*prefix(env), SCRIPT, *args], env=e, capture_output=True, text=True, timeout=30)


def popen(args, slot_dir, **env):
    e = {k: v for k, v in os.environ.items() if k != "SUITE_SLOT_HELD"}
    e.update(SUITE_SLOT_DIR=slot_dir, SUITE_SLOT_POLL="0.1", **env)
    return subprocess.Popen([*prefix(env), SCRIPT, *args], env=e, stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, start_new_session=True)


class SuiteSlot(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_exit_code_passes_through(self):
        r = run(["--", sys.executable, "-c", "raise SystemExit(7)"], self.dir)
        self.assertEqual(r.returncode, 7)

    def test_environment_and_command_errors_are_not_suite_results(self):
        self.assertEqual(run(["--", "true"], self.dir, SUITE_SLOTS="abc").returncode, 64)
        self.assertEqual(run(["--", "true"], self.dir, SUITE_SLOT_POLL="x").returncode, 64)
        self.assertEqual(run(["--slots", "1.5", "--", "true"], self.dir).returncode, 64)
        self.assertEqual(run(["--wait-limit", "nan", "--", "true"], self.dir).returncode, 64)
        self.assertEqual(run(["--", "/nonexistent-cmd-xyz"], self.dir).returncode, 71)
        blocker = Path(self.dir) / "file"
        blocker.write_text("")
        self.assertEqual(run(["--", "true"], str(blocker / "sub")).returncode, 71)

    def test_signal_killed_command_reports_128_plus_signal(self):
        r = run(["--", sys.executable, "-c", "import os,signal; os.kill(os.getpid(), signal.SIGKILL)"], self.dir)
        self.assertEqual(r.returncode, 137)

    def test_slot_files_are_world_writable_for_other_users(self):
        run(["--", "true"], self.dir)
        self.assertEqual(os.stat(self.dir).st_mode & 0o777, 0o777)
        self.assertEqual(os.stat(os.path.join(self.dir, "slot-0.lock")).st_mode & 0o666, 0o666)

    def test_usage_errors(self):
        for args in ([], ["--"], ["echo"], ["--slots", "0", "--", "true"], ["--slots", "x", "--", "true"]):
            with self.subTest(args=args):
                self.assertEqual(run(args, self.dir).returncode, 64)

    def test_second_command_waits_for_single_slot(self):
        holder = popen(["--slots", "1", "--", sys.executable, "-c", "import time; time.sleep(1.5)"], self.dir)
        time.sleep(0.5)
        start = time.monotonic()
        r = run(["--slots", "1", "--", "true"], self.dir)
        waited = time.monotonic() - start
        holder.wait()
        self.assertEqual(r.returncode, 0)
        self.assertGreater(waited, 0.5)
        self.assertIn("waiting", r.stderr)

    def test_two_slots_run_two_at_once_but_not_three(self):
        sleeper = [sys.executable, "-c", "import time; time.sleep(2)"]
        a = popen(["--slots", "2", "--", *sleeper], self.dir)
        b = popen(["--slots", "2", "--", *sleeper], self.dir)
        time.sleep(0.5)
        r = run(["--slots", "2", "--wait-limit", "0.5", "--", "true"], self.dir)
        a.wait()
        b.wait()
        self.assertEqual(r.returncode, 75)

    def test_wait_limit_means_command_never_ran(self):
        marker = Path(self.dir) / "ran"
        holder = popen(["--slots", "1", "--", sys.executable, "-c", "import time; time.sleep(2)"], self.dir)
        time.sleep(0.5)
        r = run(["--slots", "1", "--wait-limit", "0.3", "--", "touch", str(marker)], self.dir)
        holder.wait()
        self.assertEqual(r.returncode, 75)
        self.assertFalse(marker.exists())

    def test_killed_holder_frees_slot(self):
        holder = popen(["--slots", "1", "--", sys.executable, "-c", "import time; time.sleep(60)"], self.dir)
        time.sleep(0.5)
        os.killpg(holder.pid, signal.SIGKILL)
        holder.wait()
        r = run(["--slots", "1", "--wait-limit", "5", "--", "true"], self.dir)
        self.assertEqual(r.returncode, 0)

    def test_slot_stays_taken_while_orphaned_child_runs(self):
        # wrapper dies but its child keeps running: the inherited lock must hold the slot
        holder = popen(["--slots", "1", "--", sys.executable, "-c", "import time; time.sleep(3)"], self.dir)
        time.sleep(0.5)
        os.kill(holder.pid, signal.SIGKILL)
        holder.wait()
        r = run(["--slots", "1", "--wait-limit", "0.5", "--", "true"], self.dir)
        self.assertEqual(r.returncode, 75)
        time.sleep(3)

    def test_windows_lock_path_without_fcntl(self):
        log = os.path.join(self.dir, "msvcrt.log")
        fake = {"FAKE_MSVCRT_LOG": log}
        slots = os.path.join(self.dir, "slots")
        r = run(["--", sys.executable, "-c", "raise SystemExit(7)"], slots, **fake)
        self.assertEqual(r.returncode, 7, r.stderr)
        sleeper = [sys.executable, "-c", "import time; time.sleep(2)"]
        a = popen(["--slots", "2", "--", *sleeper], slots, **fake)
        b = popen(["--slots", "2", "--", *sleeper], slots, **fake)
        time.sleep(0.7)
        r = run(["--slots", "2", "--wait-limit", "0.5", "--", "true"], slots, **fake)
        a.wait()
        b.wait()
        self.assertEqual(r.returncode, 75, r.stderr)
        self.assertGreaterEqual(Path(log).read_text().count("lock"), 3)

    def test_nested_call_does_not_deadlock(self):
        inner = [sys.executable, SCRIPT, "--slots", "1", "--wait-limit", "2", "--", "true"]
        r = run(["--slots", "1", "--", *inner], self.dir)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
