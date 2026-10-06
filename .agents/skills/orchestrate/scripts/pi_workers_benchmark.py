#!/usr/bin/env python3
"""Compare first-pass host deliveries on identical local fixtures, not token usage.

Run from the harness root. --output must be fresh. No model or network calls.
The baseline runner is extracted from the pinned pre-change revision.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

BASE = '9f2e012cba23da17fadd379647fe9ef638074b4b'
RELATIVE = '.agents/skills/orchestrate/scripts/pi_workers.py'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[4]
    baseline = output / 'before/.agents/skills/orchestrate/scripts/pi_workers.py'
    baseline.parent.mkdir(parents=True)
    baseline.write_bytes(subprocess.check_output(['git', '-C', str(root), 'show', f'{BASE}:{RELATIVE}']))
    hooks = baseline.parents[3] / 'hooks'
    hooks.mkdir()
    # This import helper is not under measurement; both runners use the same profile reader.
    (hooks / '_common.py').write_bytes((root / '.agents/hooks/_common.py').read_bytes())
    spec = importlib.util.spec_from_file_location('fixtures', Path(__file__).with_name('pi_workers_test.py'))
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    measurements = {}
    for label, script in (('before', baseline), ('after', root / RELATIVE)):
        case = fixtures.WorkerTest()
        case.setUp()
        try:
            # Short read-only reports, large raw tool logs. Raw logs are preserved,
            # not counted as host input on either side. Same source and task count.
            expected = case.root / 'project/demo/expected.txt'
            expected.write_text(json.dumps({'summary': 'Read the requested fixture file',
                'changed_files': [], 'tests': ['fixture read: completed'], 'unresolved': [],
                'evidence': ['expected.txt'], 'decision_needed': False}))
            tasks = [case.task(str(i), f'Read {expected} using the read tool. long-log') for i in range(3)]
            case.settings['max_parallel'] = 3
            case.config.write_text(json.dumps(case.settings))
            case.batch.write_text(json.dumps(tasks))
            call = subprocess.run([sys.executable, str(script), '--root', str(case.root),
                '--config', str(case.config), '--batch', str(case.batch), '--output', str(case.output)],
                capture_output=True, text=True, check=True, timeout=15)
            deliveries = [call.stdout]
            if label == 'before':
                deliveries.append((case.output / 'results.json').read_text())
                deliveries.append('\n'.join(Path(item['report']).read_text() for item in case.results()))
            # Save exactly the text delivered by this deterministic host driver.
            run_dir = output / label
            run_dir.mkdir(exist_ok=True)
            for index, delivery in enumerate(deliveries):
                (run_dir / f'delivery-{index + 1}.txt').write_text(delivery)
            results = case.results()
            measurements[label] = {
                'host_delivery_calls': len(deliveries),
                'host_text_utf8_bytes': sum(len(text.encode()) for text in deliveries),
                'raw_stdout_bytes': sum(Path(item['stdout']).stat().st_size for item in results),
                'worker_processes': len(results), 'candidate': sum(r['status'] == 'candidate' for r in results)}
            for item in results:
                evidence = run_dir / item['id']
                evidence.mkdir()
                for field in ('stdout', 'stderr', 'report'):
                    (evidence / Path(item[field]).name).write_bytes(Path(item[field]).read_bytes())
        finally:
            case.doCleanups()
    measurements.update(baseline_revision=BASE, actual_host_model_calls=None,
        actual_tokens=None, scope='First-pass result delivery only; deterministic host driver, not a live LLM session. '
        'One baseline result-file read and one batched report read. No idle polling on either side. '
        'Both sides receive identical complete structured reports. Final diff/test review is outside this measurement.')
    (output / 'measurement.json').write_text(json.dumps(measurements, ensure_ascii=False, indent=2))
    print(json.dumps(measurements, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
