#!/usr/bin/env python3
"""integrity-check 회귀 테스트 — 스펙 docs/specs/2026-07-19-integrity-check-script.md 완료 기준.

실행: python3 .agents/hooks/integrity-check_test.py   (스크립트 수정 시 반드시 통과)
부수 효과: 임시 디렉토리만 사용하며 전부 정리한다(git init 포함, 픽스처 내부에서만).
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPT = os.path.join(HERE, "integrity-check.py")

# 스위트 자신의 한글 출력도 로케일 비의존이어야 한다(단일 원본 공유 — tdd-gate_test 관례).
sys.path.insert(0, HERE)
try:
    from _common import utf8_stdio
except Exception:
    def utf8_stdio():
        pass


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def write_codex_adapter(root, name="foo", description="A test agent", contract="foo", extra=""):
    write(os.path.join(root, ".codex/agents/%s.toml" % name),
          'name = "%s"\n'
          'description = "%s"\n'
          'developer_instructions = """\n'
          'Before handling the task, locate and read .agents/agents/%s.md in full.\n'
          'If the contract is unavailable, report the missing contract.\n'
          '"""\n%s' % (name, description, contract, extra))


def write_korean_views(root):
    """ADR 030 한글 뷰 3종을 현재 원본 상태에 맞게 생성한다(R16·R17 정합 픽스처).

    AGENTS.md를 다시 쓴 테스트는 이 함수를 재호출해 source-hash를 신선하게 유지한다.
    """
    with open(os.path.join(root, "AGENTS.md"), "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:12]
    write(os.path.join(root, "AGENTS.ko.md"),
          "> 생성된 뷰 — 편집 금지. source-hash: `%s`\n\n# AGENTS 한글 다이제스트\n" % h)
    skills = os.path.join(root, ".agents/skills")
    names = sorted(n for n in os.listdir(skills) if os.path.isdir(os.path.join(skills, n)))
    write(os.path.join(skills, "README.ko.md"),
          "# 스킬 한글 요약\n\n" + "".join("## %s\n요약.\n\n" % n for n in names))
    agents = os.path.join(root, ".agents/agents")
    stems = sorted(os.path.splitext(fn)[0] for fn in os.listdir(agents)
                   if fn.endswith(".md") and fn != "README.ko.md")
    write(os.path.join(agents, "README.ko.md"),
          "# 에이전트 한글 요약\n\n" + "".join("## %s\n요약.\n\n" % n for n in stems))


def make_good_fixture(root):
    """규약을 모두 지키는 최소 하네스 구조 + git init(.gitignore 판정용)."""
    # 원본 디렉토리
    write(os.path.join(root, ".agents/agents/foo.md"),
          "---\nname: foo\ndescription: A test agent\ntools: Read\ntier: implement\n---\n# foo\n")
    write(os.path.join(root, ".agents/skills/bar/SKILL.md"),
          "---\nname: bar\ndescription: A test skill\n---\n# bar\n")
    write_codex_adapter(root)
    write(os.path.join(root, ".codex/config.toml"),
          "project_doc_max_bytes = 65536\n\n"
          "[features]\n"
          "hooks = true\n\n"
          "[[hooks.SessionStart]]\n"
          'matcher = "startup|resume|clear"\n'
          "[[hooks.SessionStart.hooks]]\n"
          'type = "command"\ncommand = "python3 .agents/hooks/agentsview-daemon.py"\n'
          "[[hooks.SessionStart.hooks]]\n"
          'type = "command"\ncommand = "python3 .agents/hooks/harness-review-reminder.py"\n'
          "[[hooks.SessionStart.hooks]]\n"
          'type = "command"\ncommand = "python3 .agents/hooks/worklog-reminder.py"\n\n'
          "[[hooks.PreToolUse]]\n"
          'matcher = "apply_patch"\n'
          "[[hooks.PreToolUse.hooks]]\n"
          'type = "command"\ncommand = "python3 .agents/hooks/gate-reminder.py --check"\n\n'
          # 발행 게이트(ADR 037) — R18이 `Agent` 매처 블록을 보게 된 뒤
          # 정상 픽스처도 이것을 갖고 있어야 한다.
          "[[hooks.PreToolUse]]\n"
          'matcher = "Agent|Task|spawn_agent"\n'
          "[[hooks.PreToolUse.hooks]]\n"
          'type = "command"\ncommand = "python3 .agents/hooks/tier-gate.py"\n\n'
          "[[hooks.PostToolUse]]\n"
          'matcher = "Bash|shell|local_shell"\n'
          "[[hooks.PostToolUse.hooks]]\n"
          'type = "command"\ncommand = "python3 .agents/hooks/gate-reminder.py --record"\n')
    # .claude 심링크
    claude = os.path.join(root, ".claude")
    os.makedirs(claude, exist_ok=True)
    os.symlink("../.agents/agents", os.path.join(claude, "agents"))
    os.symlink("../.agents/skills", os.path.join(claude, "skills"))
    # R21 — Claude 쪽 훅 등록. Codex 등록과 짝이며, 한쪽만 있으면 그 런타임에서
    # 게이트가 조용히 안 걸린다(ADR 042). 예전엔 `{}`라 등록 유실을 재현조차
    # 할 수 없었다.
    write(os.path.join(claude, "settings.json"), json.dumps({
        "hooks": {
            "SessionStart": [{"hooks": [
                {"type": "command", "command": "python3 .agents/hooks/agentsview-daemon.py"},
                {"type": "command", "command": "python3 .agents/hooks/harness-review-reminder.py"},
                {"type": "command", "command": "python3 .agents/hooks/worklog-reminder.py"},
            ]}],
            "PreToolUse": [
                {"matcher": "Edit|Write", "hooks": [
                    {"type": "command", "command": "python3 .agents/hooks/gate-reminder.py --check"}]},
                {"matcher": "Agent", "hooks": [
                    {"type": "command", "command": "python3 .agents/hooks/tier-gate.py"}]},
            ],
            "PostToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": "python3 .agents/hooks/gate-reminder.py --record"}]}],
        }
    }, ensure_ascii=False, indent=2) + "\n")
    # CLAUDE.md / AGENTS.md
    write(os.path.join(root, "CLAUDE.md"), "@AGENTS.md\n\n# CLAUDE.md\n")
    write(os.path.join(root, "AGENTS.md"), "# AGENTS.md\n")
    # .gitignore 필수 항목
    write(os.path.join(root, ".gitignore"),
          "_workspace/\nproject/\nREGISTRY.md\n.agents/projects/*\n!.agents/projects/README.md\n"
          ".codex/*\n!.codex/agents/\n.codex/agents/*\n!.codex/agents/*.toml\n")
    # docs MOC 정합 (파일 ↔ README 링크 양방향 일치)
    write(os.path.join(root, "docs/adr/001-initial.md"), "# ADR 001\n")
    write(os.path.join(root, "docs/specs/2026-07-19-thing.md"), "# spec\n")
    write(os.path.join(root, "docs/README.md"),
          "# MOC\n- [001](adr/001-initial.md)\n- [thing](specs/2026-07-19-thing.md)\n")
    # 한글 뷰 3종 (ADR 030 — 원본과 정합 상태로 생성)
    write_korean_views(root)
    # git init — check-ignore 판정에 필요(add·commit 불요)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)


def run_check(root):
    p = subprocess.run([sys.executable, SCRIPT, "--root", root],
                       capture_output=True, timeout=30, encoding="utf-8", errors="replace")
    return p.returncode, p.stdout + p.stderr


class TestIntegrityCheck(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="integrity-fix-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        make_good_fixture(self.root)

    # --- 정상 케이스 ---
    def test_good_fixture_all_pass(self):
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAIL", out)

    # --- R1 심링크 ---
    def test_broken_symlink_fails(self):
        link = os.path.join(self.root, ".claude/agents")
        os.remove(link)
        os.symlink("../.agents/WRONG", link)
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)
        self.assertIn("symlink", out.lower())

    def test_windows_backslash_readlink_passes(self):
        # R1 — Windows os.readlink()는 '..\\.agents\\agents' 형태로 반환한다.
        # 정규화 없이 슬래시 리터럴과 비교하면 정상 심링크를 FAIL로 오판정한다
        # (2026-07-21 주간 점검 실측). 표기 차이는 무결성 문제가 아니다.
        import importlib.util
        from unittest import mock
        spec = importlib.util.spec_from_file_location(
            "integrity_check_mod",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "integrity-check.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        real_readlink = os.readlink
        with mock.patch.object(mod.os, "readlink",
                               side_effect=lambda p: real_readlink(p).replace("/", "\\")):
            results = mod.check_symlinks(self.root)
        fails = [r for r in results if r[1] == "FAIL"]
        self.assertEqual(fails, [], "백슬래시 표기 심링크가 FAIL로 오판정됨: %r" % fails)

    # --- R2 .claude/ 실파일 침입 ---
    def test_claude_intrusion_real_file_fails(self):
        write(os.path.join(self.root, ".claude/rogue.md"), "real file\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("rogue.md", out)

    def test_claude_intrusion_gitignored_file_ok(self):
        # 런타임 산출물이 gitignore되면 침입이 아니다(scheduled_tasks.lock 계열)
        write(os.path.join(self.root, ".claude/scheduled_tasks.lock"), "lock\n")
        with open(os.path.join(self.root, ".gitignore"), "a", encoding="utf-8") as f:
            f.write(".claude/scheduled_tasks.lock\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertNotIn("scheduled_tasks.lock", out.replace("SKIP", ""))

    # --- R3 스킬 frontmatter ---
    def test_skill_missing_description_fails(self):
        write(os.path.join(self.root, ".agents/skills/bar/SKILL.md"),
              "---\nname: bar\n---\n# bar\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("bar", out)

    def test_skill_crlf_fails(self):
        p = os.path.join(self.root, ".agents/skills/bar/SKILL.md")
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("---\r\nname: bar\r\ndescription: x\r\n---\r\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("bar", out)

    # --- R13 description 하드캡 (초과 시 Codex 로더가 스킬을 거부 — 2026-07-20 실장애) ---
    def test_skill_description_over_hardcap_fails(self):
        write(os.path.join(self.root, ".agents/skills/bar/SKILL.md"),
              '---\nname: bar\ndescription: "%s"\n---\n# bar\n' % ("x" * 1100))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("bar", out)
        self.assertIn("1024", out)

    def test_skill_description_at_hardcap_ok(self):
        # 경계값: 정확히 1024자는 통과해야 한다(오탐 방지)
        write(os.path.join(self.root, ".agents/skills/bar/SKILL.md"),
              '---\nname: bar\ndescription: "%s"\n---\n# bar\n' % ("x" * 1024))
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)

    # --- R19 상시 노출 토큰 예산 ---
    def _write_skill_catalog_bytes(self, total):
        shutil.rmtree(os.path.join(self.root, ".agents/skills"))
        os.makedirs(os.path.join(self.root, ".agents/skills"))
        remaining = total
        index = 0
        while remaining:
            size = min(1000, remaining)
            name = "skill-%02d" % index
            write(os.path.join(self.root, ".agents/skills", name, "SKILL.md"),
                  '---\nname: %s\ndescription: "%s"\n---\n# %s\n'
                  % (name, "x" * size, name))
            remaining -= size
            index += 1
        write_korean_views(self.root)

    def _write_skill_catalog_descriptions(self, descriptions):
        shutil.rmtree(os.path.join(self.root, ".agents/skills"))
        os.makedirs(os.path.join(self.root, ".agents/skills"))
        for index, desc in enumerate(descriptions):
            name = "skill-%02d" % index
            write(os.path.join(self.root, ".agents/skills", name, "SKILL.md"),
                  '---\nname: %s\ndescription: "%s"\n---\n# %s\n'
                  % (name, desc, name))
        write_korean_views(self.root)

    def test_skill_description_catalog_over_budget_fails(self):
        """R19: description UTF-8 합계 9,001바이트부터 FAIL."""
        self._write_skill_catalog_bytes(9_001)
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R19", out)
        self.assertIn("9001", out.replace(",", ""))

    def test_skill_description_catalog_at_budget_ok(self):
        """R19: description UTF-8 합계 정확히 9,000바이트는 통과."""
        self._write_skill_catalog_bytes(9_000)
        code, out = run_check(self.root)
        self.assertNotIn("FAIL R19", out)

    def test_skill_description_multibyte_catalog_over_budget_fails(self):
        """R19: 글자 수가 아니라 UTF-8 바이트 합계를 검사한다."""
        self._write_skill_catalog_descriptions(["가" * 1000] * 3 + ["x"])
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R19", out)
        self.assertIn("9001", out.replace(",", ""))

    def test_skill_description_multibyte_catalog_at_budget_ok(self):
        """R19: 한글 description 합계도 정확히 9,000바이트면 통과한다."""
        self._write_skill_catalog_descriptions(["가" * 1000] * 3)
        code, out = run_check(self.root)
        self.assertNotIn("FAIL R19", out)

    def test_claude_budget_over_fails(self):
        """R19: CLAUDE.md가 5,500바이트를 넘으면 FAIL."""
        prefix = "@AGENTS.md\n"
        write(os.path.join(self.root, "CLAUDE.md"),
              prefix + "x" * (5_501 - len(prefix.encode("utf-8"))))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R19", out)
        self.assertIn("CLAUDE.md", out)

    def test_claude_budget_at_limit_ok(self):
        """R19: CLAUDE.md 정확히 5,500바이트는 통과."""
        prefix = "@AGENTS.md\n"
        write(os.path.join(self.root, "CLAUDE.md"),
              prefix + "x" * (5_500 - len(prefix.encode("utf-8"))))
        code, out = run_check(self.root)
        self.assertNotIn("FAIL R19", out)

    # --- R4 에이전트 frontmatter ---
    def test_agent_missing_tier_fails(self):
        write(os.path.join(self.root, ".agents/agents/foo.md"),
              "---\nname: foo\ndescription: x\ntools: Read\n---\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("foo", out)
        self.assertIn("tier", out.lower())

    # --- R12 Codex custom-agent 어댑터 ---
    def test_missing_codex_agent_adapter_fails(self):
        os.remove(os.path.join(self.root, ".codex/agents/foo.toml"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("foo", out)
        self.assertIn("adapter", out.lower())

    def test_orphan_codex_agent_adapter_fails(self):
        write_codex_adapter(self.root, name="ghost", description="Ghost", contract="ghost")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("ghost", out)

    def test_codex_agent_adapter_metadata_drift_fails(self):
        write_codex_adapter(self.root, description="Drifted description")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("description", out.lower())

    def test_codex_agent_adapter_contract_reference_fails(self):
        write_codex_adapter(self.root, contract="wrong")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("contract", out.lower())

    def test_codex_agent_adapter_fixed_model_fails(self):
        write_codex_adapter(self.root, extra='model = "fixed-model"\n')
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("model", out.lower())

    # --- R5 MOC 정합 (양방향) ---
    def test_moc_orphan_file_fails(self):
        # 파일은 있는데 인덱스에 없음
        write(os.path.join(self.root, "docs/adr/002-new.md"), "# 002\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("002-new.md", out)

    def test_moc_ghost_row_fails(self):
        # 인덱스에 있는데 파일 없음
        with open(os.path.join(self.root, "docs/README.md"), "a", encoding="utf-8") as f:
            f.write("- [ghost](adr/999-ghost.md)\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("999-ghost.md", out)

    # --- R6 CLAUDE.md 첫 줄 ---
    def test_claude_md_first_line_fails(self):
        write(os.path.join(self.root, "CLAUDE.md"), "# not an import\n@AGENTS.md\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("CLAUDE.md", out)

    # --- R7 gitignore 필수 항목 ---
    def test_gitignore_missing_entry_fails(self):
        write(os.path.join(self.root, ".gitignore"),
              "_workspace/\nproject/\n.agents/projects/*\n!.agents/projects/README.md\n")  # REGISTRY.md 누락
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("REGISTRY.md", out)

    def test_gitignore_missing_codex_agent_exception_fails(self):
        path = os.path.join(self.root, ".gitignore")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        write(path, text.replace("!.codex/agents/*.toml\n", ""))
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("!.codex/agents/*.toml", out)

    # --- R11 심링크 불가 설치처 → R1·R2 SKIP ---
    def test_non_symlink_installation_skips_r1_r2(self):
        link = os.path.join(self.root, ".claude/agents")
        os.remove(link)
        os.makedirs(link)  # 실디렉토리로 대체 (sync 스크립트 설치처 가정)
        write(os.path.join(link, "foo.md"),
              "---\nname: foo\ndescription: x\ntools: Read\ntier: implement\n---\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("SKIP", out)

    # --- R9 fail-loud: 핵심 디렉토리·파일 부재는 SKIP이 아니라 FAIL ---
    def test_missing_skills_dir_fails(self):
        shutil.rmtree(os.path.join(self.root, ".agents/skills"))
        # 심링크 dangling 부작용 회피 위해 링크도 정리하고 실디렉토리로 두지 않음 → R1도 별도 FAIL 가능
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("skills", out.lower())

    def test_missing_agents_dir_fails(self):
        shutil.rmtree(os.path.join(self.root, ".agents/agents"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("agents", out.lower())

    def test_missing_moc_fails(self):
        os.remove(os.path.join(self.root, "docs/README.md"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("MOC", out)

    def test_dangling_symlink_fails(self):
        # 심링크는 올바른 경로를 가리키지만 대상 실체가 사라진 경우 (rm -rf .agents/agents 손상)
        shutil.rmtree(os.path.join(self.root, ".agents/agents"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        # R1이 dangling을 잡아야 한다(SKIP·PASS 아님)
        self.assertRegex(out, r"FAIL R1.*agents")

    # --- R10 stdlib only ---
    def test_stdlib_only(self):
        with open(SCRIPT, encoding="utf-8") as f:
            src = f.read()
        for banned in ("import requests", "import yaml", "from yaml", "import numpy"):
            self.assertNotIn(banned, src)

    # --- R8 출력 형식 ---
    def test_output_has_summary_line(self):
        code, out = run_check(self.root)
        self.assertRegex(out, r"integrity:.*(pass|PASS)")

    def test_agents_budget_over_fails(self):
        """R14: AGENTS.md가 32,000바이트를 넘으면 FAIL."""
        write(os.path.join(self.root, "AGENTS.md"), "x" * 32_001)
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("R14", out)
        self.assertIn("32001", out.replace(",", ""))

    def test_agents_budget_at_limit_ok(self):
        """R14: 정확히 32,000바이트는 Codex 기본 한도 안전 여유 내 — FAIL 없음."""
        write(os.path.join(self.root, "AGENTS.md"), "x" * 32_000)
        code, out = run_check(self.root)
        self.assertNotIn("FAIL R14", out)

    # --- R18 Codex 프로젝트 설정 계약 ---
    def test_codex_config_legacy_hooks_key_fails(self):
        """R18: 폐기 예정 codex_hooks 별칭은 정식 hooks 키로 교체해야 한다."""
        write(os.path.join(self.root, ".codex/config.toml"),
              "project_doc_max_bytes = 65536\n\n"
              "[features]\n"
              "codex_hooks = true\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        self.assertIn("codex_hooks", out)

    def test_codex_config_doc_headroom_fails(self):
        """R18: 신뢰 저장소의 전역 지침 결합 여유는 64KiB로 고정한다."""
        write(os.path.join(self.root, ".codex/config.toml"),
              "project_doc_max_bytes = 32768\n\n"
              "[features]\n"
              "hooks = true\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        self.assertIn("65536", out)

    def test_codex_config_canonical_contract_ok(self):
        """R18: 정식 hooks 키와 64KiB 보조 한도 조합은 통과한다."""
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAIL R18", out)

    def test_codex_config_missing_inline_hook_event_fails(self):
        """R18: 실제 로딩되는 inline TOML에 필수 이벤트 3종이 모두 있어야 한다."""
        path = os.path.join(self.root, ".codex/config.toml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        write(path, text.replace("SessionStart", "Stop"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        self.assertIn("SessionStart", out)

    def test_codex_config_missing_handler_fails(self):
        """R18: 이벤트 이름만 있고 command handler가 없으면 FAIL한다."""
        path = os.path.join(self.root, ".codex/config.toml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        write(path, text.replace("[[hooks.PreToolUse.hooks]]", "[[hooks.Stop.hooks]]"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        self.assertIn("PreToolUse", out)

    def test_codex_config_wrong_matcher_fails(self):
        """R18: Codex 도구명을 놓치는 matcher 드리프트는 FAIL한다."""
        path = os.path.join(self.root, ".codex/config.toml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        write(path, text.replace('matcher = "apply_patch"', 'matcher = "Edit"'))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        self.assertIn("matcher", out)

    def test_codex_config_missing_agent_gate_fails(self):
        """R18: 발행 게이트 등록을 통째로 지우면 FAIL한다.

        이 항목이 없던 동안 `Agent` 매처 블록 전체를 삭제해도 R18이 PASS였다
        (독립 검증 2026-08-03 F6). ADR 037 때 생겨 ADR 038·042로 둘이 됐다가
        ADR 045로 `tier-gate` 하나만 남았으므로, 회귀를 잡는 것은 이 케이스 하나다.
        """
        path = os.path.join(self.root, ".codex/config.toml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        start = text.index('[[hooks.PreToolUse]]\nmatcher = "Agent|Task|spawn_agent"')
        end = text.index("[[hooks.PostToolUse]]")
        write(path, text[:start] + text[end:])
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        # R18 고유 문구로 고정한다 — `tier-gate.py`만 보면 같은 출력 안의
        # R20·R21 줄이 어서션을 대신 충족시켜, `CODEX_HOOK_COMMANDS`에서
        # 이 항목을 지우는 변이가 초록으로 통과한다(독립 검증 2026-08-07 C-03).
        self.assertIn("PreToolUse command missing contract: tier-gate.py", out)

    def test_claude_settings_missing_agent_gate_fails(self):
        """R21: `.claude/settings.json`에서 발행 게이트 등록이 사라지면 FAIL한다.

        R18은 Codex 쪽만 봐서, Claude 쪽 등록을 지워도 무결성 출력이 바이트
        단위로 동일했다(독립 검증 2026-08-04 C-03 실측). ADR 045로 `dispatch-gate`가
        사라진 뒤에도 이 자리에는 `tier-gate`의 경량 금지가 남아 있고, 유실이
        조용하다는 성질은 그대로다.
        """
        path = os.path.join(self.root, ".claude/settings.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data["hooks"]["PreToolUse"]:
            entry["hooks"] = [h for h in entry["hooks"]
                              if "tier-gate" not in h.get("command", "")]
        write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R21", out)
        self.assertIn("tier-gate.py", out)

    def test_claude_settings_intact_passes_r21(self):
        code, out = run_check(self.root)
        self.assertIn("PASS R21 Claude hooks tier-gate.py", out)
        # `gate-reminder`는 PreToolUse·PostToolUse 양쪽에 필수라 PASS 줄이 둘이다.
        # `assertIn`으로 두면 한쪽을 지워도 다른 쪽이 어서션을 충족시켜 변이가
        # 살아남는다 — 개수로 고정한다(독립 검증 2026-08-07 C-02).
        self.assertEqual(out.count("PASS R21 Claude hooks gate-reminder.py"), 2, out)

    def test_codex_config_wrong_command_fails(self):
        """R18: handler가 실제 스크립트·mode를 잃으면 FAIL한다."""
        path = os.path.join(self.root, ".codex/config.toml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        write(path, text.replace("gate-reminder.py --check", "gate-reminder.py --record"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        self.assertIn("PreToolUse", out)

    def test_codex_hooks_json_parallel_source_fails(self):
        """R18: 로딩이 확인되지 않은 병렬 hooks.json 원본을 다시 만들면 FAIL한다."""
        write(os.path.join(self.root, ".codex/hooks.json"), '{"hooks": {}}\n')
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R18", out)
        self.assertIn("hooks.json", out)

    def test_adr_ref_missing_fails(self):
        """R15: 항상-온 문서가 존재하지 않는 ADR을 참조하면 FAIL."""
        write(os.path.join(self.root, "CLAUDE.md"), "@AGENTS.md\n\n규칙 근거는 ADR 099 참조.\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("R15", out)
        self.assertIn("099", out)

    def test_adr_ref_enumeration_partial_missing_fails(self):
        """R15: 'ADR 001·098' 열거에서 098만 없으면 098만 FAIL(001은 통과)."""
        write(os.path.join(self.root, "AGENTS.md"), "# AGENTS.md\n근거(ADR 001·098).\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1)
        self.assertIn("098", out)
        self.assertNotIn("referenced ADR 001", out)

    def test_adr_refs_all_exist_ok(self):
        """R15: 실재하는 ADR 참조만 있으면 통과."""
        write(os.path.join(self.root, "AGENTS.md"), "# AGENTS.md\n근거는 ADR 001.\n")
        write_korean_views(self.root)  # AGENTS.md 변경 → 뷰 재생성(R16 오탐 방지)
        code, out = run_check(self.root)
        self.assertEqual(code, 0)
        self.assertNotIn("FAIL R15", out)

    def test_adr_ref_four_digit_number_not_matched(self):
        """R15: 'ADR 2026' 같은 4자리+ 숫자는 참조로 추출하지 않는다(F2 경계)."""
        write(os.path.join(self.root, "AGENTS.md"), "# AGENTS.md\n연도 표기 ADR 2026 텍스트.\n")
        code, out = run_check(self.root)
        self.assertNotIn("FAIL R15", out)

    # --- R16 AGENTS.ko.md 한글 뷰 source-hash (ADR 030 ⓐ) ---
    def test_agents_kr_stale_hash_fails(self):
        """R16: AGENTS.md 변경 후 뷰 미재생성 → source-hash 불일치 FAIL + 재생성 안내."""
        with open(os.path.join(self.root, "AGENTS.md"), "a", encoding="utf-8") as f:
            f.write("새 규칙 추가.\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R16", out)
        self.assertIn("regenerate", out)

    def test_agents_kr_matching_hash_ok(self):
        """R16: source-hash가 현재 AGENTS.md sha256[:12]과 일치하면 통과."""
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAIL R16", out)

    def test_agents_kr_missing_fails(self):
        """R16: 뷰 파일 부재는 FAIL — ADR 030 이후 뷰는 필수."""
        os.remove(os.path.join(self.root, "AGENTS.ko.md"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R16", out)
        self.assertIn("AGENTS.ko.md", out)

    def test_agents_kr_no_hash_line_fails(self):
        """R16: source-hash 줄이 없는 뷰는 대조 불가 → FAIL."""
        write(os.path.join(self.root, "AGENTS.ko.md"), "# 한글 다이제스트 (배너 없음)\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R16", out)

    def test_agents_kr_skip_when_no_agents_md(self):
        """R16: AGENTS.md·AGENTS.ko.md 모두 부재 → SKIP (repo-shape 안전, 원본 부재는 R14 몫)."""
        os.remove(os.path.join(self.root, "AGENTS.md"))
        os.remove(os.path.join(self.root, "AGENTS.ko.md"))
        code, out = run_check(self.root)
        self.assertNotIn("FAIL R16", out)
        self.assertIn("SKIP R16", out)

    # --- R17 README.ko.md 항목 집합 정합 (ADR 030 ⓑ) ---
    def test_skills_readme_ko_heading_mismatch_fails(self):
        """R17: 실존 스킬 누락 + 유령 항목 → 양방향 FAIL."""
        write(os.path.join(self.root, ".agents/skills/README.ko.md"),
              "# 스킬 한글 요약\n\n## ghost\n요약.\n")  # bar 누락 + ghost 유령
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R17", out)
        self.assertIn("bar", out)
        self.assertIn("ghost", out)

    def test_agents_readme_ko_heading_mismatch_fails(self):
        """R17: 에이전트 요약도 동일 — foo 누락 + ghost 유령 → FAIL."""
        write(os.path.join(self.root, ".agents/agents/README.ko.md"),
              "# 에이전트 한글 요약\n\n## ghost\n요약.\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R17", out)
        self.assertIn("foo", out)
        self.assertIn("ghost", out)

    def test_readme_ko_exact_match_ok(self):
        """R17: 항목 집합이 실제 집합과 1:1이면 통과(정상 픽스처)."""
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertNotIn("FAIL R17", out)

    def test_skills_readme_ko_missing_fails(self):
        """R17: 스킬 요약 뷰 부재는 FAIL."""
        os.remove(os.path.join(self.root, ".agents/skills/README.ko.md"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R17", out)
        self.assertIn("skills", out)

    def test_agents_readme_ko_missing_fails(self):
        """R17: 에이전트 요약 뷰 부재는 FAIL."""
        os.remove(os.path.join(self.root, ".agents/agents/README.ko.md"))
        code, out = run_check(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL R17", out)
        self.assertIn("agents", out)


class TestLightweightSection(unittest.TestCase):
    """R20 (ADR 040) — tier-gate의 판정 입력이 gitignore 대상이라 상태를 드러낸다."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="integrity-r20-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        make_good_fixture(self.root)

    def test_section_with_entries_passes(self):
        write(os.path.join(self.root, "REGISTRY.md"),
              "# r\n\n## 경량 모델 (설명)\n\n- **haiku** — 최저가\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("PASS R20", out)

    def test_missing_section_skips_not_fails(self):
        # 절을 안 채운 설치처는 결함이 아니라 설계된 상태다(harness-install이 그
        # 결과를 사용자에게 말한다). FAIL이면 새 설치처가 무결성 실패로 시작한다.
        write(os.path.join(self.root, "REGISTRY.md"), "# r\n\n## 설치처 프로필\n\n- **개인** — x\n")
        code, out = run_check(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("SKIP R20", out)
        self.assertNotIn("FAIL R20", out)

    def test_section_emptied_is_visible(self):
        # 항목만 지워도(절 제목은 남겨도) 게이트는 잠든다 — 그 상태가 출력에 뜬다.
        write(os.path.join(self.root, "REGISTRY.md"), "# r\n\n## 경량 모델\n\n설명뿐\n")
        _, out = run_check(self.root)
        self.assertIn("SKIP R20", out)


if __name__ == "__main__":
    utf8_stdio()
    unittest.main(verbosity=2)
