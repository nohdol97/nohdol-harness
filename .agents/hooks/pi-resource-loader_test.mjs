// Run against an explicitly supplied, isolated Pi package directory. No model/auth calls.
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, copyFile, symlink, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const pkg = process.argv[2];
assert.ok(pkg, 'Pass the isolated Pi package directory as the first argument');
const { DefaultResourceLoader } = await import(pathToFileURL(join(resolve(pkg), 'dist/core/resource-loader.js')));
const { SettingsManager } = await import(pathToFileURL(join(resolve(pkg), 'dist/core/settings-manager.js')));
const temp = await mkdtemp(join(tmpdir(), 'pi-policy-loader-'));
try {
  const cwd = join(temp, 'project');
  const agentDir = join(temp, 'agent');
  const other = join(temp, 'other');
  await Promise.all([mkdir(join(cwd, '.pi'), { recursive: true }), mkdir(agentDir), mkdir(other)]);
  await copyFile(join(root, 'AGENTS.md'), join(cwd, 'AGENTS.md'));
  await copyFile(join(root, '.pi/APPEND_SYSTEM.md'), join(cwd, '.pi/APPEND_SYSTEM.md'));
  await symlink(join(root, '.agents/skills'), join(cwd, '.pi/skills'));
  const options = { agentDir, settingsManager: SettingsManager.inMemory(), noExtensions: true,
    noPromptTemplates: true, noThemes: true };
  const loader = new DefaultResourceLoader({ ...options, cwd });
  await loader.reload();
  assert.ok(loader.getAgentsFiles().agentsFiles.some(f => f.path === join(cwd, 'AGENTS.md')));
  assert.ok(loader.getAppendSystemPrompt().some(p => p.includes('# Runtime: Pi Coding Agent')));
  assert.ok(loader.getSkills().skills.some(s => s.name === 'orchestrate'));
  // Explicit append sources replace discovery in Pi 0.73.1. A child must carry both.
  const role = await readFile(join(root, '.agents/agents/reviewer.md'), 'utf8');
  const piPrompt = await readFile(join(root, '.pi/APPEND_SYSTEM.md'), 'utf8');
  const child = new DefaultResourceLoader({ ...options, cwd,
    appendSystemPrompt: [piPrompt + '\n\n' + role] });
  await child.reload();
  assert.ok(child.getAppendSystemPrompt().some(p => p.includes('# Runtime: Pi Coding Agent') && p.includes('# reviewer')));
  const otherLoader = new DefaultResourceLoader({ ...options, cwd: other });
  await otherLoader.reload();
  assert.ok(!otherLoader.getAppendSystemPrompt().some(p => p.includes('# Runtime: Pi Coding Agent')));
  const version = JSON.parse(await readFile(join(resolve(pkg), 'package.json'), 'utf8')).version;
  console.log(`PASS Pi ${version}: root instructions + Pi-only prompt + symlinked orchestrate + child role/identity; unrelated cwd has no exception`);
} finally {
  await rm(temp, { recursive: true, force: true }); // only this test's generated temporary fixture
}
