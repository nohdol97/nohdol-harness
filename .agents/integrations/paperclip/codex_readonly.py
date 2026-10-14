#!/usr/bin/env python3
"""Constrain Paperclip Codex arguments and retain only its governed HTTP gateways."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tomllib
from urllib.parse import urlsplit


def translate(args, sandbox='read-only'):
    if list(args) in (['login', 'status'], ['--version'], ['--help']):
        return list(args)
    prefix = ['--search'] if args and args[0] == '--search' else []
    args = list(args[len(prefix):])
    if not args or args[0] != 'exec' or sandbox not in ('read-only', 'workspace-write'):
        raise ValueError('Only Codex exec and exact authentication/help probes are supported')
    out = []
    positional = []
    i = 1
    while i < len(args):
        arg = args[i]
        i += 1
        if arg in ('-c', '--config', '-s', '--sandbox', '-m', '--model'):
            if i == len(args) or args[i].startswith('-'):
                raise ValueError('Codex option is missing its value')
            value = args[i]
            i += 1
            option = {'-c': '--config', '-s': '--sandbox', '-m': '--model'}.get(arg, arg)
        elif arg.startswith(('--config=', '--sandbox=', '--model=')):
            option, value = arg.split('=', 1)
        elif arg.startswith('-c') and not arg.startswith('--'):
            option, value = '--config', arg[2:].removeprefix('=')
        elif arg.startswith('-s') and not arg.startswith('--'):
            option, value = '--sandbox', arg[2:].removeprefix('=')
        else:
            option = None
        if option == '--sandbox':
            if value != sandbox:
                raise ValueError('Codex sandbox must match this role wrapper')
            continue
        if option == '--config':
            key, separator, setting = value.partition('=')
            # A positive allowlist also rejects quoted/dotted permission-key tricks.
            safe_setting = key.strip() in {'model_reasoning_effort', 'service_tier', 'features.fast_mode'}
            safe_probe = {'features.plugins': 'false', 'features.remote_plugin': 'false',
                          'project_doc_max_bytes': '0'}.get(key.strip()) == setting.strip()
            if not separator or not (safe_setting or safe_probe):
                raise ValueError('Codex wrapper owns permissions, authentication and gateway configuration')
            out.extend(['-c', value])
            continue
        if option == '--model':
            if not value or value.startswith('-'):
                raise ValueError('Codex model is missing')
            out.extend(['--model', value])
            continue
        if arg == '--ignore-user-config':
            continue  # Added exactly once below.
        if arg in ('--json', '--skip-git-repo-check', '--ephemeral', '--strict-config', '--help'):
            out.append(arg)
            continue
        if arg.startswith('-') and arg != '-':
            raise ValueError('Unsupported Codex option; permission-changing options are refused')
        positional.append(arg)
        out.append(arg)
    if positional and positional[0] == 'resume':
        if len(positional) != 3 or positional[-1] != '-':
            raise ValueError('Resume requires a session identifier and stdin prompt')
    elif len(positional) > 1 or (positional and positional[0] in ('fork', 'review', 'help')):
        raise ValueError('Only an exec prompt or explicit session resume is supported')
    profile, extends = ('paperclip-read', ':read-only') if sandbox == 'read-only' else ('paperclip-write', ':workspace')
    return [*prefix, 'exec', '--ignore-user-config', '-c', 'approval_policy="never"',
            '-c', f'default_permissions="{profile}"', '-c', f'permissions.{profile}.extends="{extends}"',
            '-c', f'permissions.{profile}.network.enabled=true', *out]


def managed_mcp(text):
    """Return CLI settings and child-only token environment from the managed block.

    Never parse or forward unmanaged providers, MCP commands, hooks or permissions.
    Error messages deliberately contain no config text or parser diagnostics.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == '# BEGIN PAPERCLIP MANAGED MCP']
    ends = [i for i, line in enumerate(lines) if line.strip() == '# END PAPERCLIP MANAGED MCP']
    if not starts and not ends:
        return [], {}
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ValueError('Malformed Paperclip managed MCP block')
    try:
        block = tomllib.loads('\n'.join(lines[starts[0] + 1:ends[0]]))
    except tomllib.TOMLDecodeError:
        raise ValueError('Invalid Paperclip managed MCP configuration') from None
    if set(block) != {'mcp_servers'} or not isinstance(block['mcp_servers'], dict):
        raise ValueError('Managed MCP block may contain only gateway servers')
    args, env = [], {}
    for index, (name, server) in enumerate(sorted(block['mcp_servers'].items())):
        if (not re.fullmatch(r'[a-z0-9_-]{1,100}', name) or not isinstance(server, dict)
                or set(server) != {'url', 'http_headers'} or not isinstance(server['url'], str)
                or not isinstance(server['http_headers'], dict) or set(server['http_headers']) != {'Authorization'}):
            raise ValueError('Managed MCP server must be a named HTTP gateway with one authorization header')
        url = urlsplit(server['url'])
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
                or url.query or url.fragment or any(char.isspace() for char in server['url'])):
            raise ValueError('Managed MCP gateway URL is invalid')
        auth = server['http_headers']['Authorization']
        if not isinstance(auth, str) or not auth.startswith('Bearer ') or not auth[7:] or any(c.isspace() for c in auth[7:]):
            raise ValueError('Managed MCP gateway requires bearer authorization')
        variable = f'PAPERCLIP_HARNESS_MCP_TOKEN_{index}'
        env[variable] = auth[7:]
        args.extend(['-c', f'mcp_servers.{name}.url={json.dumps(server["url"])}',
                     '-c', f'mcp_servers.{name}.bearer_token_env_var={json.dumps(variable)}'])
    return args, env


def main(sandbox='read-only'):
    try:
        args = translate(sys.argv[1:], sandbox)
        env = dict(os.environ)
        if 'exec' in args[:2] and env.get('CODEX_HOME'):
            config = Path(env['CODEX_HOME']) / 'config.toml'
            if config.is_file():
                gateway_args, gateway_env = managed_mcp(config.read_text())
                index = args.index('exec') + 1
                args[index:index] = gateway_args
                env.update(gateway_env)
        binary = os.environ.get('PAPERCLIP_HARNESS_CODEX_BIN') or shutil.which('codex')
        if not binary or os.path.realpath(binary) == os.path.realpath(__file__):
            raise ValueError('A distinct Codex CLI executable is required')
        os.execve(binary, [binary, *args], env)
    except ValueError as exc:
        print(f'Paperclip Codex adapter: {exc}', file=sys.stderr)
        return 2
    except OSError:
        print('Paperclip Codex adapter: cannot read runtime configuration or execute Codex', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
