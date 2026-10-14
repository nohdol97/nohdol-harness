import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

p = Path(__file__).with_name('codex_readonly.py')
spec = importlib.util.spec_from_file_location('readonly_wrapper', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class WrapperTests(unittest.TestCase):
    def test_replaces_legacy_sandbox_and_disables_inherited_config(self):
        args = m.translate(['exec', '--json', '--sandbox', 'read-only', '-'])
        self.assertNotIn('--sandbox', args)
        self.assertIn('--ignore-user-config', args)
        self.assertIn('default_permissions="paperclip-read"', args)
        self.assertIn('permissions.paperclip-read.extends=":read-only"', args)
        self.assertIn('permissions.paperclip-read.network.enabled=true', args)
        self.assertIn('approval_policy="never"', args)
        self.assertEqual(args[-1], '-')

    def test_rejects_writable_or_bypass_invocations(self):
        for args in [['exec', '--sandbox', 'workspace-write'], ['exec', '--yolo'], ['exec', '--dangerously-bypass-approvals-and-sandbox'], ['exec', '-c', 'sandbox_mode="danger-full-access"'], ['exec', '-c', 'default_permissions=":workspace"'], ['exec', '-cdefault_permissions=":workspace"'], ['exec', '--profile=test'], ['exec', '--add-dir=/tmp'], ['exec', '-sdanger-full-access'], ['--search', 'exec', '--yolo']]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                m.translate(args)

    def test_search_prefix_still_enforces_readonly(self):
        args=m.translate(['--search', 'exec', '--sandbox', 'read-only', '-'])
        self.assertIn('default_permissions="paperclip-read"', args)
        self.assertEqual(args[:2], ['--search', 'exec'])

    def test_preserves_auth_probe_and_version_commands(self):
        self.assertEqual(m.translate(['login', 'status']), ['login', 'status'])
        self.assertEqual(m.translate(['--version']), ['--version'])

    def test_resume_keeps_position_and_session(self):
        args=m.translate(['exec', 'resume', 'session-id', '--sandbox', 'read-only', '-'])
        self.assertEqual(args[0], 'exec')
        self.assertIn('session-id', args)
        self.assertEqual(args[-1], '-')

    def test_rejects_quoted_and_compact_permission_config_overrides(self):
        keys = ['approval_policy', '"approval_policy"', "'default_permissions'", 'permissions.paperclip-read.extends',
                '"permissions".paperclip-read.extends', 'sandbox_mode', 'sandbox_permissions',
                'features.dangerous_feature', 'model_provider']
        for key in keys:
            for prefix in [['-c'], ['--config'], ['--config='], ['-c'], ['-c=']]:
                assignment = key + '="danger-full-access"'
                forms = [*prefix, assignment] if prefix[0] in {'-c', '--config'} else [prefix[0] + assignment]
                with self.subTest(forms=forms), self.assertRaises(ValueError):
                    m.translate(['exec', *forms, '-'])
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.translate(['exec', '-c' + key + '="danger-full-access"', '-'])

    def test_allowlist_preserves_adapter_model_settings(self):
        for config in ['model_reasoning_effort="xhigh"', 'service_tier="fast"', 'features.fast_mode=true']:
            for flags in [['-c', config], ['--config=' + config], ['-c' + config]]:
                with self.subTest(flags=flags):
                    translated = m.translate(['exec', '--json', '--model', 'test-model', *flags, '--sandbox', 'read-only', '-'])
                    self.assertIn(config, translated)
                    self.assertIn('test-model', translated)

    def test_managed_hello_probe_settings_are_allowed_only_at_safe_values(self):
        args = ['exec', '--json', '--model', 'test-model', '--sandbox', 'read-only',
                '-c', 'features.plugins=false', '-c', 'features.remote_plugin=false',
                '-c', 'project_doc_max_bytes=0', '--ephemeral', '-']
        translated = m.translate(args)
        for safe in ['features.plugins=false', 'features.remote_plugin=false', 'project_doc_max_bytes=0']:
            self.assertIn(safe, translated)
        for unsafe in ['features.plugins=true', 'features.remote_plugin=true', 'project_doc_max_bytes=8192']:
            with self.subTest(config=unsafe), self.assertRaises(ValueError):
                m.translate(['exec', '-c', unsafe, '-'])

    def test_rejects_non_execution_commands_and_unknown_flags(self):
        for args in [[], ['login'], ['login', 'status', '--yolo'], ['logout'], ['app-server'], ['sandbox', 'macos', 'sh'],
                     ['exec', '--enable', 'dangerous'], ['exec', '--ignore-rules'], ['exec', '--dangerously-bypass-hook-trust'],
                     ['exec', '--output-last-message=/tmp/overwrite'], ['exec', '-pfoo'], ['exec', '--search=anything'],
                     ['exec', '--config'], ['exec', '--model', '--yolo'], ['--search', '--version']]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                m.translate(args)
        self.assertEqual(m.translate(['--help']), ['--help'])

    def test_workspace_profile_uses_same_permission_guards(self):
        args = m.translate(['exec', '--sandbox', 'workspace-write', '-'], sandbox='workspace-write')
        self.assertIn('permissions.paperclip-write.extends=":workspace"', args)
        self.assertIn('permissions.paperclip-write.network.enabled=true', args)
        self.assertIn('approval_policy="never"', args)
        with self.assertRaises(ValueError):
            m.translate(['exec', '-sdanger-full-access'], sandbox='workspace-write')

    def test_managed_gateway_import_ignores_unmanaged_config_and_keeps_token_off_argv(self):
        text = '''sandbox_mode="danger-full-access"
[mcp_servers.unmanaged]
command="untrusted"
# BEGIN PAPERCLIP MANAGED MCP
[mcp_servers."rea"]
url="http://127.0.0.1:3100/api/mcp/gateway/fixture"
http_headers={Authorization="Bearer fixture-not-a-secret"}
# END PAPERCLIP MANAGED MCP
[hooks.unmanaged]
command="untrusted"
'''
        args, env = m.managed_mcp(text)
        self.assertEqual(len(env), 1)
        self.assertEqual(list(env.values()), ['fixture-not-a-secret'])
        self.assertNotIn('fixture-not-a-secret', ' '.join(args))
        self.assertNotIn('unmanaged', ' '.join(args))
        self.assertNotIn('sandbox_mode', ' '.join(args))
        self.assertIn('mcp_servers.rea.url="http://127.0.0.1:3100/api/mcp/gateway/fixture"', args)
        self.assertIn('mcp_servers.rea.bearer_token_env_var=' + json.dumps(next(iter(env))), args)

    def test_managed_gateway_rejects_extra_config_and_untrusted_transport(self):
        invalid_blocks = [
            'approval_policy="never"',
            '[mcp_servers.rea]\ncommand="sh"\nargs=["-c", "touch file"]',
            '[mcp_servers.rea]\nurl="file:///tmp/endpoint"\nhttp_headers={Authorization="Bearer fixture"}',
            '[mcp_servers.rea]\nurl="http://user:pass@localhost:3100/mcp"\nhttp_headers={Authorization="Bearer fixture"}',
            '[mcp_servers.rea]\nurl="http://localhost:3100/mcp?token=fixture"\nhttp_headers={Authorization="Bearer fixture"}',
            '[mcp_servers.rea]\nurl="http://localhost:3100/mcp"\nhttp_headers={Authorization="Bearer fixture",Extra="bad"}',
            '[mcp_servers."rea.bad"]\nurl="http://localhost:3100/mcp"\nhttp_headers={Authorization="Bearer fixture"}',
        ]
        for block in invalid_blocks:
            with self.subTest(block=block), self.assertRaises(ValueError):
                m.managed_mcp('# BEGIN PAPERCLIP MANAGED MCP\n' + block + '\n# END PAPERCLIP MANAGED MCP')
        for text in ['# BEGIN PAPERCLIP MANAGED MCP', '# END PAPERCLIP MANAGED MCP',
                     '# BEGIN PAPERCLIP MANAGED MCP\n# BEGIN PAPERCLIP MANAGED MCP\n# END PAPERCLIP MANAGED MCP']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                m.managed_mcp(text)
        self.assertEqual(m.managed_mcp('[mcp_servers.unmanaged]\ncommand="sh"'), ([], {}))

    def test_main_passes_managed_gateway_only_in_child_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, 'config.toml').write_text('# BEGIN PAPERCLIP MANAGED MCP\n[mcp_servers.rea]\n'
                'url="http://127.0.0.1:3100/api/mcp/gateway/fixture"\n'
                'http_headers={Authorization="Bearer fixture-not-a-secret"}\n# END PAPERCLIP MANAGED MCP\n')
            with patch.dict(os.environ, {'CODEX_HOME': temp, 'PAPERCLIP_HARNESS_CODEX_BIN': '/bin/echo'}), \
                    patch.object(sys, 'argv', ['wrapper', 'exec', '--sandbox', 'read-only', '-']), \
                    patch.object(m.os, 'execve') as execute:
                m.main()
            binary, argv, env = execute.call_args.args
            self.assertEqual(binary, '/bin/echo')
            self.assertNotIn('fixture-not-a-secret', ' '.join(argv))
            self.assertIn('fixture-not-a-secret', env.values())
            self.assertEqual(env['CODEX_HOME'], temp)

    def test_workspace_entrypoint_loads_shared_translator(self):
        result = subprocess.run([sys.executable, str(p.with_name('codex_workspace.py')), 'exec', '--sandbox', 'workspace-write', '-'],
                                env=dict(os.environ, PAPERCLIP_HARNESS_CODEX_BIN='/bin/echo', CODEX_HOME='/nonexistent-fixture'),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('permissions.paperclip-write.extends=":workspace"', result.stdout)


if __name__ == '__main__':
    unittest.main()
