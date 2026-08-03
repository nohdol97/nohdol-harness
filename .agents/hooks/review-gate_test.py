#!/usr/bin/env python3
"""review-gate 훅 회귀 테스트 — 스펙 완료 기준 C1~C10(C11은 리마인더 스위트).

스펙: docs/specs/2026-08-03-review-gate-hook.md
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)  # 훅이 `from _common import ...`을 하므로 경로가 필요하다
_spec = importlib.util.spec_from_file_location(
    "review_gate_hook", os.path.join(HERE, "review-gate.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

import _common  # noqa: E402  — C10이 판독기의 위치를 고정한다

PERSONAL_REGISTRY = """# 레지스트리

## 설치처 프로필

- **개인** — 하네스 파일 수정·커밋·푸시 가능.

## 경로 규약
"""

CORPORATE_REGISTRY = """# 레지스트리

## 설치처 프로필

- **사내** — 추적 하네스 파일 수정 금지.

## 경로 규약
"""


def base_with(registry_text):
    """임시 루트에 REGISTRY.md를 깔고 경로를 돌려주는 컨텍스트 매니저."""
    d = tempfile.TemporaryDirectory()
    if registry_text is not None:
        with open(os.path.join(d.name, "REGISTRY.md"), "w", encoding="utf-8") as f:
            f.write(registry_text)
    return d


def payload(subagent_type=None, prompt="…", tool_name="Agent", **extra):
    ti = {"description": "…", "prompt": prompt}
    if subagent_type is not None:
        ti["subagent_type"] = subagent_type
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


class Gate(unittest.TestCase):
    def test_c1_corporate_blocks_reviewer(self):
        # C1 — 사용자가 지목한 비용 축. 차단 메시지는 대체 절차를 알려야 한다.
        # **종료 코드는 리터럴 2로 못박는다** — PreToolUse가 키로 삼는 값이
        # 그것이라, 상수에만 대고 비교하면 BLOCK_EXIT를 0이나 1로 바꾸는 변이가
        # 스위트를 통과한다(독립 검증 F3 — 실제로 두 변이가 살아남았다).
        with base_with(CORPORATE_REGISTRY) as d:
            rc, err = run(payload("reviewer"), d)
        self.assertEqual(rc, 2)
        self.assertEqual(rc, hook.BLOCK_EXIT)
        self.assertIn("reviewer", err)
        self.assertIn("038", err)          # 계약 문서를 가리켜야 한다
        self.assertIn(hook.OVERRIDE, err)  # 우회 방법도 함께

    def test_c2_task_tool_name_also_blocks(self):
        # C2 — matcher가 "Task"로도 발화하므로 그 갈래도 판정한다. AGENT_TOOLS를
        # ("Agent",)로 줄이는 변이가 통과하던 구멍이다(독립 검증 F4).
        with base_with(CORPORATE_REGISTRY) as d:
            rc, _ = run(payload("reviewer", tool_name="Task"), d)
        self.assertEqual(rc, 2)

    def test_c3_personal_passes(self):
        # 개인 설치처의 동작은 한 바이트도 바뀌지 않는다.
        with base_with(PERSONAL_REGISTRY) as d:
            rc, err = run(payload("reviewer"), d)
            self.assertEqual(rc, 0)
            self.assertEqual(err, "")

    def test_c4_missing_registry_passes(self):
        # 미상은 차단하지 않는다 — fail-open의 방향이 "검증이 돌아간다"이다.
        with base_with(None) as d:
            rc, err = run(payload("reviewer"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c5_non_reviewer_types_pass(self):
        # 빌드 측은 사용자가 지목한 비용 축이 아니다 — 구현 위임까지 끊으면
        # orchestrate의 3파일 위임 규칙이 무너진다.
        #
        # **`integrator`가 여기 있는 것이 이 테스트의 핵심이다.** 규칙은 리뷰
        # 리포트 fan-in을 끄지만 훅은 타입으로 막지 않는다 — 같은 타입이
        # `project-status` Phase 2의 상태 fan-in에도 쓰여, 타입 차단은 그 스킬을
        # 사내에서 통째로 죽인다(정당한 우회도 없다). 독립 검증 2인이 각각
        # 지적했고, 이 케이스가 그 축소를 고정한다.
        with base_with(CORPORATE_REGISTRY) as d:
            for agent in ("integrator", "implementer", "explorer",
                          "infra-specialist", "troubleshooter", "architect",
                          "general-purpose"):
                rc, err = run(payload(agent), d)
                self.assertEqual(rc, 0, agent)
                self.assertEqual(err, "", agent)

    def test_c6_override_marker_passes(self):
        # 사용자 명시 요청 — 비용을 그 자리에서 승인한 상태다(8절 선례).
        with base_with(CORPORATE_REGISTRY) as d:
            rc, err = run(payload("reviewer", prompt="Verify the diff. [review-ok]"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c7_other_tools_pass(self):
        with base_with(CORPORATE_REGISTRY) as d:
            rc, _ = run(payload("reviewer", tool_name="Bash"), d)
        self.assertEqual(rc, 0)

    def test_c8_malformed_stdin_fails_open(self):
        with base_with(CORPORATE_REGISTRY) as d:
            for raw in ("", "not json", "[]", '{"tool_input": null}',
                        '{"tool_name": "Agent", "tool_input": {}}'):
                rc, err = run(raw, d)
                self.assertEqual(rc, 0, raw)
                self.assertEqual(err, "", raw)

    def test_c9_exception_fails_open(self):
        with base_with(CORPORATE_REGISTRY) as d:
            with mock.patch.object(hook, "read_profile", side_effect=RuntimeError):
                rc, err = run(payload("reviewer"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c9b_non_string_subagent_type_passes(self):
        with base_with(CORPORATE_REGISTRY) as d:
            rc, _ = run(payload(subagent_type=123), d)
            self.assertEqual(rc, 0)
            rc, _ = run(payload(None), d)
            self.assertEqual(rc, 0)


class SharedProfileReader(unittest.TestCase):
    """C10 — 판독기가 `_common`에 있고 이 훅이 그것을 쓴다(위치 고정).

    파서의 의미 축(코드 펜스·제목 레벨·다른 절 산문)은 harness-review-reminder
    스위트가 같은 함수에 대고 이미 판정한다 — 여기서 다시 세우면 같은 검사가
    두 벌이 된다(§16). 이 클래스가 막는 회귀는 하나다: 판독기를 훅 안으로
    되돌려 복제하는 것.
    """

    def test_c10_hook_uses_the_shared_reader(self):
        self.assertIs(hook.read_profile, _common.read_profile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
