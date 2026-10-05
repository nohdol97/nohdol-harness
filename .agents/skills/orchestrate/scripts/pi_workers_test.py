#!/usr/bin/env python3
"""Corporate Pi bridge contracts; fixture processes make no model calls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('pi_workers.py')
FAKE = '''import json, sys, time
from pathlib import Path
args = sys.argv[1:]
prompt = args[-1]
now = time.monotonic()
print(json.dumps({"type": "fixture", "start": now, "args": args}), flush=True)
if "timeout" in prompt:
    time.sleep(30)
time.sleep(.15)
if "exit-error" in prompt:
    sys.exit(7)
if "malformed" in prompt:
    print("broken-json")
    sys.exit(0)
reason = "error" if "model-error" in prompt else "length" if "truncated" in prompt else "stop"
message = {"role": "assistant", "stopReason": reason, "content": [{"type": "text", "text": "Candidate report"}]}
print(json.dumps({"type": "message_end", "message": message}))
if "missing-end" not in prompt:
    print(json.dumps({"type": "agent_end", "messages": [message]}))
print(json.dumps({"type": "fixture", "end": time.monotonic()}))
'''


class WorkerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path in ('.pi', '.agents/agents', '.agents/projects/demo', '_workspace/job', 'project/demo'):
            (self.root / path).mkdir(parents=True)
        (self.root / 'REGISTRY.md').write_text('## 설치처 프로필\n\n- **사내**\n')
        (self.root / 'AGENTS.md').write_text('Root policy')
        (self.root / '.pi/APPEND_SYSTEM.md').write_text('Pi Coding Agent runtime')
        for role in ('explorer', 'implementer'):
            (self.root / f'.agents/agents/{role}.md').write_text(f'Role: {role}')
        self.harness = self.root / '.agents/projects/demo/AGENTS.md'
        self.harness.write_text('Project policy')
        self.fake = self.root / 'fake.py'
        self.fake.write_text(FAKE)
        self.config = self.root / '_workspace/job/config.json'
        self.settings = {'command': [sys.executable, str(self.fake)], 'provider': 'internal-fixture',
                         'model': 'fixture-model', 'max_parallel': 2, 'timeout_seconds': 5}
        self.batch = self.root / '_workspace/job/batch.json'
        self.output = self.root / '_workspace/job/results'

    def task(self, name='a', prompt='work', role='explorer', target=None):
        source = self.root / f'_workspace/job/{name}.md'
        source.write_text(prompt)
        return {'id': name, 'role': role, 'target': str(target or self.root / 'project/demo'),
                'project_harness': str(self.harness), 'prompt_file': str(source)}

    def run_batch(self, tasks):
        self.config.write_text(json.dumps(self.settings))
        self.batch.write_text(json.dumps(tasks))
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root),
            '--config', str(self.config), '--batch', str(self.batch), '--output', str(self.output)],
            text=True, capture_output=True, timeout=15)

    def results(self):
        return json.loads((self.output / 'results.json').read_text())

    def test_profile_only_corporate(self):
        for text in ('## 설치처 프로필\n- **개인**\n', '# unknown\n'):
            (self.root / 'REGISTRY.md').write_text(text)
            self.assertNotEqual(self.run_batch([self.task()]).returncode, 0)
            self.assertFalse(self.output.exists())

    def test_config_and_missing_harness_fail_before_launch(self):
        task = self.task()
        self.harness.unlink()
        self.assertNotEqual(self.run_batch([task]).returncode, 0)
        self.assertFalse(self.output.exists())
        self.harness.write_text('policy')
        for field, value in (('provider', ''), ('model', ''), ('max_parallel', 0), ('timeout_seconds', -1)):
            original = self.settings[field]
            self.settings[field] = value
            self.assertNotEqual(self.run_batch([task]).returncode, 0)
            self.assertFalse(self.output.exists())
            self.settings[field] = original

    def test_design_role_and_same_writer_path_rejected(self):
        self.assertNotEqual(self.run_batch([self.task(role='reviewer')]).returncode, 0)
        self.assertNotEqual(self.run_batch([self.task(role='implementer')]).returncode, 0)
        self.assertFalse(self.output.exists())

    def test_parallel_reads_and_limit(self):
        result = self.run_batch([self.task(str(i)) for i in range(5)])
        self.assertEqual(result.returncode, 0, result.stderr)
        events = []
        for item in self.results():
            self.assertEqual(item['status'], 'candidate')
            lines = [json.loads(line) for line in Path(item['stdout']).read_text().splitlines()]
            args = lines[0]['args']
            self.assertEqual(args[args.index('--provider') + 1], 'internal-fixture')
            self.assertEqual(args[args.index('--model') + 1], 'fixture-model')
            self.assertEqual(args[args.index('--tools') + 1], 'read,bash,grep,find,ls')
            self.assertIn('--no-session', args)
            system = Path(args[args.index('--append-system-prompt') + 1]).read_text()
            for text in ('Root policy', 'Pi Coding Agent runtime', 'Role: explorer', 'Project policy'):
                self.assertIn(text, system)
            events += [(lines[0]['start'], 1), (lines[-1]['end'], -1)]
        active = peak = 0
        for _, delta in sorted(events):
            active += delta
            peak = max(peak, active)
        self.assertEqual(peak, 2)

    def test_failure_classification_and_successful_sibling_preserved(self):
        self.settings['max_parallel'] = 6
        result = self.run_batch([self.task(name, name) for name in
            ('ok', 'model-error', 'exit-error', 'truncated', 'missing-end', 'malformed')])
        self.assertNotEqual(result.returncode, 0)
        states = {item['id']: item['status'] for item in self.results()}
        self.assertEqual(states.pop('ok'), 'candidate')
        self.assertTrue(all(state == 'failed' for state in states.values()))

    def test_timeout(self):
        self.settings['timeout_seconds'] = .2
        result = self.run_batch([self.task(prompt='timeout')])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.results()[0]['status'], 'timeout')

    def test_implementation_worktree_and_overlap(self):
        repo = self.root / 'project/demo'
        def git(*args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
        git('init', '-b', 'main')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'base')
        target = self.root / 'project/worktree'
        git('worktree', 'add', '-b', 'feat/test', str(target))
        writer = self.task('writer', role='implementer', target=target)
        result = self.run_batch([writer, self.task('reader', target=target)])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        result = self.run_batch([writer])
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.output / 'writer/stdout.jsonl').read_text().splitlines()[0])['args']
        self.assertIn('edit', args[args.index('--tools') + 1])

    def test_reusing_output_does_not_overwrite(self):
        self.assertEqual(self.run_batch([self.task()]).returncode, 0)
        original = (self.output / 'results.json').read_bytes()
        self.assertNotEqual(self.run_batch([self.task()]).returncode, 0)
        self.assertEqual((self.output / 'results.json').read_bytes(), original)

    def test_missing_project_harness_can_be_observed_under_root_policy(self):
        task = self.task()
        self.harness.unlink()
        task['project_harness'] = str(self.root / 'AGENTS.md')
        self.assertEqual(self.run_batch([task]).returncode, 0)

    def test_primary_separate_git_directory_is_not_a_linked_worktree(self):
        target = self.root / 'project/primary'
        subprocess.run(['git', 'init', '--separate-git-dir', str(self.root / 'metadata'),
            '-b', 'feat/test', str(target)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(target), '-c', 'user.name=Test', '-c',
            'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'base'],
            check=True, capture_output=True)
        self.assertTrue((target / '.git').is_file())
        self.assertNotEqual(self.run_batch([self.task(role='implementer', target=target)]).returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
