#!/usr/bin/env python3
"""§8 lesson index loader for runtimes that do not load it themselves (Pi)."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "memory-index.py")
spec = importlib.util.spec_from_file_location("memory_index", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MemoryIndex(unittest.TestCase):
    def setUp(self):
        self.config = tempfile.mkdtemp()
        self.root = os.path.join(tempfile.mkdtemp(), "my_harness.v2")

    def run_script(self, *args, **extra):
        env = {**os.environ, "CLAUDE_CONFIG_DIR": self.config, **extra}
        return subprocess.run([sys.executable, SCRIPT, *args], env=env, capture_output=True,
                              text=True, encoding="utf-8", timeout=30)

    def test_slug_matches_claude_project_directory_names(self):
        # Observed on this machine: /Users/nohdol/nohdol-harness/.claude/worktrees/x -> -Users-...-harness--claude-...
        self.assertEqual(mod.slug("/Users/a/nohdol-harness/.claude/worktrees/x"),
                         "-Users-a-nohdol-harness--claude-worktrees-x")
        self.assertEqual(mod.slug("/r/_workspace"), "-r--workspace")
        self.assertEqual(mod.slug("C:\\Users\\홍 길동\\harness"), "C--Users------harness")

    def test_missing_index_is_silent(self):
        r = self.run_script("--root", self.root)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_prints_index_with_its_directory(self):
        d = Path(self.config, "projects", mod.slug(self.root), "memory")
        d.mkdir(parents=True)
        (d / "MEMORY.md").write_text("- [교훈](a.md) — 상황\n", encoding="utf-8")
        r = self.run_script("--root", self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(str(d), r.stdout.splitlines()[0])
        self.assertIn("- [교훈](a.md) — 상황", r.stdout)

    def test_utf8_index_survives_a_cp949_console(self):
        # Windows Korean locale: stdout defaults to cp949, which cannot encode "—".
        d = Path(self.config, "projects", mod.slug(self.root), "memory")
        d.mkdir(parents=True)
        (d / "MEMORY.md").write_text("- [a](a.md) — 상황\n", encoding="utf-8")
        r = self.run_script("--root", self.root, PYTHONIOENCODING="cp949", PYTHONUTF8="0")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- [a](a.md) — 상황", r.stdout)

    def test_non_utf8_index_still_exits_zero(self):
        # The docstring promises exit 0 always; a stray non-UTF-8 byte used to raise
        # UnicodeDecodeError (rc=1) at session start (review 2026-11-27 C-10).
        d = Path(self.config, "projects", mod.slug(self.root), "memory")
        d.mkdir(parents=True)
        (d / "MEMORY.md").write_bytes(b"\xff\xfe bad\n- [ok](ok.md)\n")
        r = self.run_script("--root", self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- [ok](ok.md)", r.stdout)

    def test_default_root_is_this_harness(self):
        here = os.path.abspath(os.path.join(os.path.dirname(SCRIPT), "..", ".."))
        d = Path(self.config, "projects", mod.slug(here), "memory")
        d.mkdir(parents=True)
        (d / "MEMORY.md").write_text("- x\n", encoding="utf-8")
        self.assertIn("- x", self.run_script().stdout)


if __name__ == "__main__":
    unittest.main()
