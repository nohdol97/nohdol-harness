#!/usr/bin/env python3
"""tier-gate 훅 회귀 테스트 — 스펙 완료 기준 C1~C10.

스펙: docs/specs/2026-08-03-tier-gate-hook.md
"""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "tier_gate_hook", os.path.join(HERE, "tier-gate.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def payload(subagent_type=None, model=None, tool_name="Agent", **extra):
    ti = {"prompt": "…", "description": "…"}
    if subagent_type is not None:
        ti["subagent_type"] = subagent_type
    if model is not None:
        ti["model"] = model
    ti.update(extra)
    return json.dumps({"tool_name": tool_name, "tool_input": ti})


def run(raw, base=None):
    """훅을 stdin 텍스트로 실행하고 (exit code, stderr)를 돌려준다."""
    err = io.StringIO()
    env = {"CLAUDE_PROJECT_DIR": base} if base else {}
    with mock.patch("sys.stdin", io.StringIO(raw)), \
         mock.patch.dict(os.environ, env), \
         contextlib.redirect_stderr(err):
        rc = hook.main()
    return rc, err.getvalue()


class Tier(unittest.TestCase):
    """실제 저장소의 에이전트 정의에서 tier를 읽는다(하드코딩 금지)."""

    def test_reads_declared_tier(self):
        root = os.path.dirname(HERE)  # .agents/
        base = os.path.dirname(root)
        self.assertEqual(hook.read_tier(base, "explorer"), "explore")
        self.assertEqual(hook.read_tier(base, "reviewer"), "design")

    def test_unknown_agent_is_none(self):
        base = os.path.dirname(os.path.dirname(HERE))
        self.assertIsNone(hook.read_tier(base, "general-purpose"))
        self.assertIsNone(hook.read_tier(base, "../../etc/passwd"))

    def test_missing_tier_key_is_none(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".agents", "agents"))
            p = os.path.join(d, ".agents", "agents", "nameless.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("---\nname: nameless\ndescription: x\n---\n본문\n")
            self.assertIsNone(hook.read_tier(d, "nameless"))


class Gate(unittest.TestCase):
    def setUp(self):
        self.base = os.path.dirname(os.path.dirname(HERE))

    def test_c1_explore_without_model_is_blocked(self):
        # C1 — 미지정이 곧 세션 모델 상속이고, 그것이 §9를 덮어 온 원인이다
        # (실측 2026-08-03: explorer 37세션 중 25건이 explore에 배정된 적 없는
        # 최상위 모델로 발행됐고, 그 이전 구간에는 검증 25건이 표준 모델로 돌았다).
        rc, err = run(payload("explorer"), self.base)
        self.assertEqual(rc, hook.BLOCK_EXIT)
        self.assertIn("explore", err)
        self.assertIn("9", err)  # §9 표를 가리켜야 한다

    def test_c2_design_without_model_is_blocked(self):
        rc, err = run(payload("reviewer"), self.base)
        self.assertEqual(rc, hook.BLOCK_EXIT)
        self.assertIn("design", err)

    def test_c3_model_given_passes(self):
        for agent in ("explorer", "reviewer", "implementer"):
            rc, err = run(payload(agent, model="sonnet"), self.base)
            self.assertEqual(rc, 0, agent)
            self.assertEqual(err, "", agent)

    def test_c4_model_value_is_not_judged(self):
        # ADR 005 탈모델명 — 훅은 무엇을 골랐는지 판정하지 않는다. 어떤 값이든
        # 지정 자체가 상속을 끊으므로 통과시키고, 적절성 판단은 §9를 읽는
        # 세션의 몫이다. 모델명을 코드에 박으면 라인업이 바뀔 때마다 훅이 낡는다.
        for m in ("opus", "sonnet", "haiku", "무엇이든"):
            rc, _ = run(payload("explorer", model=m), self.base)
            self.assertEqual(rc, 0, m)

    def test_c12_inherit_is_treated_as_unset(self):
        # C12 — `inherit`는 모델명이 아니라 "상속하라"는 지시어라 미지정과 결과가
        # 같다. 통과시키면 게이트가 막으려는 상태가 한 단어로 되살아난다
        # (독립 검증 2026-08-03 F6 — 실측으로 통과하던 우회).
        for v in ("inherit", "Inherit", " INHERIT "):
            rc, err = run(payload("explorer", model=v), self.base)
            self.assertEqual(rc, hook.BLOCK_EXIT, v)
            self.assertIn("explore", err)

    def test_c5_unknown_agent_type_passes(self):
        # 하네스 로스터 밖(general-purpose 등)은 §9가 관장하지 않는다.
        rc, err = run(payload("general-purpose"), self.base)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c6_other_tools_pass(self):
        rc, _ = run(payload("explorer", tool_name="Bash"), self.base)
        self.assertEqual(rc, 0)

    def test_c7_no_subagent_type_passes(self):
        rc, _ = run(payload(None), self.base)
        self.assertEqual(rc, 0)

    def test_c8_malformed_stdin_fails_open(self):
        for raw in ("", "not json", "[]", '{"tool_input": null}'):
            rc, err = run(raw, self.base)
            self.assertEqual(rc, 0, raw)
            self.assertEqual(err, "", raw)

    def test_c9_unreadable_definitions_fail_open(self):
        # 정의를 못 읽으면 통과다 — 비용·품질 규칙이지 §3 가드레일이 아니므로
        # 판독 실패로 작업을 막지 않는다(기존 훅 3종과 같은 방향).
        with tempfile.TemporaryDirectory() as d:
            rc, err = run(payload("explorer"), d)
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")

    def test_c10_exception_fails_open(self):
        with mock.patch.object(hook, "read_tier", side_effect=RuntimeError):
            rc, err = run(payload("explorer"), self.base)
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
