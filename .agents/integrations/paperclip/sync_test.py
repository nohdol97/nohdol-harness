"""Regression tests for the local Paperclip synchronizer (no live service)."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("paperclip_sync", Path(__file__).with_name("sync.py"))
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class FakeAPI:
    def __init__(self):
        self.agents = [{"id": "manager", "name": "chief-of-staff", "companyId": "company",
                        "adapterConfig": {"model": "keep-model"}, "runtimeConfig": {"keep": True}}]
        self.skills = []
        self.workspaces = [{"id": "workspace", "isPrimary": True, "cwd": "/old", "repoUrl": "keep"}]
        self.instructions = {"content": "Original manager instructions.\n", "revision": {"id": "rev"},
                             "contentHash": "a" * 64}
        self.calls = []
        self.assignments = {}
        self.fail_import = False
        self.omit_inventory = False

    def request(self, method, path, body=None):
        self.calls.append((method, path, copy.deepcopy(body)))
        if method == "GET":
            if path == "/companies/company":
                return {"id": "company"}
            if path == "/companies/company/agents":
                return copy.deepcopy(self.agents)
            if path.startswith("/companies/company/skills"):
                return copy.deepcopy(self.skills)
            if path == "/projects/project":
                return {"id": "project", "companyId": "company"}
            if path == "/projects/project/workspaces":
                return copy.deepcopy(self.workspaces)
            if path.startswith("/agents/manager/instructions-bundle/file"):
                return copy.deepcopy(self.instructions)
            if path.startswith("/agents/"):
                return copy.deepcopy(next(a for a in self.agents if a["id"] == path.split("/")[2]))
        if method == "POST" and path.endswith("/skills/import"):
            if self.fail_import:
                raise sync.SyncError("API POST skill import failed (HTTP 500)")
            parent = Path(body["source"])
            if parent.name != "skills":
                raise AssertionError("Import the staged parent directory to inventory all skill files")
            imported = []
            for entry in sorted(parent.glob("*/SKILL.md")):
                source = entry.parent
                key = sync.skill_key(source, source.name)
                inventory = [{"path": str(path.relative_to(source)), "kind": "other"}
                             for path in source.rglob("*") if path.is_file()]
                skill = {"id": f"skill-{source.name}", "key": key, "slug": source.name,
                         "sourceType": "local_path", "sourceLocator": str(source),
                         "fileInventory": inventory[:1] if self.omit_inventory else inventory}
                self.skills = [s for s in self.skills if s["key"] != key] + [skill]
                imported.append(copy.deepcopy(skill))
            return {"imported": imported, "warnings": []}
        if method == "PATCH" and "/workspaces/" in path:
            self.workspaces[0].update(body)
            return copy.deepcopy(self.workspaces[0])
        if method == "POST" and path == "/companies/company/agents":
            agent = dict(copy.deepcopy(body), id="agent-" + body["name"], companyId="company", status="idle")
            self.agents.append(agent)
            return copy.deepcopy(agent)
        if method == "PATCH" and path.startswith("/agents/"):
            agent = next(a for a in self.agents if a["id"] == path.split("/")[2])
            agent.update(copy.deepcopy(body))
            return copy.deepcopy(agent)
        if method == "POST" and path.endswith("/skills/sync"):
            aid = path.split("/")[2]
            agent = next(a for a in self.agents if a["id"] == aid)
            preference = agent["adapterConfig"].setdefault("paperclipSkillSync", {})
            existing = preference.get("desiredSkills", [])
            key_of = lambda entry: entry if isinstance(entry, str) else entry["key"]
            if body["mode"] == "remove":
                existing = [entry for entry in existing if key_of(entry) not in body["desiredSkills"]]
            else:
                keys = {key_of(entry) for entry in existing}
                existing += [key for key in body["desiredSkills"] if key not in keys]
            preference["desiredSkills"] = existing
            self.assignments[aid] = {key_of(entry) for entry in existing}
            return {}
        if method == "PUT" and path.endswith("/instructions-bundle/file"):
            self.instructions["content"] = body["content"]
            return copy.deepcopy(self.instructions)
        raise AssertionError((method, path))


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.roles = ["architect", "explorer", "implementer", "infra-specialist", "integrator", "reviewer", "troubleshooter"]
        for role in self.roles:
            tier = "explore" if role == "explorer" else "implement" if role in {"implementer", "infra-specialist"} else "design"
            self.write(f".agents/agents/{role}.md", f"---\nname: {role}\ntier: {tier}\n---\nOriginal {role} role.\n")
        for slug in ["orchestrate", "team-review", "autoloop", "metaskill", "context7"]:
            self.write(f".agents/skills/{slug}/SKILL.md", f"---\nname: {slug}\ndescription: example\n---\nOriginal {slug}.\n")
        self.write(".agents/skills/team-review/references/check.md", "Tracked reference.\n")
        self.write(".agents/skills/team-review/scripts/check", "#!/bin/sh\nexit 0\n")
        self.write(".agents/skills/autoloop/dashboard-ui/src/app.ts", "// Tracked auxiliary skill asset.\n")
        (self.root / ".agents/skills/team-review/scripts/check").chmod(0o755)
        self.write(".agents/integrations/paperclip/runtime.md", "Paperclip owns scheduling.\n")
        self.write(".agents/integrations/paperclip/codex_readonly.py", "#!/usr/bin/env python3\n")
        (self.root / ".agents/integrations/paperclip/codex_readonly.py").chmod(0o755)
        self.write(".agents/integrations/paperclip/codex_workspace.py", "#!/usr/bin/env python3\n")
        (self.root / ".agents/integrations/paperclip/codex_workspace.py").chmod(0o755)
        self.write("AGENTS.md", "Root rules.\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        self.write(".agents/skills/team-review/.env", "DO_NOT_COPY=fixture\n")
        self.write(".agents/skills/team-review/node_modules/private.txt", "DO_NOT_COPY\n")
        self.write(".agents/skills/team-review/untracked.txt", "DO_NOT_COPY\n")
        self.api = FakeAPI()
        self.options = {"root": str(self.root), "company_id": "company", "project_id": "project",
                        "manager_id": "manager", "design_model": "design", "implement_model": "implement",
                        "explore_model": "explore", "codex_command": "/bin/echo", "apply": False}

    def write(self, rel, content):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def run_sync(self, apply=False):
        return sync.synchronize(dict(self.options, apply=apply), self.api)

    def test_dry_run_reads_only_and_preserves_every_byte(self):
        before = self.snapshot()
        plan = self.run_sync()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len(plan["agents"]), 7)
        self.assertEqual(len(plan["skills"]), 5)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def test_apply_twice_preserves_originals_and_foreign_settings(self):
        originals = self.snapshot()
        self.run_sync(True)
        owned = next(a for a in self.api.agents if a["name"] == "reviewer")
        owned["adapterConfig"]["customSetting"] = "preserve"
        owned["adapterConfig"]["env"] = {"EXISTING_SETTING": "preserve"}
        owned["runtimeConfig"]["customRuntime"] = {"keep": 1}
        owned["metadata"]["customMetadata"] = True
        self.run_sync(True)
        self.assertEqual(len(self.api.agents), 8)
        self.assertEqual(len(self.api.skills), 5)
        self.assertEqual(self.api.instructions["content"].count(sync.BLOCK_START), 1)
        self.assertTrue(self.api.instructions["content"].startswith("Original manager instructions.\n"))
        self.assertEqual(self.api.agents[0]["adapterConfig"]["model"], "keep-model")
        self.assertEqual(self.api.workspaces[0]["repoUrl"], "keep")
        self.assertEqual(self.api.workspaces[0]["cwd"], str(self.root))
        reviewer = next(a for a in self.api.agents if a["name"] == "reviewer")
        self.assertEqual(reviewer["adapterConfig"]["customSetting"], "preserve")
        self.assertEqual(reviewer["adapterConfig"]["env"], {"EXISTING_SETTING": "preserve"})
        self.assertEqual(reviewer["runtimeConfig"]["customRuntime"], {"keep": 1})
        self.assertTrue(reviewer["metadata"]["customMetadata"])
        for path, content in originals.items():
            self.assertEqual((self.root / path).read_bytes(), content, path)
        for agent in self.api.agents[1:]:
            cfg = agent["adapterConfig"]
            self.assertEqual(cfg["engine"], "cli")
            self.assertFalse(cfg["dangerouslyBypassApprovalsAndSandbox"])
            expected = "workspace-write" if agent["name"] in {"implementer", "infra-specialist"} else "read-only"
            self.assertEqual(cfg["extraArgs"][1], expected)
            self.assertEqual(len(cfg["extraArgs"]), 2)
            self.assertNotIn("PAPERCLIP_HARNESS_CODEX_BIN", cfg.get("env", {}))
            launcher = Path(cfg["command"])
            self.assertEqual(launcher.name, "codex")
            self.assertTrue(launcher.stat().st_mode & 0o111)
            self.assertIn("codex_workspace.py" if agent["name"] in {"implementer", "infra-specialist"} else "codex_readonly.py", launcher.read_text())
            self.assertIn("os.environ['PAPERCLIP_HARNESS_CODEX_BIN'] = '/bin/echo'", launcher.read_text())
            self.assertFalse(agent["runtimeConfig"]["heartbeat"]["enabled"])
            self.assertEqual(agent["reportsTo"], "manager")
            instructions = Path(cfg["instructionsFilePath"]).read_text()
            self.assertIn("Original " + agent["name"] + " role.", instructions)
            self.assertIn("sha256:", instructions)
        self.assertFalse(any("autoloop" in key for keys in self.api.assignments.values() for key in keys))
        self.assertFalse(any("orchestrate" in key for keys in self.api.assignments.values() for key in keys))
        self.assertFalse(any("metaskill" in key for aid, keys in self.api.assignments.items() if aid != "manager" for key in keys))

    def test_unchanged_reapply_skips_agent_patches_and_changed_role_patches_once(self):
        self.run_sync(True)
        self.api.calls.clear()
        self.run_sync(True)
        patches = [(path, body) for method, path, body in self.api.calls
                   if method == "PATCH" and path.startswith("/agents/")]
        self.assertEqual(patches, [])
        role_path = self.root / ".agents/agents/reviewer.md"
        role_path.write_text(role_path.read_text() + "\nAdditional review criterion.\n")
        self.api.calls.clear()
        self.run_sync(True)
        patches = [(path, body) for method, path, body in self.api.calls
                   if method == "PATCH" and path.startswith("/agents/")]
        self.assertEqual([path for path, _ in patches], ["/agents/agent-reviewer"])

    def test_migrates_only_owned_coordination_assignments_without_waking_or_reassigning(self):
        self.run_sync(True)
        owned = {skill['slug']: skill['key'] for skill in self.api.skills if skill['slug'] in {'orchestrate', 'autoloop'}}
        foreign_keys = ['foreign/orchestrate', 'foreign/autoloop']
        for slug, key in zip(['orchestrate', 'autoloop'], foreign_keys):
            self.api.skills.append({'id': 'foreign-' + slug, 'key': key, 'slug': slug,
                                    'sourceType': 'github', 'sourceLocator': 'fixture-foreign-source'})
        seeded = [owned['orchestrate'], {'key': owned['autoloop'], 'versionId': 'owned-pin'},
                  {'key': foreign_keys[0], 'versionId': 'preserved-pin'}, foreign_keys[1], 'outside/unrelated']
        for agent in self.api.agents:
            agent['status'] = 'paused'
            agent['adapterConfig']['paperclipSkillSync'] = {'desiredSkills': copy.deepcopy(seeded), 'other': 'preserve'}
        foreign_agent = {'id': 'foreign-agent', 'name': 'unrelated-worker', 'adapterConfig':
                         {'paperclipSkillSync': {'desiredSkills': copy.deepcopy(seeded)}}}
        self.api.agents.append(copy.deepcopy(foreign_agent))
        self.api.calls.clear()
        self.run_sync(True)
        removals = [body for method, path, body in self.api.calls
                    if method == 'POST' and path.endswith('/skills/sync') and body['mode'] == 'remove']
        self.assertEqual(len(removals), 8)
        self.assertTrue(all(set(body['desiredSkills']) == set(owned.values()) for body in removals))
        self.assertFalse(any(method == 'PATCH' and path.startswith('/agents/') for method, path, _ in self.api.calls))
        for agent in self.api.agents[:8]:
            self.assertEqual(agent['status'], 'paused')
            preference = agent['adapterConfig']['paperclipSkillSync']
            self.assertEqual(preference['other'], 'preserve')
            self.assertIn({'key': foreign_keys[0], 'versionId': 'preserved-pin'}, preference['desiredSkills'])
            self.assertIn(foreign_keys[1], preference['desiredSkills'])
            self.assertIn('outside/unrelated', preference['desiredSkills'])
            self.assertFalse(self.api.assignments[agent['id']] & set(owned.values()))
            writes = [body['mode'] for method, path, body in self.api.calls
                      if method == 'POST' and path == f"/agents/{agent['id']}/skills/sync"]
            self.assertEqual(writes[0], 'remove')
        self.assertEqual(self.api.agents[-1], foreign_agent)
        self.assertEqual(len(self.api.skills), 7)
        self.assertIn('native Paperclip', self.api.instructions['content'])
        self.api.calls.clear()
        self.run_sync(True)
        self.assertFalse(any(method == 'POST' and path.endswith('/skills/sync') for method, path, _ in self.api.calls))

    def test_staged_skill_notice_preserves_yaml_original_body_and_provenance(self):
        originals = {path: path.read_bytes() for path in (self.root / '.agents/skills').glob('*/SKILL.md')}
        self.run_sync(True)
        self.run_sync(True)
        for source, raw in originals.items():
            staged = (self.root / '_workspace/paperclip-sync/skills' / source.parent.name / 'SKILL.md').read_bytes()
            header, body = raw.split(b'\n---\n', 1)
            self.assertTrue(staged.startswith(header + b'\n---\n'))
            self.assertTrue(staged.endswith(body))
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(staged.count(b'<!-- nohdol-harness:paperclip-skill -->'), 1)
            self.assertIn(str(self.root / '.agents/integrations/paperclip/runtime.md').encode(), staged)
            self.assertIn(str(self.root / 'AGENTS.md').encode(), staged)
            self.assertIn(sync.digest(raw).encode(), staged)
            self.assertIn(b'corporate direct execution', staged)
            self.assertIn(b'native dispatch bans', staged)
            self.assertIn(b'self-review exemptions', staged)
        self.assertEqual((self.root / '_workspace/paperclip-sync/skills/team-review/references/check.md').read_text(),
                         'Tracked reference.\n')

    def test_stage_only_tracked_files_and_references(self):
        self.run_sync(True)
        stage = self.root / "_workspace/paperclip-sync/skills/team-review"
        self.assertEqual(sorted(str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_file()),
                         ["SKILL.md", "references/check.md", "scripts/check"])
        self.assertTrue((stage / "scripts/check").stat().st_mode & 0o111)
        autoloop = next(skill for skill in self.api.skills if skill["slug"] == "autoloop")
        self.assertIn("dashboard-ui/src/app.ts", [entry["path"] for entry in autoloop["fileInventory"]])
        imports = [body for method, path, body in self.api.calls if method == "POST" and path.endswith("/skills/import")]
        self.assertEqual(imports, [{"source": str(stage.parent)}])

    def test_foreign_agent_and_skill_collisions_abort_before_any_write(self):
        for kind in ["agent", "skill", "orchestrate", "autoloop"]:
            with self.subTest(kind=kind):
                self.api = FakeAPI()
                if kind == "agent":
                    self.api.agents.append({"id": "foreign", "name": "reviewer", "metadata": {}})
                else:
                    slug = kind if kind in {'orchestrate', 'autoloop'} else 'team-review'
                    self.api.skills.append({"id": "foreign", "slug": slug, "key": "company/foreign/" + slug})
                before = self.snapshot()
                with self.assertRaises(sync.SyncError):
                    self.run_sync(True)
                self.assertEqual(self.snapshot(), before)
                self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def test_running_agent_aborts_before_any_write(self):
        self.api.agents.append({"id": "busy", "name": "reviewer", "status": "running",
                                "metadata": {"nohdolHarness": {"role": "reviewer", "source": ".agents/agents/reviewer.md"}}})
        before = self.snapshot()
        with self.assertRaises(sync.SyncError):
            self.run_sync(True)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def test_escaping_tracked_symlink_is_rejected_before_writes(self):
        link = self.root / ".agents/skills/team-review/escape"
        link.symlink_to("/etc/hosts")
        subprocess.run(["git", "-C", str(self.root), "add", str(link)], check=True)
        with self.assertRaises(sync.SyncError):
            self.run_sync(True)
        self.assertFalse((self.root / "_workspace").exists())

    def test_partial_failure_does_not_record_success_and_rerun_recovers(self):
        self.api.fail_import = True
        with self.assertRaises(sync.SyncError):
            self.run_sync(True)
        manifest = self.root / "_workspace/paperclip-sync/manifest.json"
        self.assertTrue(not manifest.exists() or json.loads(manifest.read_text())["status"] != "success")
        self.api.fail_import = False
        self.run_sync(True)
        self.assertEqual(json.loads(manifest.read_text())["status"], "success")
        self.assertEqual(len(self.api.agents), 8)

    def test_incomplete_import_inventory_cannot_report_success(self):
        self.api.omit_inventory = True
        with self.assertRaises(sync.SyncError):
            self.run_sync(True)
        manifest = self.root / "_workspace/paperclip-sync/manifest.json"
        self.assertNotEqual(json.loads(manifest.read_text())["status"], "success")
        self.assertEqual(len(self.api.agents), 1)

    def test_parent_import_rejects_unknown_staged_skill_before_mutations(self):
        self.write("_workspace/paperclip-sync/skills/unexpected/SKILL.md", "Unexpected local skill")
        before = self.snapshot()
        with self.assertRaises(sync.SyncError):
            self.run_sync(True)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))

    def test_non_loopback_api_is_rejected(self):
        for url in ["https://example.com", "http://127.0.0.1.evil.test:3100", "http://user:pass@localhost:3100"]:
            with self.subTest(url=url), self.assertRaises(sync.SyncError):
                sync.API(url)

    def test_manager_block_keeps_text_on_both_sides_and_rejects_bad_markers(self):
        content = "before\n" + sync.BLOCK_START + "old" + sync.BLOCK_END + "\nafter\n"
        replacement = sync.BLOCK_START + "new" + sync.BLOCK_END
        self.assertEqual(sync.merge_manager_block(content, replacement), "before\n" + replacement + "\nafter\n")
        with self.assertRaises(sync.SyncError):
            sync.merge_manager_block("before " + sync.BLOCK_START, replacement)

    def test_generated_path_symlink_cannot_overwrite_source(self):
        target = self.root / "_workspace/paperclip-sync/agents"
        target.parent.mkdir(parents=True)
        target.symlink_to(self.root / ".agents/agents", target_is_directory=True)
        with self.assertRaises(sync.SyncError):
            self.run_sync(True)
        self.assertTrue(all(method == "GET" for method, _, _ in self.api.calls))


if __name__ == "__main__":
    unittest.main()
