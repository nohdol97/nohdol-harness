#!/usr/bin/env python3
"""Pi policy wiring and branch-only recipe regression (no model calls)."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PiProfileContractTest(unittest.TestCase):
    def test_pi_identity_is_system_only_and_keeps_profile(self):
        prompt = (ROOT / '.pi/APPEND_SYSTEM.md').read_text()
        for text in ('Pi Coding Agent', 'AGENTS.md §11', 'system prompt', 'REGISTRY.md'):
            self.assertIn(text, prompt)
        policy = (ROOT / 'AGENTS.md').read_text().split('**Pi runtime exception', 1)[1].split('\n## ', 1)[0]
        for text in ('not from file existence', 'Claude/Codex', '§3', 'autoloop', 'corporate root-edit', 'data-egress'):
            self.assertIn(text, policy)

    def test_policy_consumers_defer_to_pi_exception(self):
        for name in ('orchestrate', 'team-review', 'metaskill', 'project-status', 'tool-eval', 'branch-workflow'):
            with self.subTest(skill=name):
                text = (ROOT / f'.agents/skills/{name}/SKILL.md').read_text()
                self.assertIn('Pi runtime exception', text)
                self.assertIn('§11', text)

    def test_branch_only_recipe_starts_from_remote_main(self):
        text = (ROOT / '.agents/skills/branch-workflow/SKILL.md').read_text()
        section = text.split('### Pi checkout option', 1)[1].split('## Start procedure', 1)[0]
        recipe = re.search(r'```bash\n(.*?)\n```', section, re.S).group(1)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            origin, checkout = tmp / 'origin', tmp / 'checkout'
            def git(*args, cwd=tmp):
                return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-b', 'main', str(origin))
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'base', cwd=origin)
            git('clone', str(origin), str(checkout))
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'new main', cwd=origin)
            recipe = recipe.replace('<checkout>', str(checkout)).replace('<type>/<description>', 'feat/pi-test')
            subprocess.run(['bash', '-e', '-c', recipe], check=True, capture_output=True, text=True)
            self.assertEqual(git('branch', '--show-current', cwd=checkout), 'feat/pi-test')
            self.assertEqual(git('rev-parse', 'HEAD', cwd=checkout), git('rev-parse', 'main', cwd=origin))
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', '@{upstream}'], cwd=checkout, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(len(git('worktree', 'list', '--porcelain', cwd=checkout).split('worktree ')) - 1, 1)

    def test_pi_environment_does_not_exempt_claude_or_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'REGISTRY.md').write_text('## 설치처 프로필\n\n- **사내**\n')
            env = dict(os.environ, CLAUDE_PROJECT_DIR=tmp, PI_SESSION_ID='fixture', PI_CODING_AGENT_DIR=tmp)
            for tool, field in (('Agent', 'subagent_type'), ('spawn_agent', 'agent_type')):
                result = subprocess.run(['python3', str(ROOT / '.agents/hooks/dispatch-gate.py')],
                    input=json.dumps({'tool_name': tool, 'tool_input': {field: 'reviewer'}}),
                    text=True, capture_output=True, cwd=tmp, env=env)
                self.assertEqual(result.returncode, 2, result.stderr)


if __name__ == '__main__':
    unittest.main()
