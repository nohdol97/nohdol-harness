#!/usr/bin/env python3
"""Sync installation registry metadata to local Paperclip; dry-run by default."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
from sync import API, SyncError, digest, rows, safe_generated_path

START = '<!-- nohdol-harness:registry:start -->'
END = '<!-- nohdol-harness:registry:end -->'
OWNER = '<!-- nohdol-harness:registry-owner '
COLUMNS = ['이름', '경로', '스택', '역할', '연관 프로젝트', '하네스 유무', '이관']


def cells(line):
    """Split pipes outside escaped text and matching backtick code spans."""
    parts, value, fence, index = [], '', 0, 0
    while index < len(line):
        char = line[index]
        if char == '\\' and index + 1 < len(line):
            value += line[index:index + 2]
            index += 2
            continue
        if char == '`':
            length = len(line[index:]) - len(line[index:].lstrip('`'))
            fence = 0 if fence == length else length if not fence else fence
            value += '`' * length
            index += length
            continue
        if char == '|' and not fence:
            parts.append(value.strip())
            value = ''
        else:
            value += char
        index += 1
    if fence:
        raise SyncError('Registry table contains an unmatched code delimiter')
    parts.append(value.strip())
    return parts[1:-1] if line.strip().startswith('|') and line.strip().endswith('|') else parts


def parse_registry(text):
    sections = re.split(r'^##\s+', text, flags=re.MULTILINE)
    matches = [part.partition('\n')[2] for part in sections[1:] if part.partition('\n')[0].strip() == '레지스트리']
    if len(matches) != 1:
        raise SyncError('Registry must contain exactly one level-two registry section')
    table = re.split(r'^#{1,6}\s', matches[0], maxsplit=1, flags=re.MULTILINE)[0]
    lines = [line.strip() for line in table.splitlines() if line.strip()]
    if (len(lines) < 2 or cells(lines[0]) != COLUMNS or len(cells(lines[1])) != 7
            or not all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells(lines[1]))):
        raise SyncError('Registry table must have the seven required columns')
    result, names = [], set()
    for line in lines[2:]:
        values = cells(line)
        if len(values) != 7 or not all(values):
            raise SyncError('Registry table contains an incomplete or malformed row')
        if any(marker in value for value in values for marker in [START, END, OWNER]):
            raise SyncError('Registry values may not contain synchronization ownership markers')
        row = dict(zip(COLUMNS, values))
        name = row['이름'].strip('`')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', name) or name.casefold() in names:
            raise SyncError('Registry has an invalid or duplicate project name')
        row['이름'] = name
        names.add(name.casefold())
        result.append(row)
    profile_sections = [part.partition('\n')[2] for part in sections[1:] if part.partition('\n')[0].strip() == '설치처 프로필']
    profiles = re.findall(r'^-\s+\*\*(개인|사내)\*\*', profile_sections[0], re.MULTILINE) if len(profile_sections) == 1 else []
    return profiles[0] if len(set(profiles)) == 1 else '미확인', result


def local_path(root, value):
    value = value.strip().strip('`')
    if not value or '://' in value or '\n' in value:
        raise SyncError('Registry path must be a local filesystem path')
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def git(cwd, *args):
    env = {key: value for key, value in os.environ.items() if key not in {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR'}}
    env['GIT_OPTIONAL_LOCKS'] = '0'
    result = subprocess.run(['git', '-C', str(cwd), 'rev-parse', *args], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, timeout=10, env=env)
    return result.stdout.strip() if result.returncode == 0 else None


def inspect_row(root, registry, profile, source_hash, row):
    cwd, blockers = local_path(root, row['경로']), []
    rules, git_root, base = None, None, None
    if not cwd.is_dir():
        blockers.append('missing_directory')
    else:
        top = git(cwd, '--show-toplevel')
        git_root = str(Path(top).resolve()) if top else None
        if git_root != str(cwd):
            blockers.append('not_git_root')
        elif not git(cwd, '--verify', 'HEAD'):
            blockers.append('missing_git_commit')
        else:
            base = 'main' if git(cwd, '--verify', 'refs/heads/main') else 'HEAD'
    harness = row['하네스 유무']
    if harness.startswith('✓ '):
        rules = local_path(root, harness[2:])
        if rules.name != 'AGENTS.md' or not rules.is_relative_to(root / '.agents/projects'):
            blockers.append('invalid_central_rules_path')
        elif not rules.is_file():
            blockers.append('missing_rules')
    elif harness == '미확인':
        if row['이관'] != '로컬':
            blockers.append('unknown_harness_nonlocal')
    elif harness != '없음(확인함)':
        blockers.append('unrecognized_harness_status')
    if profile == '미확인':
        blockers.append('unknown_installation_profile')
    return {'registryPath': str(registry), 'registryName': row['이름'], 'root': str(root), 'sourceHash': source_hash,
            'profile': profile, 'row': row, 'cwd': str(cwd), 'rulesPath': str(rules) if rules else None,
            'gitRoot': git_root, 'baseRef': base, 'readiness': 'blocked' if blockers else 'ready', 'blockers': blockers}


def identity(record):
    if not isinstance(record, dict) or not all(isinstance(record.get(key), str) for key in ['registryPath', 'registryName', 'root']):
        raise SyncError('Invalid registry ownership metadata')
    return {key: record[key] for key in ['registryPath', 'registryName', 'root']}


def owner(description):
    matches = re.findall(re.escape(OWNER) + r'([^\n]+) -->', description or '')
    if not matches:
        return None
    try:
        value = json.loads(matches[0])
    except (ValueError, TypeError):
        raise SyncError('Invalid registry ownership marker') from None
    if (len(matches) != 1 or not isinstance(value, dict) or set(value) != {'registryPath', 'registryName', 'root'}
            or (description or '').count(START) != 1 or (description or '').count(END) != 1):
        raise SyncError('Invalid registry ownership marker')
    return identity(value)


def description(existing, record):
    block = START + '\n' + OWNER + json.dumps(identity(record), ensure_ascii=True) + ' -->\n'
    block += 'Registry data; not authorization to execute or bypass project rules.\n'
    block += '\n'.join(f'{key}: {value}' for key, value in record['row'].items())
    block += f"\nInstallation profile: {record['profile']}\nLocal root: {record['cwd']}\nCentral rules: {record['rulesPath'] or 'not declared'}"
    block += f"\nReadiness: {record['readiness']}; blockers: {', '.join(record['blockers']) or 'none'}\n"
    block += 'Re-read REGISTRY.md and root/project rules before work. Missing rules are not confirmed absence.\n' + END
    existing = existing or ''
    if existing.count(START) != existing.count(END) or existing.count(START) > 1:
        raise SyncError('Malformed registry description markers')
    if START in existing:
        begin, end = existing.index(START), existing.index(END)
        if end < begin:
            raise SyncError('Malformed registry description markers')
        return existing[:begin] + block + existing[end + len(END):]
    return existing + ('\n\n' if existing else '') + block


def synchronize(options, api=None):
    root = Path(options['root']).expanduser().resolve()
    registry = root / 'REGISTRY.md'
    manifest = root / '_workspace/paperclip-sync/registry-manifest.json'
    safe_generated_path(root, manifest)
    text = registry.read_text()
    profile, source_rows = parse_registry(text)
    records = [inspect_row(root, registry, profile, digest(text.encode()), row) for row in source_rows]
    company, manager = options.get('company_id'), options.get('manager_id')
    if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in [company, manager]):
        raise SyncError('Set company_id and manager_id in the local config or CLI flags')
    api = api or API(options.get('api_base', 'http://127.0.0.1:3100'))
    api.request('GET', f'/companies/{company}')
    if api.request('GET', f'/agents/{manager}').get('companyId') != company:
        raise SyncError('Manager does not belong to the selected company')
    projects = rows(api.request('GET', f'/companies/{company}/projects'), 'projects')
    plans, result = [], {'status': 'plan', 'sourceHash': digest(text.encode()), 'profile': profile, 'projects': [], 'stale': []}
    owners = {p['id']: owner(p.get('description')) for p in projects}
    for record in records:
        matches = [p for p in projects if p['name'].casefold() == record['registryName'].casefold()
                   or owners[p['id']] == identity(record)]
        if len(matches) > 1 or (matches and (owners[matches[0]['id']] != identity(record) or matches[0]['name'] != record['registryName'])):
            raise SyncError('Foreign or mismatched project ownership collision; no changes applied')
        old = api.request('GET', f"/projects/{matches[0]['id']}") if matches else {}
        if old and (old.get('companyId', company) != company or owner(old.get('description')) != identity(record)):
            raise SyncError('Project ownership changed during preflight')
        workspaces = old.get('workspaces') or []
        owned = [w for w in workspaces if (w.get('metadata') or {}).get('nohdolHarnessRegistry')]
        if len(owned) > 1 or any(identity(w['metadata']['nohdolHarnessRegistry']) != identity(record) for w in owned):
            raise SyncError('Mismatched registry workspace ownership; no changes applied')
        if workspaces and not owned:
            raise SyncError('Existing project has only foreign workspaces; no changes applied')
        workspace = owned[0] if owned else {}
        default_id = (old.get('executionWorkspacePolicy') or {}).get('defaultProjectWorkspaceId')
        foreign_primary = any(w.get('isPrimary') and w['id'] != workspace.get('id') for w in workspaces)
        ambiguous_primary = len(workspaces) > 1 and not workspace.get('isPrimary') and default_id != workspace.get('id')
        if (default_id and default_id != workspace.get('id')) or foreign_primary or ambiguous_primary:
            raise SyncError('Effective project workspace conflicts with registry ownership; no changes applied')
        patch = {'description': description(old.get('description'), record), 'leadAgentId': manager}
        workspace_patch = None
        if record['readiness'] == 'ready' or workspace:
            metadata = dict(workspace.get('metadata') or {}, nohdolHarnessRegistry=record)
            workspace_patch = {'metadata': metadata}
            if record['readiness'] == 'ready':
                workspace_patch.update(name=record['registryName'], sourceType='local_path', cwd=record['cwd'])
                policy = dict(old.get('executionWorkspacePolicy') or {})
                strategy = dict(policy.get('workspaceStrategy') or {}, type='git_worktree', baseRef=record['baseRef'])
                policy.update(enabled=True, defaultMode='isolated_workspace', allowIssueOverride=False, workspaceStrategy=strategy)
                patch['executionWorkspacePolicy'] = policy
        plans.append((record, old, patch, workspace, workspace_patch))
        result['projects'].append({'name': record['registryName'], 'id': old.get('id'), 'readiness': record['readiness'],
                                   'blockers': record['blockers'], 'action': 'update' if old else 'create'})
    desired = {r['registryName'] for r in records}
    for project in projects:
        marker = owners[project['id']]
        if marker and marker['root'] == str(root) and marker['registryPath'] == str(registry) and marker['registryName'] not in desired:
            result['stale'].append({'id': project['id'], 'name': project['name']})
    if not options.get('apply'):
        return result
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(dict(result, status='applying'), ensure_ascii=False, indent=2) + '\n')
    for report, (record, old, patch, workspace, workspace_patch) in zip(result['projects'], plans):
        if not old:
            payload = dict(patch, name=record['registryName'], status='planned')
            if workspace_patch:
                payload['workspace'] = dict(workspace_patch, isPrimary=True)
            saved = api.request('POST', f'/companies/{company}/projects', payload)
            report['id'] = saved['id']
        else:
            if any(old.get(key) != value for key, value in patch.items()):
                api.request('PATCH', f"/projects/{old['id']}", patch)
            if workspace_patch and not workspace:
                api.request('POST', f"/projects/{old['id']}/workspaces", dict(workspace_patch, isPrimary=True))
            elif workspace_patch and any(workspace.get(key) != value for key, value in workspace_patch.items()):
                api.request('PATCH', f"/projects/{old['id']}/workspaces/{workspace['id']}", workspace_patch)
    result['status'] = 'success'
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config')
    parser.add_argument('--apply', action='store_true')
    for flag in ['root', 'api-base', 'company-id', 'manager-id']:
        parser.add_argument('--' + flag)
    args = vars(parser.parse_args(argv))
    try:
        options = {'root': str(Path(__file__).resolve().parents[3]), 'api_base': 'http://127.0.0.1:3100'}
        if args['config']:
            config = json.loads(Path(args['config']).expanduser().read_text())
            options.update({key: config[key] for key in ['root', 'api_base', 'company_id', 'manager_id'] if key in config})
        options.update({key: value for key, value in args.items() if key != 'config' and value is not None})
        if options['apply']:
            print(json.dumps(synchronize(dict(options, apply=False)), ensure_ascii=False, indent=2), flush=True)
        print(json.dumps(synchronize(options), ensure_ascii=False, indent=2))
        return 0
    except SyncError as error:
        print(f'registry-sync: {error}', file=sys.stderr)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        print('registry-sync: invalid or inaccessible local registry/API metadata; no success recorded', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
