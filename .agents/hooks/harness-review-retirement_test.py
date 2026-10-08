"""Retirement contract: spec 2026-10-08-retire-harness-review C1."""
import json
from pathlib import Path
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Retirement(unittest.TestCase):
    def test_retired_entrypoints_are_absent(self):
        for rel in ('.agents/skills/harness-review/SKILL.md',
                    '.agents/hooks/harness-review-reminder.py'):
            with self.subTest(path=rel):
                self.assertFalse((ROOT / rel).exists())

    def test_startup_keeps_other_hooks_without_review(self):
        configs = [json.loads((ROOT / '.claude/settings.json').read_text()),
                   tomllib.loads((ROOT / '.codex/config.toml').read_text())]
        for config in configs:
            commands = [h['command'] for group in config['hooks']['SessionStart']
                        for h in group['hooks']]
            joined = '\n'.join(commands)
            self.assertNotIn('harness-review', joined)
            self.assertIn('agentsview-daemon.py', joined)
            self.assertIn('worklog-reminder.py', joined)


if __name__ == '__main__':
    unittest.main()
