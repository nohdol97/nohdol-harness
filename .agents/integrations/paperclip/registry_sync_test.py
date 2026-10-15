"""Offline regression tests; fixtures contain no installation/private registry data."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
spec = importlib.util.spec_from_file_location('registry_sync', Path(__file__).with_name('registry_sync.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

HEADER = '| 이름 | 경로 | 스택 | 역할 | 연관 프로젝트 | 하네스 유무 | 이관 |\n|---|---|---|---|---|---|---|\n'


class FakeAPI:
    def __init__(self):
        self.projects, self.calls = [], []

    def request(self, method, path, body=None):
        self.calls.append((method, path, copy.deepcopy(body)))
        if method == 'GET':
            if path == '/companies/company':
                return {'id': 'company'}
            if path == '/agents/manager':
                return {'id': 'manager', 'companyId': 'company'}
            if path == '/companies/company/projects':
                return copy.deepcopy(self.projects)
            if path.startswith('/projects/'):
                return copy.deepcopy(next(p for p in self.projects if p['id'] == path.split('/')[2]))
        if method == 'POST' and path == '/companies/company/projects':
            project = copy.deepcopy(body)
            workspace = project.pop('workspace', None)
            project.update(id='project-' + project['name'], companyId='company', workspaces=[])
            if workspace:
                project['workspaces'] = [dict(workspace, id='workspace-' + project['name'])]
            self.projects.append(project)
            return copy.deepcopy(project)
        project = next(p for p in self.projects if p['id'] == path.split('/')[2])
        if method == 'PATCH' and '/workspaces/' in path:
            workspace = next(w for w in project['workspaces'] if w['id'] == path.split('/')[-1])
            workspace.update(copy.deepcopy(body))
            return copy.deepcopy(workspace)
        if method == 'POST' and path.endswith('/workspaces'):
            workspace = dict(copy.deepcopy(body), id='workspace-' + project['name'])
            project['workspaces'].append(workspace)
            return copy.deepcopy(workspace)
        if method == 'PATCH':
            project.update(copy.deepcopy(body))
            return copy.deepcopy(project)
        raise AssertionError((method, path))


class RegistryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.api = FakeAPI()
        self.options = {'root': str(self.root), 'company_id': 'company', 'manager_id': 'manager', 'apply': False}
        self.names = ['alpha', 'Beta']
        for name in self.names:
            path = self.root / 'project' / name
            path.mkdir(parents=True)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True)
            subprocess.run(['git', '-C', str(path), '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture', '--allow-empty'], check=True)
            rules = self.root / '.agents/projects' / name / 'AGENTS.md'
            rules.parent.mkdir(parents=True)
            rules.write_text('Synthetic project rules.\n')
        self.registry()

    def registry(self, names=None, harness=None, handoff='로컬'):
        lines = []
        for name in names or self.names:
            rules = harness if harness is not None else f'✓ `.agents/projects/{name}/AGENTS.md`'
            lines.append(f'| {name} | `project/{name}/` | Python \\| Rust | Role `a|b` | 미기록 | {rules} | {handoff} |')
        (self.root / 'REGISTRY.md').write_text('# Registry\n\n## 설치처 프로필\n- **개인** — fixture\n\n'
            '## 레지스트리\n\n' + HEADER + '\n'.join(lines) + '\n\n### Other table\n| Ignore | Me |\n|---|---|\n| x | y |\n')

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def run_sync(self, apply=False):
        return module.synchronize(dict(self.options, apply=apply), self.api)

    def test_dry_run_reads_only_and_parses_only_registry_table(self):
        before = self.snapshot()
        plan = self.run_sync()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(plan['projects']), 2)
        self.assertTrue(all(p['readiness'] == 'ready' for p in plan['projects']))
        self.assertTrue(all(method == 'GET' for method, _, _ in self.api.calls))
        parsed = module.parse_registry((self.root / 'REGISTRY.md').read_text())
        self.assertEqual(parsed[1][0]['스택'], 'Python \\| Rust')
        self.assertEqual(parsed[1][0]['역할'], 'Role `a|b`')

    def test_apply_is_idempotent_and_preserves_sources_and_manual_settings(self):
        before = self.snapshot()
        self.run_sync(True)
        first = self.api.projects[0]
        first['description'] = 'Manual prefix\n' + first['description'] + '\nManual suffix'
        first['status'] = 'in_progress'
        first['executionWorkspacePolicy']['cleanupPolicy'] = {'preserve': True}
        first['workspaces'][0]['metadata']['manual'] = True
        first['workspaces'][0]['runtimeConfig'] = {'desiredState': 'manual'}
        self.api.calls.clear()
        self.run_sync(True)
        self.assertTrue(all(method == 'GET' for method, _, _ in self.api.calls))
        self.assertEqual(len(self.api.projects), 2)
        self.assertTrue(first['description'].startswith('Manual prefix\n'))
        self.assertTrue(first['description'].endswith('\nManual suffix'))
        self.assertEqual(first['status'], 'in_progress')
        self.assertEqual(first['executionWorkspacePolicy']['cleanupPolicy'], {'preserve': True})
        self.assertTrue(first['workspaces'][0]['metadata']['manual'])
        self.assertEqual(first['workspaces'][0]['sourceType'], 'local_path')
        self.assertEqual(first['executionWorkspacePolicy']['workspaceStrategy']['baseRef'], 'main')
        self.assertFalse(first['executionWorkspacePolicy']['allowIssueOverride'])
        for path, data in before.items():
            self.assertEqual((self.root / path).read_bytes(), data)

    def test_foreign_collision_in_later_row_aborts_all_writes(self):
        self.api.projects = [{'id': 'foreign', 'name': 'Beta', 'description': 'User content', 'workspaces': []}]
        before = self.snapshot()
        with self.assertRaises(module.SyncError):
            self.run_sync(True)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(all(method == 'GET' for method, _, _ in self.api.calls))

    def test_malformed_and_duplicate_rows_are_rejected(self):
        good = (self.root / 'REGISTRY.md').read_text()
        for bad in [good.replace('| Beta |', '| alpha |'), good.replace('| Beta |', '| ../Beta |'),
                    good.replace('| 스택 |', '| Unknown |'), good.replace('| Python \\| Rust |', '| Python | Rust |'),
                    good.replace('Role `a|b`', 'Role `unclosed'), '## 레지스트리']:
            with self.subTest(case=bad), self.assertRaises(module.SyncError):
                module.parse_registry(bad)

    def test_missing_rules_and_unknown_nonlocal_harness_block_registration_workspace(self):
        (self.root / '.agents/projects/alpha/AGENTS.md').unlink()
        self.run_sync(True)
        first = self.api.projects[0]
        self.assertFalse(first['workspaces'])
        self.assertIn('missing_rules', first['description'])
        self.registry(harness='미확인', handoff='미확인')
        plan = self.run_sync()
        self.assertTrue(all(p['readiness'] == 'blocked' for p in plan['projects']))

    def test_missing_cwd_and_nested_git_directory_do_not_get_workspaces(self):
        self.registry(names=['missing'])
        plan = self.run_sync(True)
        self.assertEqual(plan['projects'][0]['readiness'], 'blocked')
        self.assertFalse(self.api.projects[0]['workspaces'])
        self.registry(names=['alpha'])
        nested = self.root / 'project/alpha/nested'
        nested.mkdir()
        path = self.root / 'REGISTRY.md'
        path.write_text(path.read_text().replace('`project/alpha/`', '`project/alpha/nested/`'))
        self.assertIn('not_git_root', self.run_sync()['projects'][0]['blockers'])

    def test_removed_registry_rows_are_reported_without_deletion(self):
        self.run_sync(True)
        self.registry(names=['alpha'])
        self.api.calls.clear()
        result = self.run_sync(True)
        self.assertEqual(result['stale'], [{'id': 'project-Beta', 'name': 'Beta'}])
        self.assertEqual(len(self.api.projects), 2)
        self.assertFalse(any(method == 'DELETE' for method, _, _ in self.api.calls))

    def test_generated_manifest_symlink_is_rejected_before_any_write(self):
        path = self.root / '_workspace/paperclip-sync'
        path.mkdir(parents=True)
        (path / 'registry-manifest.json').symlink_to(self.root / 'REGISTRY.md')
        before = self.snapshot()
        with self.assertRaises(module.SyncError):
            self.run_sync(True)
        self.assertEqual(self.snapshot(), before)

    def test_mismatched_workspace_ownership_aborts_all_updates(self):
        self.run_sync(True)
        self.api.projects[1]['workspaces'][0]['metadata']['nohdolHarnessRegistry']['root'] = '/unrelated'
        self.api.calls.clear()
        before = self.snapshot()
        with self.assertRaises(module.SyncError):
            self.run_sync(True)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(all(method == 'GET' for method, _, _ in self.api.calls))

    def test_local_unknown_and_confirmed_absent_rules_keep_original_status(self):
        for harness in ['미확인', '없음(확인함)']:
            self.registry(harness=harness)
            self.api = FakeAPI()
            self.run_sync(True)
            for project in self.api.projects:
                record = project['workspaces'][0]['metadata']['nohdolHarnessRegistry']
                self.assertEqual(record['readiness'], 'ready')
                self.assertIsNone(record['rulesPath'])
                self.assertEqual(record['row']['하네스 유무'], harness)

    def test_registry_changes_preserve_description_outside_owned_block(self):
        self.run_sync(True)
        project = self.api.projects[0]
        project['description'] = 'Before\n' + project['description'] + '\nAfter'
        registry = self.root / 'REGISTRY.md'
        registry.write_text(registry.read_text().replace('Role `a|b`', 'Changed role'))
        self.run_sync(True)
        self.assertTrue(project['description'].startswith('Before\n'))
        self.assertTrue(project['description'].endswith('\nAfter'))
        self.assertIn('Changed role', project['description'])

    def test_repository_without_main_uses_verified_head(self):
        subprocess.run(['git', '-C', str(self.root / 'project/alpha'), 'branch', '-m', 'fixture-branch'], check=True)
        self.run_sync(True)
        self.assertEqual(self.api.projects[0]['executionWorkspacePolicy']['workspaceStrategy']['baseRef'], 'HEAD')

    def test_foreign_effective_workspace_selection_aborts_before_all_writes(self):
        for conflict in ['default', 'primary', 'ambiguous']:
            with self.subTest(conflict=conflict):
                self.api = FakeAPI()
                self.run_sync(True)
                project = self.api.projects[1]
                owned = project['workspaces'][0]
                foreign = {'id': 'foreign-workspace', 'name': 'Manual workspace', 'cwd': '/unrelated',
                           'isPrimary': conflict == 'primary', 'metadata': {'manual': True}}
                project['workspaces'].append(foreign)
                if conflict == 'default':
                    project['executionWorkspacePolicy']['defaultProjectWorkspaceId'] = foreign['id']
                else:
                    owned['isPrimary'] = False
                registry = self.root / 'REGISTRY.md'
                registry.write_text(registry.read_text().replace('Role `a|b`', 'Changed role'))
                before, api_before = self.snapshot(), copy.deepcopy(self.api.projects)
                self.api.calls.clear()
                with self.assertRaises(module.SyncError):
                    self.run_sync(True)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.api.projects, api_before)
                self.assertTrue(all(method == 'GET' for method, _, _ in self.api.calls))

    def test_unrelated_nonprimary_workspace_is_preserved(self):
        self.run_sync(True)
        project = self.api.projects[0]
        project['workspaces'].append({'id': 'foreign-workspace', 'name': 'Manual workspace', 'cwd': '/unrelated',
                                      'isPrimary': False, 'metadata': {'manual': True}})
        self.api.calls.clear()
        self.run_sync(True)
        self.assertEqual(len(project['workspaces']), 2)
        self.assertTrue(all(method == 'GET' for method, _, _ in self.api.calls))


if __name__ == '__main__':
    unittest.main()
