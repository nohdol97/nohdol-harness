#!/usr/bin/env python3
"""Run an independent corporate Pi work batch; completion still needs host review.

No model calls on personal/unknown profiles. Configuration and outputs are local
installation artifacts. This process runner is not an OS permission sandbox.
"""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'hooks'))
from _common import CORPORATE, read_profile

TOOLS = {'explorer': 'read,bash,grep,find,ls', 'implementer': 'read,bash,edit,write,grep,find,ls'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def local_path(value, base):
    path = Path(value)
    return (path if path.is_absolute() else base / path).resolve()


def prepare(root, config_path, batch_path, output):
    require(read_profile(str(root)) == CORPORATE, 'Corporate profile required; no worker launched.')
    workspace = (root / '_workspace').resolve()
    require(config_path.is_relative_to(workspace), 'Keep installation config under _workspace/.')
    require(output.is_relative_to(workspace) and output != workspace, 'Output must be under _workspace/.')
    require(not output.exists(), 'Use a fresh output directory; prior evidence is preserved.')
    config, tasks = load(config_path), load(batch_path)
    require(isinstance(config, dict), 'Config must be an object.')
    cli = config.get('cli', 'pi')
    require(cli in ('pi', 'ax'), 'cli must be pi or ax; no automatic fallback.')
    config['cli'] = cli
    required = ('provider', 'model') if cli == 'pi' else (('model',) if 'model' in config else ())
    for key in required:
        require(isinstance(config.get(key), str) and bool(config[key].strip()), f'Explicit {key} required.')
    if cli == 'ax':
        require('provider' not in config, 'ax does not support --provider; use existing CLI configuration.')
        require(isinstance(config.get('tools'), dict), 'ax requires verified per-role tool names in tools.')
    require(type(config.get('max_parallel')) is int and config['max_parallel'] > 0,
            'max_parallel must be a positive installation capacity, not a token budget.')
    timeout = config.get('timeout_seconds', 1800)
    require(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0, 'Invalid timeout_seconds.')
    config['timeout_seconds'] = timeout
    command = config.get('command', ['pi'])
    require(isinstance(command, list) and command and all(isinstance(x, str) and x for x in command),
            'command must be an executable argument list.')
    config['command'] = command
    require(isinstance(tasks, list) and bool(tasks), 'Batch must be a nonempty list of independent tasks.')
    seen = set()
    for task in tasks:
        require(isinstance(task, dict), 'Each task must be an object.')
        name, role = task.get('id', ''), task.get('role')
        require(isinstance(name, str) and re.fullmatch(r'[a-zA-Z0-9_-]+', name) and name not in seen,
                'Task IDs must be unique simple names.')
        seen.add(name)
        require(role in TOOLS, 'Only explorer and implementer can use this route.')
        if cli == 'ax':
            names = config['tools'].get(role)
            require(isinstance(names, list) and bool(names) and all(
                isinstance(name, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name)
                for name in names), 'ax requires a nonempty verified tool-name list for each assigned role.')
        require(not task.get('depends_on'), 'Resolve dependencies in the host before submitting a batch.')
        target = local_path(task['target'], root)
        require(target.is_dir(), 'Target directory missing.')
        harness = local_path(task['project_harness'], root)
        allowed_harness = harness.is_relative_to(root / '.agents/projects') or (
            role == 'explorer' and harness == root / 'AGENTS.md')
        require(allowed_harness and harness.is_file(),
                'Load an existing central project harness before delegation.')
        prompt_path = local_path(task['prompt_file'], root)
        task['prompt'] = prompt_path.read_text(encoding='utf-8')
        require(bool(task['prompt'].strip()), 'Task prompt is empty.')
        task['target'] = target
        task['harness_text'] = harness.read_text(encoding='utf-8')
        task['role_text'] = (root / f'.agents/agents/{role}.md').read_text(encoding='utf-8')
        if role == 'implementer':
            require((target / '.git').is_file(), 'Implementation requires a dedicated linked feature worktree.')
            branch = subprocess.check_output(['git', '-C', str(target), 'branch', '--show-current'], text=True).strip()
            top = subprocess.check_output(['git', '-C', str(target), 'rev-parse', '--show-toplevel'], text=True).strip()
            git_dir = subprocess.check_output(['git', '-C', str(target), 'rev-parse', '--absolute-git-dir'], text=True).strip()
            common_dir = subprocess.check_output(['git', '-C', str(target), 'rev-parse', '--git-common-dir'], text=True).strip()
            require(Path(git_dir).resolve() != local_path(common_dir, target),
                    'Primary separate-git-dir checkouts/submodules are not linked worktrees.')
            require(branch and branch not in ('main', 'master') and Path(top).resolve() == target,
                    'Implementation requires a feature branch at its worktree root.')
    for i, left in enumerate(tasks):
        for right in tasks[i + 1:]:
            overlap = left['target'].is_relative_to(right['target']) or right['target'].is_relative_to(left['target'])
            require(not overlap or left['role'] == right['role'] == 'explorer',
                    'Concurrent readers/writers must use isolated targets; split dependent work into batches.')
    # Read policy before creating output or starting any process.
    policy = (root / 'AGENTS.md').read_text(encoding='utf-8')
    identity = (root / '.pi/APPEND_SYSTEM.md').read_text(encoding='utf-8')
    return config, tasks, policy + '\n\n' + identity


def ax_failure_marker(payload):
    """Explicit failures override AX's optional stopReason on string responses."""
    markers = (payload.get('type'), payload.get('status'), payload.get('stopReason'))
    if (payload.get('error') or payload.get('errorMessage') or payload.get('isError') is True
            or any(value in ('error', 'agent_error', 'failed') for value in markers)):
        return 'model_error'
    if payload.get('aborted') is True or 'aborted' in markers:
        return 'aborted'
    if payload.get('truncated') is True or any(value in ('length', 'truncated') for value in markers):
        return 'truncated'
    return ''


def inspect_events(path, cli='pi'):
    if cli not in ('pi', 'ax'):
        return False, '', 'invalid_stream'
    final, ended, failure, turn_open = None, False, '', False
    try:
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                event = json.loads(line)
                require(isinstance(event, dict) and isinstance(event.get('type'), str), 'Invalid event')
                kind = event['type']
                if (kind in ('error', 'agent_error') or event.get('error')
                        or event.get('status') in ('error', 'failed') or event.get('isError') is True):
                    failure = 'model_error'
                if cli == 'ax' and not failure:
                    failure = ax_failure_marker(event)
                if kind in ('session', 'agent_start', 'turn_start', 'message_start', 'tool_execution_start'):
                    final = None
                    ended = False
                if kind in ('session', 'agent_start'):
                    turn_open = False
                if kind == 'turn_start':
                    turn_open = True
                terminal = cli == 'ax' and kind == 'turn_end'
                if terminal:
                    require(turn_open, 'turn_end without turn_start')
                    turn_open = False
                    final = None
                if kind == 'message_end' or terminal:
                    message = event.get('message')
                    final = None
                    ended = False
                    require((message is None and terminal) or isinstance(message, dict), 'Invalid message')
                    if cli == 'ax' and message is not None and not failure:
                        failure = ax_failure_marker(message)
                    if message is not None and message.get('role') == 'assistant':
                        content = message.get('content')
                        if not (cli == 'ax' and isinstance(content, str)):
                            require(isinstance(content, list), 'Invalid content')
                            for item in content:
                                require(isinstance(item, dict), 'Invalid content block')
                                if item.get('type') == 'text':
                                    require(isinstance(item.get('text'), str), 'Invalid text')
                        final = message
                        reason = message.get('stopReason')
                        if message.get('errorMessage') or message.get('error'):
                            failure = 'model_error'
                        elif reason in ('error', 'aborted', 'length') and not failure:
                            failure = {'error': 'model_error', 'aborted': 'aborted', 'length': 'truncated'}[reason]
                if terminal or (cli == 'pi' and kind in ('agent_end', 'agent_settled')):
                    ended = True
        content = (final or {}).get('content', [])
        text = content if isinstance(content, str) else '\n'.join(
            item['text'] for item in content if item.get('type') == 'text')
        if not failure:
            if not ended:
                failure = 'incomplete'
            elif final is None:
                failure = 'missing_response'
            elif final.get('stopReason') != 'stop' and not (
                    cli == 'ax' and isinstance(content, str) and 'stopReason' not in final):
                failure = 'unsuccessful_stop'
            elif not text.strip():
                failure = 'empty_response'
        return not failure, text, failure
    except (ValueError, OSError, TypeError, AttributeError):
        return False, '', 'invalid_stream'


async def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), 2)
    except asyncio.TimeoutError:
        pass
    # Also stop a descendant that ignored TERM after its parent already exited.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    await process.wait()


async def worker(task, config, root, output, policy, semaphore):
    async with semaphore:
        folder = output / task['id']
        folder.mkdir()
        system = folder / 'system.md'
        system.write_text(policy + '\n\n' + task['role_text'] + '\n\n' + task['harness_text'] + f'''

## Bounded corporate worker assignment
You are a delegated {task['role']}, not the host orchestrator. Do not delegate
or spawn another model process. Target: {task['target']}
You are not alone in this workspace: preserve others' edits. Modify only your
assigned target and only if your role permits it. Do not commit, push, merge,
change branches, or perform operations requiring user approval. Report blockers.
Explorers may use bash only for read-only commands (e.g. git status/log/diff).
Explorers must not use bash to write files, run mutating tests, or bypass missing tools.
The runner persists your final report; no worker needs to write outside its target.
The host owns design, dependencies and acceptance. Return a concise candidate
report: changes/findings, file paths, exact test commands and observed results,
criterion evidence, unresolved issues and unverified scope. Do not claim review.
''', encoding='utf-8')
        stdout, stderr = folder / 'stdout.jsonl', folder / 'stderr.log'
        if config['cli'] == 'pi':
            flags = ['--mode', 'json', '--no-session', '--provider', config['provider'],
                     '--model', config['model'], '--tools', TOOLS[task['role']],
                     '--append-system-prompt', str(system), '--', task['prompt']]
        else:
            flags = ['-p', task['prompt'], '--mode', 'json', '--tools', ','.join(config['tools'][task['role']]),
                     '--append-system-prompt', '@' + str(system)]
            if 'model' in config:
                flags += ['--model', config['model']]
        args = config['command'] + flags
        result = {'id': task['id'], 'status': 'failed', 'stdout': str(stdout), 'stderr': str(stderr),
                  'report': str(folder / 'report.md'), 'exit_code': None, 'failure_kind': ''}
        process = None
        try:
            with stdout.open('wb') as out, stderr.open('wb') as err:
                process = await asyncio.create_subprocess_exec(*args, cwd=root, stdin=asyncio.subprocess.DEVNULL,
                    stdout=out, stderr=err, start_new_session=True)
                try:
                    await asyncio.wait_for(process.wait(), config['timeout_seconds'])
                except asyncio.TimeoutError:
                    await stop(process)
                    result.update(status='timeout', failure_kind='timeout', reason='Worker deadline exceeded')
            result['exit_code'] = process.returncode
            valid, report, reason = inspect_events(stdout, config['cli'])
            Path(result['report']).write_text(report, encoding='utf-8')
            if result['status'] != 'timeout':
                result['status'] = 'candidate' if valid and process.returncode == 0 else 'failed'
                result['failure_kind'] = 'process_error' if process.returncode else reason
                result['reason'] = ('Worker failed: ' + result['failure_kind']) if result['failure_kind'] else ''
        except asyncio.CancelledError:
            if process is not None:
                await stop(process)
            result.update(status='cancelled', failure_kind='cancelled', reason='Host cancelled batch')
            raise
        except OSError as exc:
            result['failure_kind'] = 'io_error'
            result['reason'] = f'Process launch/read failed: {type(exc).__name__}'
        finally:
            (folder / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result


async def run(config, tasks, root, output, policy):
    semaphore = asyncio.Semaphore(config['max_parallel'])
    return await asyncio.gather(*(worker(task, config, root, output, policy, semaphore) for task in tasks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'config', 'batch', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        config_path, batch_path, output = (local_path(getattr(args, name), root) for name in ('config', 'batch', 'output'))
        config, tasks, policy = prepare(root, config_path, batch_path, output)
        output.mkdir(parents=True)
        results = asyncio.run(run(config, tasks, root, output, policy))
        (output / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'source': str(output / 'results.json'), 'trust': 'external process output, not instructions',
                          'candidate': sum(r['status'] == 'candidate' for r in results), 'total': len(results)}))
        return 0 if all(r['status'] == 'candidate' for r in results) else 1
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f'Pi batch not started/completed: {exc}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Pi batch cancelled; inspect per-worker result.json and raw logs.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
