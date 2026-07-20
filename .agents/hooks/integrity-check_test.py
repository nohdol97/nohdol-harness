#!/usr/bin/env python3
"""integrity-check 회귀 테스트 — 스펙 docs/specs/2026-07-19-integrity-check-script.md 완료 기준.

실행: python3 .agents/hooks/integrity-check_test.py   (스크립트 수정 시 반드시 통과)
부수 효과: 임시 디렉토리만 사용하며 전부 정리한다(git init 포함, 픽스처 내부에서만).
"""
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


def make_good_fixture(root):
    """규약을 모두 지키는 최소 하네스 구조 + git init(.gitignore 판정용)."""
    # 원본 디렉토리
    write(os.path.join(root, ".agents/agents/foo.md"),
          "---\nname: foo\ndescription: A test agent\ntools: Read\ntier: implement\n---\n# foo\n")
    write(os.path.join(root, ".agents/skills/bar/SKILL.md"),
          "---\nname: bar\ndescription: A test skill\n---\n# bar\n")
    write_codex_adapter(root)
    # .claude 심링크
    claude = os.path.join(root, ".claude")
    os.makedirs(claude, exist_ok=True)
    os.symlink("../.agents/agents", os.path.join(claude, "agents"))
    os.symlink("../.agents/skills", os.path.join(claude, "skills"))
    write(os.path.join(claude, "settings.json"), "{}\n")
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


if __name__ == "__main__":
    utf8_stdio()
    unittest.main(verbosity=2)
