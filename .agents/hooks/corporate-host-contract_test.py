#!/usr/bin/env python3
"""Retired corporate Pi route must not remain executable or actively prescribed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / '.agents/skills/orchestrate/scripts'


class CorporateHostContractTest(unittest.TestCase):
    def test_retired_runner_cannot_be_invoked(self):
        for name in ('pi_workers.py', 'pi_workers_test.py', 'pi_workers_benchmark.py'):
            with self.subTest(name=name):
                self.assertFalse((SCRIPTS / name).exists())

    def test_active_entry_points_do_not_route_to_retired_runner(self):
        paths = [ROOT / name for name in ('AGENTS.md', 'AGENTS.ko.md', 'CLAUDE.md', 'README.md',
                                             '.agents/skills/README.ko.md')]
        paths += list((ROOT / '.agents/skills').glob('*/SKILL.md'))
        paths += list((ROOT / '.agents/agents').glob('*.md'))
        paths += [ROOT / '.agents/skills/doc-writer/references/templates.md',
                  ROOT / '.agents/skills/metaskill/references/patterns.md']
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))):
                text = path.read_text()
                for retired in ('corporate-pi.md', 'pi_workers.py', 'Pi implements',
                                'internal Pi workers', 'Pi owns implementation',
                                'Pi writer', 'Pi explorer', 'host review of Pi output'):
                    self.assertNotIn(retired, text)

    def test_retirement_notices_have_no_launch_recipe(self):
        for name in ('.agents/skills/orchestrate/references/corporate-pi.md',
                     'docs/runbooks/pi-worker-cli-setup.md'):
            text = (ROOT / name).read_text()
            self.assertTrue('Retired' in text or '폐기' in text)
            self.assertIn('055', text)
            self.assertNotIn('```', text)
            self.assertNotIn('pi_workers.py', text)

    def test_standalone_pi_identity_and_skills_still_exist(self):
        self.assertIn('Pi Coding Agent', (ROOT / '.pi/APPEND_SYSTEM.md').read_text())
        self.assertIn('### Pi execution mapping',
                      (ROOT / '.agents/skills/orchestrate/SKILL.md').read_text())
        self.assertIn('### Pi checkout option',
                      (ROOT / '.agents/skills/branch-workflow/SKILL.md').read_text())


if __name__ == '__main__':
    unittest.main()
