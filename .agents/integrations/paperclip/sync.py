#!/usr/bin/env python3
"""Synchronize tracked harness roles and skills with one local Paperclip company.

Without --apply, only read the source tree and API and print a sanitized plan.
Installation choices belong in an untracked JSON --config, never this module.
"""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


ROLES = {"architect", "explorer", "implementer", "infra-specialist", "integrator", "reviewer", "troubleshooter"}
WRITERS = {"implementer", "infra-specialist"}
CLI_COORDINATION_SKILLS = {"orchestrate", "autoloop"}
BLOCK_START = "<!-- nohdol-harness:paperclip:start -->"
BLOCK_END = "<!-- nohdol-harness:paperclip:end -->"
COMMON_SKILLS = {"context7", "defuddle", "doc-writer", "wait-what"}
ROLE_SKILLS = {
    "architect": {"diagram", "tool-eval"},
    "explorer": {"project-status", "tool-audit"},
    "implementer": {"branch-workflow"},
    "infra-specialist": {"branch-workflow", "tool-audit"},
    "integrator": {"team-review", "project-status", "diagram"},
    "reviewer": {"team-review", "tool-audit"},
    "troubleshooter": {"tool-audit", "project-status"},
}


class SyncError(Exception):
    """Safe, actionable error text; never include API response bodies."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class API:
    def __init__(self, base):
        parsed = urllib.parse.urlsplit(base)
        host = parsed.hostname
        try:
            loopback = host == "localhost" or ipaddress.ip_address(host or "").is_loopback
        except ValueError:
            loopback = False
        if (parsed.scheme not in {"http", "https"} or not loopback or parsed.username
                or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/", "/api", "/api/"}):
            raise SyncError("API must be a loopback URL without credentials, query, or custom path")
        self.base = base.rstrip("/")
        if not self.base.endswith("/api"):
            self.base += "/api"
        # Ignore proxy environment variables; local requests must remain local.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Accept": "application/json", "Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            error.close()
            raise SyncError(f"API {method} {path.split('?')[0]} failed (HTTP {error.code}); inspect the local Paperclip UI") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            raise SyncError(f"API {method} {path.split('?')[0]} failed; check local Paperclip health") from None


def digest(content):
    return hashlib.sha256(content).hexdigest()


def skill_key(directory, slug):
    return f"local/{digest(str(directory).encode())[:10]}/{slug}"


def frontmatter(text):
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        raise SyncError("Source document is missing YAML frontmatter")
    header = text[4:].split("\n---", 1)[0]
    return dict(re.findall(r"^(name|tier):\s*([a-z0-9-]+)\s*$", header, re.MULTILINE))


def safe_generated_path(root, path):
    """A generated path may not redirect writes through symlinks."""
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise SyncError(f"Generated path is a symlink: {part.relative_to(root)}")
    if not path.resolve().is_relative_to(root):
        raise SyncError("Generated path escapes the harness root")


def discover(root):
    try:
        tracked = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", ".agents/skills"],
                                 check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode().split("\0")
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        raise SyncError("Cannot read the harness Git index") from None
    roles = {}
    for path in sorted((root / ".agents/agents").glob("*.md")):
        if path.name == "README.ko.md":
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise SyncError("Role source must be a regular file inside the harness")
        raw = path.read_bytes()
        info = frontmatter(raw.decode())
        if info.get("name") != path.stem or info.get("tier") not in {"design", "implement", "explore"}:
            raise SyncError(f"Invalid role metadata: {path.name}")
        roles[path.stem] = {"role": path.stem, "tier": info["tier"], "source": str(path.relative_to(root)),
                            "sha256": digest(raw), "text": raw.decode()}
    if set(roles) != ROLES:
        raise SyncError("Expected the seven standard harness roles; review roster changes before syncing")
    skills = {}
    for path in sorted((root / ".agents/skills").glob("*/SKILL.md")):
        slug = path.parent.name
        if frontmatter(path.read_text()).get("name") != slug:
            raise SyncError(f"Skill name must match its directory: {slug}")
        prefix = f".agents/skills/{slug}/"
        if prefix + "SKILL.md" not in tracked:
            raise SyncError(f"Skill entry is not tracked by Git: {slug}")
        files, modes = {}, {}
        for relative in tracked:
            if not relative.startswith(prefix):
                continue
            name = relative[len(prefix):]
            parts = Path(name).parts
            if any(p in {"node_modules", ".git", "__pycache__"} or p == ".env" or p.startswith(".env.") for p in parts):
                continue
            source = root / relative
            if not source.resolve().is_relative_to(path.parent.resolve()) or not source.resolve().is_relative_to(root):
                raise SyncError(f"Tracked skill file escapes its skill directory: {relative}")
            if not source.is_file():
                raise SyncError(f"Tracked skill file is unavailable: {relative}")
            files[name] = source.read_bytes()
            modes[name] = 0o644 | (source.stat().st_mode & 0o111)
        stage = root / "_workspace/paperclip-sync/skills" / slug
        safe_generated_path(root, stage)
        skills[slug] = {"source": str(path.parent.relative_to(root)), "stage": stage,
                        "key": skill_key(stage, slug), "files": files, "modes": modes,
                        "sha256": digest(b"".join(name.encode() + b"\0" + digest(value).encode() + b"\0"
                                                  for name, value in sorted(files.items())))}
    if not skills:
        raise SyncError("No tracked harness skills found")
    return roles, skills


def merge_manager_block(content, block):
    starts, ends = content.count(BLOCK_START), content.count(BLOCK_END)
    if starts != ends or starts > 1:
        raise SyncError("Manager instructions contain malformed harness block markers")
    if starts:
        start, end = content.index(BLOCK_START), content.index(BLOCK_END)
        if end < start:
            raise SyncError("Manager instructions contain reversed harness block markers")
        return content[:start] + block + content[end + len(BLOCK_END):]
    return content + ("\n" if content.endswith("\n") else "\n\n") + block + "\n"


def coordination_notice(root):
    return (f"Read the dedicated contract `{root / '.agents/integrations/paperclip/runtime.md'}` and "
            f"`{root / 'AGENTS.md'}` §11. Only actual Paperclip run context governed by that contract activates "
            "native Paperclip coordination; an environment variable or document mention alone is insufficient. "
            "Within that context, the contract supersedes CLI orchestration, corporate direct execution, "
            "corporate native dispatch bans, and corporate self-review exemptions for Paperclip issue assignment only. "
            "Use registered Paperclip roles and independent review; do not run CLI orchestrate/autoloop or start native CLI workers. "
            "Keep data-egress limits, the corporate root-edit ban, secrets, sandbox/tool permissions, "
            "approval gates and missing-harness stops. This notice does not resume agents or authorize model calls.")


def staged_skill(root, slug, raw):
    header = re.match(rb'\A---\r?\n.*?^---[ \t]*(?:\r?\n|\Z)', raw, re.MULTILINE | re.DOTALL)
    if not header:
        raise SyncError("Skill is missing a complete YAML frontmatter block")
    notice = ("\n<!-- nohdol-harness:paperclip-skill -->\n" + coordination_notice(root)
              + f"\nOriginal source: `{root / '.agents/skills' / slug / 'SKILL.md'}`\n"
              + f"Source SHA-256: `{digest(raw)}`\n\n")
    return raw[:header.end()] + notice.encode() + raw[header.end():]


def sync_agent_skills(api, agent, desired, excluded):
    preference = (agent.get('adapterConfig') or {}).get('paperclipSkillSync') or {}
    entries = preference.get('desiredSkills') or []
    current = {entry.strip() if isinstance(entry, str) else entry.get('key', '').strip()
               for entry in entries if isinstance(entry, (str, dict))}
    remove = sorted(current & excluded)
    if remove:
        api.request('POST', f"/agents/{agent['id']}/skills/sync", {'mode': 'remove', 'desiredSkills': remove})
    # Called after any agent PATCH, so stale adapter settings cannot restore removals.
    additions = sorted(set(desired) - excluded - current)
    if additions:
        api.request('POST', f"/agents/{agent['id']}/skills/sync", {'mode': 'add', 'desiredSkills': additions})


def rows(value, label):
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get(label), list):
        return value[label]
    raise SyncError(f"Unexpected API {label} response")


def synchronize(options, api=None):
    root = Path(options["root"]).expanduser().resolve()
    ids = {key: options.get(key) for key in ["company_id", "project_id", "manager_id"]}
    if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in ids.values()):
        raise SyncError("Set company_id, project_id and manager_id in --config or CLI flags")
    models = {tier: options.get(tier + "_model") for tier in ["design", "implement", "explore"]}
    if any(not isinstance(value, str) or not value.strip() for value in models.values()):
        raise SyncError("Choose explicit design_model, implement_model and explore_model from the installed Codex catalog")
    command = shutil.which(options.get("codex_command") or "codex")
    if not command:
        raise SyncError("Codex command is unavailable; set --codex-command")
    runtime_path = root / ".agents/integrations/paperclip/runtime.md"
    wrapper_path = root / ".agents/integrations/paperclip/codex_readonly.py"
    writer_wrapper = root / ".agents/integrations/paperclip/codex_workspace.py"
    if (not (root / "AGENTS.md").is_file() or not runtime_path.is_file()
            or not all(os.access(path, os.X_OK) for path in [wrapper_path, writer_wrapper])):
        raise SyncError("Root AGENTS.md, runtime.md and executable Codex wrappers are required")
    runtime = runtime_path.read_text()
    roles, skills = discover(root)
    output = root / "_workspace/paperclip-sync"
    safe_generated_path(root, output / "manifest.json")
    staged_parent = output / "skills"
    if staged_parent.exists():
        for child in staged_parent.iterdir():
            if child.name not in skills or not child.is_dir() or child.is_symlink():
                raise SyncError("Staged skill parent contains an unexpected entry; move it outside generated output before syncing")
    for role in roles:
        safe_generated_path(root, output / "agents" / role / "AGENTS.md")
        safe_generated_path(root, output / "agents" / role / "codex")
    api = api or API(options.get("api_base", "http://127.0.0.1:3100"))
    company, project, manager = ids["company_id"], ids["project_id"], ids["manager_id"]
    company_path = f"/companies/{company}"
    api.request("GET", company_path)
    project_info = api.request("GET", f"/projects/{project}")
    if project_info.get("companyId") != company:
        raise SyncError("Project does not belong to the selected company")
    agents = rows(api.request("GET", company_path + "/agents"), "agents")
    existing_skills = rows(api.request("GET", company_path + "/skills"), "skills")
    manager_info = api.request("GET", f"/agents/{manager}")
    if manager_info.get("companyId") != company or manager_info.get("name") in ROLES:
        raise SyncError("Manager must be a separate existing agent in the selected company")
    if manager_info.get("status") == "running":
        raise SyncError("Manager is running; synchronize after it becomes idle")
    workspaces = rows(api.request("GET", f"/projects/{project}/workspaces"), "workspaces")
    workspace = next((w for w in workspaces if w.get("isPrimary")), workspaces[0] if workspaces else None)
    instruction_path = f"/agents/{manager}/instructions-bundle/file"
    manager_file = api.request("GET", instruction_path + "?path=AGENTS.md")
    block = f"""{BLOCK_START}
## nohdol-harness coordination

Read `{root / 'AGENTS.md'}` and `{runtime_path}` before coordinating harness work.
Installed harness root: `{root}`. Role and skill originals under `.agents/` remain authoritative.
{coordination_notice(root)}
You coordinate Paperclip issues, dependencies, delegation, implementation/review cycles and final integration.
Delegate using the Paperclip roles: {', '.join(sorted(roles))}.
Use the native Paperclip contract, not the CLI orchestrate scale-assessment or team-dispatch procedure.
Paperclip owns scheduling, issue assignment, execution and retries; do not start autoloop or native subagent/team scheduling for these issues.
Keep independent review, test evidence, explicit completion criteria and human approval guardrails.
Read-only roles return drafts and evidence through Paperclip comments; an authorized writer persists approved artifacts.
Do not claim copied prompts activate hooks or grant permissions. Do not deploy or merge without required approval.
{BLOCK_END}"""
    manager_content = merge_manager_block(manager_file["content"], block)
    existing_roles = {}
    for role, source in roles.items():
        matches = [a for a in agents if a.get("name") == role
                   or (a.get("metadata") or {}).get("nohdolHarness", {}).get("role") == role]
        if len(matches) > 1:
            raise SyncError(f"Multiple agents claim harness role: {role}")
        if not matches:
            continue
        agent = matches[0]
        marker = (agent.get("metadata") or {}).get("nohdolHarness", {})
        if agent.get("name") != role or marker.get("role") != role or marker.get("source") != source["source"]:
            raise SyncError(f"Foreign agent name/ownership collision: {role}")
        if agent.get("status") == "running":
            raise SyncError(f"Harness agent is running: {role}; synchronize after it becomes idle")
        existing_roles[role] = api.request("GET", f"/agents/{agent['id']}")
    for slug, skill in skills.items():
        established = any(existing.get('key') == skill['key'] and existing.get('sourceType') == 'local_path'
                          and existing.get('sourceLocator') == str(skill['stage']) for existing in existing_skills)
        for existing in existing_skills:
            # These copies remain reference assets. A different installation's
            # same-slug coordination skill is neither imported over nor removed.
            if established and slug in CLI_COORDINATION_SKILLS and existing.get('key') != skill['key']:
                continue
            if existing.get("slug") == slug or existing.get("key") == skill["key"]:
                if (existing.get("key") != skill["key"] or existing.get("sourceType") != "local_path"
                        or existing.get("sourceLocator") != str(skill["stage"])):
                    raise SyncError(f"Foreign skill name/source collision: {slug}")
    plan = {"status": "plan", "root": str(root), **ids, "models": models,
            "workspace": {"id": workspace["id"] if workspace else None, "cwd": str(root)},
            "agents": [{"role": role, "action": "update" if role in existing_roles else "create",
                        "source": source["source"], "sha256": source["sha256"], "tier": source["tier"],
                        "model": models[source["tier"]], "sandbox": "workspace-write" if role in WRITERS else "read-only"}
                       for role, source in roles.items()],
            "skills": [{"slug": slug, "key": skill["key"], "source": skill["source"],
                        "sha256": skill["sha256"], "fileCount": len(skill["files"])} for slug, skill in skills.items()]}
    if not options.get("apply"):
        return plan
    # Preflight above performs no local or API writes; all collisions abort there.
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(dict(plan, status="applying"), indent=2) + "\n")
    if workspace:
        if workspace.get("cwd") != str(root):
            api.request("PATCH", f"/projects/{project}/workspaces/{workspace['id']}", {"cwd": str(root)})
    else:
        workspace = api.request("POST", f"/projects/{project}/workspaces",
                                {"name": "nohdol-harness", "cwd": str(root), "isPrimary": True})
        plan["workspace"]["id"] = workspace["id"]
    for slug, skill in skills.items():
        stage = skill["stage"]
        if stage.exists():
            # This directory is dedicated generated output, never the source tree.
            shutil.rmtree(stage)
        for relative, data in skill["files"].items():
            destination = stage / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(staged_skill(root, slug, data) if relative == 'SKILL.md' else data)
            destination.chmod(skill["modes"][relative])
    # Import the parent: importing a skill directory itself loses sibling file
    # inventory in Paperclip 2026.1012.0; SKILL.md imports omit custom directories.
    result = api.request("POST", company_path + "/skills/import", {"source": str(output / "skills")})
    imported = result.get("imported", [])
    expected_keys = {skill["key"] for skill in skills.values()}
    if len(imported) != len(skills) or {item.get("key") for item in imported} != expected_keys:
        raise SyncError("Import returned unexpected skill identities")
    by_key = {item["key"]: item for item in imported}
    for slug, skill in skills.items():
        item = by_key[skill["key"]]
        inventory = {entry.get("path") for entry in item.get("fileInventory", [])}
        if inventory != set(skill["files"]):
            raise SyncError(f"Imported file inventory does not match staged tracked files: {slug}")
        skill["id"] = item["id"]
    excluded_keys = {skill['key'] for slug, skill in skills.items() if slug in CLI_COORDINATION_SKILLS}
    for role, source in roles.items():
        bundle = output / "agents" / role
        bundle.mkdir(parents=True, exist_ok=True)
        entry = bundle / "AGENTS.md"
        entry.write_text(f"# Paperclip role: {role}\n\nInstalled harness root: `{root}`.\n"
                         f"Read root rules: `{root / 'AGENTS.md'}`.\n\n"
                         f"Source: `{source['source']}`\nsha256: `{source['sha256']}`\n\n"
                         + coordination_notice(root) + "\n\n"
                         + runtime + "\n\n---\n\n## Original role document (preserved)\n\n" + source["text"])
        old = existing_roles.get(role, {})
        readonly = role not in WRITERS
        # Paperclip's managed Codex hello probe requires command basename "codex".
        launcher = bundle / "codex"
        launcher.write_text("#!/usr/bin/env python3\nimport os\nimport runpy\n"
                            f"os.environ['PAPERCLIP_HARNESS_CODEX_BIN'] = {command!r}\n"
                            f"runpy.run_path({str(wrapper_path if readonly else writer_wrapper)!r}, run_name='__main__')\n")
        launcher.chmod(0o755)
        adapter = dict(old.get("adapterConfig") or {})
        adapter.update({"engine": "cli", "command": str(launcher),
                        "cwd": str(root), "model": models[source["tier"]],
                        "modelReasoningEffort": {"design": "xhigh", "implement": "high", "explore": "low"}[source["tier"]],
                        "dangerouslyBypassApprovalsAndSandbox": False,
                        "extraArgs": ["--sandbox", "read-only" if readonly else "workspace-write"],
                        "instructionsFilePath": str(entry), "instructionsRootPath": str(bundle),
                        "instructionsEntryFile": "AGENTS.md", "instructionsBundleMode": "external"})
        runtime_config = dict(old.get("runtimeConfig") or {})
        heartbeat = dict(runtime_config.get("heartbeat") or {})
        heartbeat.update({"enabled": False, "intervalSec": 0, "wakeOnDemand": True, "maxConcurrentRuns": 1})
        runtime_config.update({"heartbeat": heartbeat,
                               "aiConnection": {"mode": "responsible_user", "provider": "openai", "method": "subscription"}})
        metadata = dict(old.get("metadata") or {})
        metadata["nohdolHarness"] = {key: source[key] for key in ["role", "source", "sha256"]}
        payload = {"name": role, "role": "engineer" if role in WRITERS else "general", "title": role,
                   "reportsTo": manager, "adapterType": "codex_local", "adapterConfig": adapter,
                   "runtimeConfig": runtime_config, "metadata": metadata}
        if old:
            # Paperclip revalidates the managed account on every PATCH, even
            # when only object-key ordering differs. Avoid unnecessary probes.
            agent = old if all(old.get(key) == value for key, value in payload.items()) else api.request(
                "PATCH", f"/agents/{old['id']}", payload)
        else:
            payload["permissions"] = {"canCreateAgents": False, "canCreateSkills": False}
            agent = api.request("POST", company_path + "/agents", payload)
        source["id"] = agent["id"]
        keys = [skills[slug]["key"] for slug in sorted((COMMON_SKILLS | ROLE_SKILLS[role]) - CLI_COORDINATION_SKILLS) if slug in skills]
        sync_agent_skills(api, agent, keys, excluded_keys)
    sync_agent_skills(api, manager_info,
                      [skill['key'] for slug, skill in skills.items() if slug not in CLI_COORDINATION_SKILLS], excluded_keys)
    if manager_content != manager_file["content"]:
        api.request("PUT", instruction_path,
                    {"path": "AGENTS.md", "content": manager_content,
                     "baseRevisionId": (manager_file.get("revision") or {}).get("id"),
                     "baseHash": manager_file.get("contentHash")})
    for item in plan["agents"]:
        item["id"] = roles[item["role"]]["id"]
    for item in plan["skills"]:
        item["id"] = skills[item["slug"]]["id"]
    plan["status"] = "success"
    manifest_path.write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Untracked local JSON with installation IDs and model choices")
    parser.add_argument("--apply", action="store_true", help="Apply the plan; otherwise no writes")
    for name in ["root", "api-base", "company-id", "project-id", "manager-id", "design-model",
                 "implement-model", "explore-model", "codex-command"]:
        parser.add_argument("--" + name)
    args = vars(parser.parse_args(argv))
    try:
        options = {"root": str(Path(__file__).resolve().parents[3]), "api_base": "http://127.0.0.1:3100"}
        if args["config"]:
            config = json.loads(Path(args["config"]).expanduser().read_text())
            allowed = set(args) - {"config", "apply"}
            if not isinstance(config, dict) or set(config) - allowed:
                raise SyncError("Config must contain only installation IDs, paths and model choices (no credentials or apply flag)")
            options.update(config)
        options.update({key: value for key, value in args.items() if key != "config" and value is not None})
        if options.get("apply"):
            print(json.dumps(synchronize(dict(options, apply=False)), indent=2), flush=True)
        print(json.dumps(synchronize(options), indent=2))
        return 0
    except SyncError as error:
        print(f"paperclip-sync: {error}", file=sys.stderr)
    except (OSError, ValueError, TypeError, KeyError):
        print("paperclip-sync: invalid or inaccessible local input/API metadata; no successful sync recorded", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
