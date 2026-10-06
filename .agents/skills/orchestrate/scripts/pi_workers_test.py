#!/usr/bin/env python3
"""Corporate Pi bridge contracts; fixture processes make no model calls."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

SCRIPT = Path(__file__).with_name('pi_workers.py')
SPEC = importlib.util.spec_from_file_location('pi_workers', SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
# Exact successful payload supplied by the user from AX 0.7.0, not inferred from Pi.
AX_OBSERVED_TURN_END = '{"type":"turn_end","message":{"role":"assistant","content":"응답 문자열"}}'
FAKE = '''import argparse, json, sys, time
from pathlib import Path
args = sys.argv[1:]
ax = "-p" in args or "--prompt" in args
if ax:
    # Model the user-reported value-taking AX parser, not the runner's argv.
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("-p", "--prompt", required=True)
    parser.add_argument("--mode", choices=["json"], required=True)
    parser.add_argument("--tools", required=True)
    parser.add_argument("--append-system-prompt", required=True)
    parser.add_argument("--model")
    prompt = parser.parse_args(args).prompt
else:
    prompt = args[-1]
now = time.monotonic()
print(json.dumps({"type": "fixture", "start": now, "args": args}), flush=True)
if ax:
    assert "--provider" not in args and "--no-session" not in args
    system = args[args.index("--append-system-prompt") + 1]
    assert system.startswith("@") and Path(system[1:]).is_file()
    print(json.dumps({"type": "session"}))
    print(json.dumps({"type": "turn_start"}))
if "timeout" in prompt:
    time.sleep(30)
time.sleep(.15)
if "exit-error" in prompt and "late-exit-error" not in prompt:
    sys.exit(7)
if "malformed" in prompt:
    print("broken-json")
    sys.exit(0)
reason = "error" if "model-error" in prompt else "length" if "truncated" in prompt else "stop"
text = " " if "empty" in prompt else "Candidate report"
if prompt.startswith("Read ") and "expected.txt" in prompt:
    text = Path(prompt.split("Read ", 1)[1].split(" using", 1)[0]).read_text()
message = {"role": "assistant", "stopReason": reason, "content": [{"type": "text", "text": text}]}
if ax:
    if "array-format" not in prompt:
        message = {"role": "assistant", "content": text}
        if reason != "stop":
            message["stopReason"] = reason
    if "event-error" in prompt:
        print(json.dumps({"type": "error", "error": "fixture failure"}))
    if "missing-end" not in prompt:
        print(json.dumps({"type": "turn_end", "message": message}))
else:
    print(json.dumps({"type": "message_end", "message": message}))
    if "missing-end" not in prompt:
        print(json.dumps({"type": "agent_end", "messages": [message]}))
print(json.dumps({"type": "fixture", "end": time.monotonic()}))
if "late-exit-error" in prompt:
    sys.exit(7)
'''


class EventTest(unittest.TestCase):
    def inspect(self, events, cli='pi'):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'stdout.jsonl'
            path.write_text('\n'.join(json.dumps(event) for event in events))
            return RUNNER.inspect_events(path, cli)

    def message(self, text='Candidate', reason='stop'):
        return {'type': 'message_end', 'message': {'role': 'assistant',
                'stopReason': reason, 'content': [{'type': 'text', 'text': text}]}}

    def test_normal_and_empty_responses_are_distinct(self):
        valid, text, kind = self.inspect([self.message(), {'type': 'agent_end'}])
        self.assertEqual((valid, text, kind), (True, 'Candidate', ''))
        for body in ('', '  \n'):
            valid, text, kind = self.inspect([self.message(body), {'type': 'agent_end'}])
            self.assertFalse(valid)
            self.assertEqual(kind, 'empty_response')

    def test_error_event_cannot_be_overwritten_by_success(self):
        for error in ({'type': 'error', 'error': 'redacted fixture'},
                      self.message('partial', 'error')):
            valid, _, kind = self.inspect([error, self.message(), {'type': 'agent_end'}])
            self.assertFalse(valid)
            self.assertEqual(kind, 'model_error')

    def test_new_turn_cannot_reuse_previous_response(self):
        valid, _, kind = self.inspect([self.message(), {'type': 'agent_end'},
            {'type': 'turn_start'}, {'type': 'agent_end'}])
        self.assertFalse(valid)
        self.assertEqual(kind, 'missing_response')

    def test_nonassistant_message_cannot_reuse_previous_response(self):
        valid, _, kind = self.inspect([self.message(),
            {'type': 'message_end', 'message': {'role': 'user', 'content': 'new request'}},
            {'type': 'agent_end'}])
        self.assertFalse(valid)
        self.assertEqual(kind, 'missing_response')

    def test_incomplete_and_bad_stop_reasons_are_distinct(self):
        for events, expected in (([self.message()], 'incomplete'),
                ([{'type': 'agent_end'}], 'missing_response'),
                ([self.message(reason='error'), {'type': 'agent_end'}], 'model_error'),
                ([self.message(reason='length'), {'type': 'agent_end'}], 'truncated'),
                ([self.message(reason='aborted'), {'type': 'agent_end'}], 'aborted'),
                ([self.message(reason='toolUse'), {'type': 'agent_end'}], 'unsuccessful_stop')):
            with self.subTest(expected=expected):
                self.assertEqual(self.inspect(events)[::2], (False, expected))

    def test_malformed_messages_fail_without_parser_exception(self):
        for content in (None, 7, {}, ['invalid block'], [{'type': 'text', 'text': 42}]):
            message = self.message()
            message['message']['content'] = content
            with self.subTest(content=content):
                self.assertEqual(self.inspect([message, {'type': 'agent_end'}])[::2],
                                 (False, 'invalid_stream'))

    def ax_events(self, text='Candidate', reason='stop'):
        # Synthetic contract, not a capture from the unavailable corporate CLI.
        message = self.message(text, reason)['message']
        return [{'type': 'session'}, {'type': 'turn_start'},
                {'type': 'turn_end', 'message': message}]

    def test_ax_turn_end_is_terminal_at_eof(self):
        self.assertEqual(self.inspect(self.ax_events(), 'ax'), (True, 'Candidate', ''))
        self.assertEqual(self.inspect(self.ax_events())[::2], (False, 'incomplete'))

    def test_ax_error_empty_and_missing_are_distinct(self):
        for events, expected in ((self.ax_events(reason='error'), 'model_error'),
                (self.ax_events(' \n'), 'empty_response'),
                (self.ax_events(reason='length'), 'truncated'),
                (self.ax_events(reason='aborted'), 'aborted'),
                ([{'type': 'session'}, {'type': 'turn_start'}, {'type': 'turn_end'}], 'missing_response'),
                ([{'type': 'session'}, {'type': 'turn_start'},
                  {'type': 'turn_end', 'error': {'message': 'fixture failure'}}], 'model_error')):
            with self.subTest(expected=expected):
                self.assertEqual(self.inspect(events, 'ax')[::2], (False, expected))

    def test_ax_requires_terminal_message_and_matching_turn(self):
        for events in (self.ax_events()[:-1], self.ax_events()[2:],
                       self.ax_events() + [{'type': 'turn_start'}],
                       self.ax_events() + [{'type': 'turn_start'}, {'type': 'turn_end'}],
                       [{'type': 'turn_start'}, self.message(), {'type': 'turn_end'}]):
            with self.subTest(events=events):
                self.assertFalse(self.inspect(events, 'ax')[0])

    def test_ax_error_is_not_hidden_by_later_response(self):
        events = self.ax_events(reason='error') + self.ax_events()
        self.assertEqual(self.inspect(events, 'ax')[::2], (False, 'model_error'))

    def test_ax_rejects_unknown_payloads_and_malformed_content(self):
        for payload in ({'text': 'Unverified envelope'}, {'message': []},
                        {'message': {'role': 'assistant', 'content': 42, 'stopReason': 'stop'}},
                        {'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'body'}]}}):
            events = [{'type': 'session'}, {'type': 'turn_start'}, {'type': 'turn_end', **payload}]
            with self.subTest(payload=payload):
                self.assertFalse(self.inspect(events, 'ax')[0])

    def ax_string_events(self):
        return [{'type': 'session'}, {'type': 'turn_start'}, json.loads(AX_OBSERVED_TURN_END)]

    def test_ax_observed_string_without_stop_reason(self):
        self.assertEqual(self.inspect(self.ax_string_events(), 'ax'), (True, '응답 문자열', ''))
        events = self.ax_string_events()
        events[-1]['message']['stopReason'] = 'stop'
        self.assertEqual(self.inspect(events, 'ax'), (True, '응답 문자열', ''))

    def test_ax_empty_string_is_not_a_candidate(self):
        for content in ('', '  \n\t'):
            events = self.ax_string_events()
            events[-1]['message']['content'] = content
            self.assertEqual(self.inspect(events, 'ax')[::2], (False, 'empty_response'))

    def test_ax_error_event_before_or_after_string_response_is_sticky(self):
        for position in (2, 3):
            events = self.ax_string_events()
            events.insert(position, {'type': 'error', 'error': 'fixture failure'})
            self.assertEqual(self.inspect(events, 'ax')[::2], (False, 'model_error'))

    def test_ax_string_requires_matching_completion_and_assistant(self):
        events = self.ax_string_events()
        for stream in (events[:-1], events[2:], events + [{'type': 'turn_start'}],
                       events + [{'type': 'turn_start'}, {'type': 'turn_end'}]):
            self.assertFalse(self.inspect(stream, 'ax')[0])
        events[-1]['message']['role'] = 'user'
        self.assertEqual(self.inspect(events, 'ax')[::2], (False, 'missing_response'))

    def test_ax_string_explicit_failure_markers_are_never_success(self):
        markers = [({'stopReason': 'error'}, 'model_error'),
                   ({'stopReason': 'aborted'}, 'aborted'),
                   ({'stopReason': 'length'}, 'truncated'),
                   ({'status': 'failed'}, 'model_error'),
                   ({'status': 'aborted'}, 'aborted'),
                   ({'status': 'truncated'}, 'truncated'),
                   ({'errorMessage': 'fixture failure'}, 'model_error'),
                   ({'isError': True}, 'model_error'),
                   ({'aborted': True}, 'aborted'),
                   ({'truncated': True}, 'truncated')]
        for marker, expected in markers:
            for surface in ('event', 'message'):
                with self.subTest(marker=marker, surface=surface):
                    events = self.ax_string_events()
                    target = events[-1] if surface == 'event' else events[-1]['message']
                    target.update(marker)
                    self.assertEqual(self.inspect(events, 'ax')[::2], (False, expected))
        for kind in ('aborted', 'truncated'):
            events = self.ax_string_events()
            events.insert(2, {'type': kind})
            self.assertEqual(self.inspect(events, 'ax')[::2], (False, kind))

    def test_ax_string_unknown_or_null_stop_reason_is_not_omitted(self):
        for reason in ('toolUse', 'unknown', None):
            events = self.ax_string_events()
            events[-1]['message']['stopReason'] = reason
            self.assertEqual(self.inspect(events, 'ax')[::2], (False, 'unsuccessful_stop'))

    def test_ax_nonassistant_failure_is_not_hidden_by_final_response(self):
        for role in ('toolResult', 'user'):
            for marker, expected in (({'isError': True}, 'model_error'),
                                     ({'aborted': True}, 'aborted'),
                                     ({'truncated': True}, 'truncated')):
                with self.subTest(role=role, marker=marker):
                    events = self.ax_string_events()
                    events.insert(2, {'type': 'message_end', 'message': {
                        'role': role, 'content': [{'type': 'text', 'text': 'failed'}], **marker}})
                    self.assertEqual(self.inspect(events, 'ax')[::2], (False, expected))

    def test_ax_string_exemption_does_not_relax_arrays_or_upstream(self):
        arrays = self.ax_events()
        self.assertTrue(self.inspect(arrays, 'ax')[0])
        del arrays[-1]['message']['stopReason']
        self.assertEqual(self.inspect(arrays, 'ax')[::2], (False, 'unsuccessful_stop'))
        message = json.loads(AX_OBSERVED_TURN_END)['message']
        for reason in (None, 'stop'):
            if reason is not None:
                message['stopReason'] = reason
            self.assertEqual(self.inspect([{'type': 'message_end', 'message': message},
                                          {'type': 'agent_end'}])[::2], (False, 'invalid_stream'))
        array_message = self.message()
        del array_message['message']['stopReason']
        self.assertEqual(self.inspect([array_message, {'type': 'agent_end'}])[::2],
                         (False, 'unsuccessful_stop'))


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

    def test_unknown_cli_is_rejected_before_launch(self):
        self.settings['cli'] = 'unknown'
        self.assertNotEqual(self.run_batch([self.task()]).returncode, 0)
        self.assertFalse(self.output.exists())

    def test_ax_uses_confirmed_flags_and_explicit_tools(self):
        self.settings.pop('provider')
        self.settings.pop('model')
        self.settings.update(cli='ax', tools={'explorer': ['fixture_read', 'fixture_shell']})
        prompt = 'Report "quoted text" and 한국어\nKeep --mode json and $(literal) unchanged.'
        result = self.run_batch([self.task(prompt=prompt)])
        self.assertEqual(result.returncode, 0, (self.output / 'a/stderr.log').read_text())
        args = json.loads((self.output / 'a/stdout.jsonl').read_text().splitlines()[0])['args']
        self.assertIn('-p', args)
        self.assertEqual(args[args.index('-p') + 1], prompt)
        self.assertEqual(args.count(prompt), 1)
        self.assertNotIn('--', args)
        self.assertNotIn('--provider', args)
        self.assertNotIn('--list-models', args)
        self.assertNotIn('--model', args)
        self.assertEqual(args[args.index('--tools') + 1], 'fixture_read,fixture_shell')
        system = args[args.index('--append-system-prompt') + 1]
        self.assertTrue(system.startswith('@'))
        self.assertIn('Role: explorer', Path(system[1:]).read_text())

    def test_ax_parser_rejects_old_boolean_prompt_and_trailing_positionals(self):
        options = ['--mode', 'json', '--tools', 'fixture_read',
                   '--append-system-prompt', '@unused-system.md']
        for args, expected in ((['-p', *options, '--', 'work'],
                                'argument -p/--prompt: expected one argument'),
                               (['-p', 'work', *options, '--', 'duplicate'], 'unrecognized arguments')):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(self.fake), *args],
                                        text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertIn(expected, result.stderr)

    def test_upstream_prompt_remains_positional(self):
        prompt = 'Explain "upstream"\n한국어 and $(literal).'
        result = self.run_batch([self.task(prompt=prompt)])
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.output / 'a/stdout.jsonl').read_text().splitlines()[0])['args']
        system = str((self.output / 'a/system.md').resolve())
        self.assertEqual(args, ['--mode', 'json', '--no-session', '--provider', 'internal-fixture',
            '--model', 'fixture-model', '--tools', 'read,bash,grep,find,ls',
            '--append-system-prompt', system, '--', prompt])

    def test_ax_batch_classifies_responses_and_preserves_sibling(self):
        self.settings.pop('provider')
        self.settings.update(cli='ax', tools={'explorer': ['fixture_read']})
        expected = {'ok': '', 'empty': 'empty_response', 'model-error': 'model_error',
                    'event-error': 'model_error', 'exit-error': 'process_error',
                    'late-exit-error': 'process_error', 'array-format': '',
                    'malformed': 'invalid_stream', 'missing-end': 'incomplete', 'truncated': 'truncated'}
        result = self.run_batch([self.task(name, name) for name in expected])
        self.assertEqual(result.returncode, 1, result.stderr)
        for item in self.results():
            self.assertEqual(item['failure_kind'], expected[item['id']])
            self.assertEqual(item['status'], 'failed' if expected[item['id']] else 'candidate')
            self.assertTrue(Path(item['report']).is_file())
            self.assertTrue(Path(item['stdout']).is_file())
            if item['id'] in ('ok', 'late-exit-error'):
                self.assertEqual(Path(item['report']).read_text(), 'Candidate report')
                self.assertEqual(item['exit_code'], 7 if item['id'] == 'late-exit-error' else 0)
                events = [json.loads(line) for line in Path(item['stdout']).read_text().splitlines()]
                message = next(event['message'] for event in events if event['type'] == 'turn_end')
                self.assertIsInstance(message['content'], str)
                self.assertNotIn('stopReason', message)
        args = json.loads((self.output / 'ok/stdout.jsonl').read_text().splitlines()[0])['args']
        self.assertEqual(args[args.index('--model') + 1], 'fixture-model')

    def test_runbook_configuration_and_read_smoke_with_fixture_cli(self):
        runbook = SCRIPT.resolve().parents[4] / 'docs/runbooks/pi-worker-cli-setup.md'
        blocks = [textwrap.dedent(block) for block in
                  re.findall(r'(?m)^ *```bash\n(.*?)^ *```', runbook.read_text(), re.S)]
        snippets = [block for block in blocks if block.startswith(("python3 -c '", "python3 - <<'PY'"))]
        self.assertEqual(len(snippets), 3)
        inputs = '\n'.join((json.dumps([sys.executable, str(self.fake)]),
                            '["fixture_read"]', '["fixture_read", "fixture_write"]', '2')) + '\n'
        def snippet(index, input_text=''):
            return subprocess.run(['/bin/sh', '-c', snippets[index]], cwd=self.root,
                input=input_text, text=True, capture_output=True, timeout=10)
        result = snippet(0, inputs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(snippet(0, inputs).returncode, 0)  # existing config preserved
        result = snippet(1)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root),
            '--config', '_workspace/pi-workers/config.json',
            '--batch', '_workspace/pi-workers/smoke/batch.json',
            '--output', '_workspace/pi-workers/smoke/run-01'], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = snippet(2)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ax_missing_tools_or_provider_rejected(self):
        self.settings['cli'] = 'ax'
        task = self.task()
        self.assertNotEqual(self.run_batch([task]).returncode, 0)
        self.settings.pop('provider')
        for mapping in (None, {}, {'explorer': []}, {'explorer': 'read'},
                        {'explorer': ['read,write']}, {'explorer': ['--all']}):
            self.settings['tools'] = mapping
            self.assertNotEqual(self.run_batch([task]).returncode, 0)
            self.assertFalse(self.output.exists())

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
        self.assertEqual(self.results()[0]['failure_kind'], 'timeout')

    def test_ax_timeout_does_not_become_candidate(self):
        self.settings.pop('provider')
        self.settings.update(cli='ax', tools={'explorer': ['fixture_read']}, timeout_seconds=.2)
        self.assertNotEqual(self.run_batch([self.task(prompt='timeout')]).returncode, 0)
        self.assertEqual(self.results()[0]['failure_kind'], 'timeout')

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
