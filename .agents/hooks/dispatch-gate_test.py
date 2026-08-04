#!/usr/bin/env python3
"""dispatch-gate 훅 회귀 테스트 — 스펙 완료 기준 C1~C11(C12는 리마인더 스위트).

스펙: docs/specs/2026-08-04-dispatch-gate-hook.md
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
    "dispatch_gate_hook", os.path.join(HERE, "dispatch-gate.py")
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

# 이 하네스가 실제로 발행하는 역할 전량 + 로스터 밖 타입. `infra-specialist`만
# 빠져 있고, 그 하나는 C6이 반대 방향으로 고정한다.
BLOCKED_AGENTS = (
    "reviewer", "implementer", "explorer", "troubleshooter",
    "architect", "integrator", "general-purpose", "Explore", "claude",
)


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
        # C1 — 초판이 막던 축은 그대로 막힌다. 차단 메시지는 대체 절차를 알려야 한다.
        # **종료 코드는 리터럴 2로 못박는다** — PreToolUse가 키로 삼는 값이
        # 그것이라, 상수에만 대고 비교하면 BLOCK_EXIT를 0이나 1로 바꾸는 변이가
        # 스위트를 통과한다(ADR 038 독립 검증 F3 — 실제로 두 변이가 살아남았다).
        with base_with(CORPORATE_REGISTRY) as d:
            rc, err = run(payload("reviewer"), d)
        self.assertEqual(rc, 2)
        self.assertEqual(rc, hook.BLOCK_EXIT)
        self.assertIn("reviewer", err)
        self.assertIn("042", err)  # 계약 문서를 가리켜야 한다

    def test_c2_task_tool_name_also_blocks(self):
        # C2 — matcher가 "Task"로도 발화하므로 그 갈래도 판정한다. AGENT_TOOLS를
        # ("Agent",)로 줄이는 변이가 통과하던 구멍이다(ADR 038 독립 검증 F4).
        with base_with(CORPORATE_REGISTRY) as d:
            rc, _ = run(payload("reviewer", tool_name="Task"), d)
        self.assertEqual(rc, 2)

    def test_c3_personal_passes(self):
        # 개인 설치처의 동작은 한 바이트도 바뀌지 않는다.
        with base_with(PERSONAL_REGISTRY) as d:
            for agent in BLOCKED_AGENTS:
                rc, err = run(payload(agent), d)
                self.assertEqual(rc, 0, agent)
                self.assertEqual(err, "", agent)

    def test_c4_missing_registry_passes(self):
        # 미상은 차단하지 않는다 — fail-open의 방향이 "발행이 돌아간다"이다.
        with base_with(None) as d:
            rc, err = run(payload("reviewer"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c5_every_role_blocks(self):
        # C5 — **초판에서 뒤집힌 케이스다.** 판정 축이 "어느 역할인가"에서
        # "발행인가"로 바뀌었으므로 빌드 측·fan-in·로스터 밖이 전부 막힌다.
        # EXEMPT_AGENTS에 역할을 하나라도 더 넣는 변이가 여기서 죽는다.
        with base_with(CORPORATE_REGISTRY) as d:
            for agent in BLOCKED_AGENTS:
                rc, err = run(payload(agent), d)
                self.assertEqual(rc, 2, agent)
                self.assertIn("dispatch-gate", err, agent)

    def test_c6_infra_specialist_is_the_only_exemption(self):
        # C6 — 비용이 아니라 블라스트 반경으로 판정하는 유일한 축(7절 5항
        # admission 선확인). 대소문자·여백 변형도 같은 값으로 읽혀야 한다.
        with base_with(CORPORATE_REGISTRY) as d:
            for form in ("infra-specialist", "  infra-specialist  ",
                         "Infra-Specialist"):
                rc, err = run(payload(form), d)
                self.assertEqual(rc, 0, form)
                self.assertEqual(err, "", form)

    def test_c7_other_tools_pass(self):
        with base_with(CORPORATE_REGISTRY) as d:
            rc, _ = run(payload("reviewer", tool_name="Bash"), d)
        self.assertEqual(rc, 0)

    def test_c8_malformed_stdin_fails_open(self):
        # 형식 자체가 성립하지 않는 입력만 여기 남는다. `tool_input`이 빈 dict인
        # 경우는 **형식 불명이 아니라 타입 미지정 발행**이므로 C9b가 가져갔다.
        with base_with(CORPORATE_REGISTRY) as d:
            for raw in ("", "not json", "[]", '{"tool_input": null}',
                        '{"tool_name": "Agent", "tool_input": []}'):
                rc, err = run(raw, d)
                self.assertEqual(rc, 0, raw)
                self.assertEqual(err, "", raw)

    def test_c9_exception_fails_open(self):
        with base_with(CORPORATE_REGISTRY) as d:
            with mock.patch.object(hook, "read_profile", side_effect=RuntimeError):
                rc, err = run(payload("reviewer"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c9b_missing_or_non_string_type_still_blocks(self):
        # C9b — **초판에서 뒤집힌 두 번째 케이스.** 타입 미지정은 기본 에이전트로
        # 떨어질 뿐 비용은 그대로다. 미지정을 통과시키던 초판의 분기를 되살리는
        # 변이가 여기서 죽는다. 메시지는 빈 타입명을 그대로 노출하지 않는다.
        with base_with(CORPORATE_REGISTRY) as d:
            rc, err = run(payload(None), d)
            self.assertEqual(rc, 2)
            self.assertIn("타입 미지정", err)
            rc, _ = run(payload(subagent_type=123), d)
            self.assertEqual(rc, 2)
            rc, _ = run('{"tool_name": "Agent", "tool_input": {}}', d)
            self.assertEqual(rc, 2)

    def test_c11_no_override_marker_exists(self):
        # C11 — 사용자 결정 2026-08-04 "사내에선 예외 없음". 초판의 `[review-ok]`는
        # 폐기됐고, **되살리는 변이를 이 케이스가 잡는다** — 상수 부재만 보면
        # 이름을 바꿔 되살리는 변이가 통과하므로 동작으로도 확인한다.
        self.assertFalse(hasattr(hook, "OVERRIDE"))
        with base_with(CORPORATE_REGISTRY) as d:
            for marker in ("[review-ok]", "[agent-ok]", "[dispatch-ok]",
                           "[light-ok]", "[no-test]"):
                rc, _ = run(payload("reviewer", prompt="Verify. " + marker), d)
                self.assertEqual(rc, 2, marker)


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
