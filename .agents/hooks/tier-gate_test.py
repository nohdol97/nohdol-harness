#!/usr/bin/env python3
"""tier-gate 훅 회귀 테스트 — 스펙 완료 기준 C1~C14.

스펙: docs/specs/2026-08-03-tier-gate-hook.md
결정: docs/adr/040-tier-gate-inversion-lightweight-ban.md
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
sys.path.insert(0, HERE)  # _common을 훅과 같은 방식으로 찾게 한다
_spec = importlib.util.spec_from_file_location(
    "tier_gate_hook", os.path.join(HERE, "tier-gate.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

REPO = os.path.dirname(os.path.dirname(HERE))


def payload(subagent_type=None, model=None, tool_name="Agent", prompt="…", **extra):
    ti = {"prompt": prompt, "description": "…"}
    if subagent_type is not None:
        ti["subagent_type"] = subagent_type
    if model is not None:
        ti["model"] = model
    ti.update(extra)
    return json.dumps({"tool_name": tool_name, "tool_input": ti})


def codex_payload(agent_type=None, message="…", **extra):
    """Current Codex spawn_agent schema — do not reuse Claude field names."""
    ti = {"message": message}
    if agent_type is not None:
        ti["agent_type"] = agent_type
    ti.update(extra)
    return json.dumps({"tool_name": "spawn_agent", "tool_input": ti})


def run(raw, base=None):
    """훅을 stdin 텍스트로 실행하고 (exit code, stderr)를 돌려준다."""
    err = io.StringIO()
    env = {"CLAUDE_PROJECT_DIR": base} if base else {}
    with mock.patch("sys.stdin", io.StringIO(raw)), \
         mock.patch.dict(os.environ, env), \
         contextlib.redirect_stderr(err):
        rc = hook.main()
    return rc, err.getvalue()


@contextlib.contextmanager
def fixture(lightweight="- **haiku** — 최저가 등급\n", heading="## 경량 모델 (설명)"):
    """티어 선언 에이전트 2개(explore·design) + 「경량 모델」 절을 갖춘 임시 루트.

    판정 입력 둘을 여기서 통제한다 — 실제 저장소를 읽는 경로는 Wiring이 따로
    검증한다(하드코딩 금지: 목록도 티어도 파일에서 온다).
    """
    with tempfile.TemporaryDirectory() as d:
        agents = os.path.join(d, ".agents", "agents")
        os.makedirs(agents)
        for name, tier in (("collector", "explore"), ("judge", "design")):
            with open(os.path.join(agents, name + ".md"), "w", encoding="utf-8") as f:
                f.write("---\nname: %s\ndescription: x\ntier: %s\n---\n본문\n"
                        % (name, tier))
        body = "# 레지스트리\n\n## 설치처 프로필\n\n- **개인** — 설명\n\n"
        if lightweight is not None:
            body += "%s\n\n%s\n" % (heading, lightweight)
        with open(os.path.join(d, "REGISTRY.md"), "w", encoding="utf-8") as f:
            f.write(body)
        yield d


class Blocking(unittest.TestCase):
    def test_c1_lightweight_model_is_blocked(self):
        # C1 — 이 게이트의 존재 이유. 2026-08-03 실사례: 앞 방향의 훅이 미지정을
        # 막고 "골라 지정하라"고 지시하자 세션이 경량 모델로 재발행했다.
        with fixture() as d:
            rc, err = run(payload("collector", model="haiku"), d)
        self.assertEqual(rc, hook.BLOCK_EXIT)
        self.assertIn("haiku", err)
        self.assertIn("explore", err)  # 티어를 알려야 무엇을 고를지 판단한다
        self.assertIn("9", err)        # §9 표를 가리켜야 한다

    def test_c2_full_model_id_matches_by_substring(self):
        # C2 — 목록은 등급 이름만 적고 별칭과 전체 ID를 함께 잡는다. 버전·날짜가
        # 붙은 실제 모델 ID로 우회되면 목록을 라인업마다 갱신해야 한다.
        with fixture() as d:
            for m in ("claude-haiku-4-5-20251001", "HAIKU", " haiku "):
                rc, _ = run(payload("collector", model=m), d)
                self.assertEqual(rc, hook.BLOCK_EXIT, m)

    def test_c13_block_exit_is_literal_two(self):
        # C13 — PreToolUse에서 차단을 뜻하는 값은 2뿐이다. 0·1로 바뀌면 게이트가
        # 조용히 무력해지므로 상수를 통해서가 아니라 리터럴로 고정한다
        # (독립 검증 2026-08-03이 그 훅에서 같은 변이를 지적했다).
        self.assertEqual(hook.BLOCK_EXIT, 2)
        with fixture() as d:
            rc, _ = run(payload("collector", model="haiku"), d)
        self.assertEqual(rc, 2)

    def test_c17_override_does_not_reach_design_tier(self):
        # C17 — 전역 정책은 조항이 둘이다: 경량 예외("사용자가 명시적으로 요청")와,
        # 그와 **별도인** 검증·리뷰·최종 확인의 절대 금지. 표식을 티어 판정 앞에
        # 두면 후자가 한 단어로 풀린다(독립 검증 2026-08-04 F1 — 실측으로 통과했다).
        with fixture() as d:
            rc, err = run(payload("judge", model="haiku",
                                  prompt="빠르게 검증 %s" % hook.OVERRIDE), d)
        self.assertEqual(rc, hook.BLOCK_EXIT)
        self.assertIn("우회가 없습니다", err)  # 왜 안 통하는지 알려야 한다

    def test_c18_word_boundary_prevents_false_block(self):
        # C18 — 맨 부분 문자열이면 다른 벤더 등급명을 오차단한다(독립 검증 F2:
        # 항목 `mini`가 `gemini-2.5-pro`를 막았고, 한 글자 항목은 전 발행을 막았다).
        with fixture(lightweight="- **mini** — 가상 항목\n") as d:
            rc, _ = run(payload("collector", model="gemini-2.5-pro"), d)
            self.assertEqual(rc, 0, "낱말 내부의 우연한 일치는 차단하지 않는다")
            for m in ("mini", "gpt-4-mini", "MINI-2"):
                rc, _ = run(payload("collector", model=m), d)
                self.assertEqual(rc, hook.BLOCK_EXIT, m)

    def test_c19_empty_list_item_does_not_block_everything(self):
        # C19 — 빈 항목이 집합에 들어가면 어떤 모델에도 매칭돼 fail-open 설계가
        # fail-closed로 뒤집힌다(독립 검증 F5, 변이로 재현된 생존).
        with fixture(lightweight="- **** — 빈 라벨\n- ****\n") as d:
            rc, err = run(payload("collector", model="opus"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c14_task_tool_name_also_fires(self):
        # C14 — matcher가 Task로 걸린 경로도 판정한다. 갈래가 지워지면 그 경로의
        # 발행이 통째로 통과한다.
        with fixture() as d:
            rc, _ = run(payload("collector", model="haiku", tool_name="Task"), d)
        self.assertEqual(rc, hook.BLOCK_EXIT)

    def test_c21_codex_spawn_agent_tool_name_also_fires(self):
        # C21 — Codex는 역할을 agent_type에 싣는다. 도구명만 Codex로 바꾸고
        # Claude의 subagent_type을 읽으면 design 경량 금지가 조용히 통과한다.
        with fixture() as d:
            rc, _ = run(codex_payload("judge", model="haiku"), d)
        self.assertEqual(rc, hook.BLOCK_EXIT)

    def test_c22_codex_message_carries_lightweight_override(self):
        # C22 — Codex의 프롬프트 필드는 message다. explore 티어의 명시적 예외가
        # Claude 전용 prompt만 읽는 바람에 막히는 반대 방향 회귀도 고정한다.
        with fixture() as d:
            rc, err = run(codex_payload(
                "collector", model="haiku", message="빠른 확인 %s" % hook.OVERRIDE), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")


class Passing(unittest.TestCase):
    def test_c3_unset_model_passes(self):
        # C3 — 반전의 핵심. 미지정은 부모 세션 모델 상속이고 세션은 상위·표준
        # 둘 중 하나라 경량에 닿지 않는다. 여기를 막으면 사용자 전역 정책의
        # 기본값("명시하지 않는다")과 정면으로 충돌한다.
        with fixture() as d:
            rc, err = run(payload("collector"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c4_inherit_passes(self):
        # C4 — `inherit`는 상속 지시어라 미지정과 결과가 같다. 앞 방향에서는
        # 둘 다 차단이었으므로 이 케이스도 함께 뒤집힌다.
        with fixture() as d:
            for v in ("inherit", "Inherit", " INHERIT "):
                rc, err = run(payload("collector", model=v), d)
                self.assertEqual(rc, 0, v)
                self.assertEqual(err, "", v)

    def test_c5_non_lightweight_models_pass(self):
        # C5 — 티어 적합성은 보지 않는다. explore에 상위 모델을 골라도 통과하며
        # 그 판단은 §9를 읽는 세션의 몫이다(이 훅이 막는 것은 절대 금지 하나).
        with fixture() as d:
            for m in ("opus", "sonnet", "claude-opus-5", "무엇이든"):
                rc, err = run(payload("collector", model=m), d)
                self.assertEqual(rc, 0, m)
                self.assertEqual(err, "", m)

    def test_c6_override_marker_passes(self):
        # C6 — §9 경량 금지의 유일한 예외(사용자가 명시적으로 "빠르게/가볍게"를
        # 요청)를 그대로 옮긴 우회다.
        with fixture() as d:
            rc, err = run(payload("collector", model="haiku",
                                  prompt="빠른 확인 %s" % hook.OVERRIDE), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c7_roster_external_type_passes(self):
        with fixture() as d:
            rc, err = run(payload("general-purpose", model="haiku"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c8_missing_lightweight_section_passes(self):
        # C8 — 절을 안 채운 설치처에서는 발화하지 않는다(fail-open). 비용·품질
        # 규칙이지 3절 가드레일이 아니므로 판정 입력 부재로 작업을 막지 않는다.
        with fixture(lightweight=None) as d:
            rc, err = run(payload("collector", model="haiku"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c9_other_tools_pass(self):
        with fixture() as d:
            rc, _ = run(payload("collector", model="haiku", tool_name="Bash"), d)
        self.assertEqual(rc, 0)

    def test_c10_malformed_stdin_fails_open(self):
        with fixture() as d:
            for raw in ("", "not json", "[]", '{"tool_input": null}'):
                rc, err = run(raw, d)
                self.assertEqual(rc, 0, raw)
                self.assertEqual(err, "", raw)

    def test_c11_unreadable_definitions_fail_open(self):
        with tempfile.TemporaryDirectory() as d:
            rc, err = run(payload("collector", model="haiku"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")

    def test_c12_exception_fails_open(self):
        with fixture() as d:
            with mock.patch.object(hook, "read_tier", side_effect=RuntimeError):
                rc, err = run(payload("collector", model="haiku"), d)
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")


class Wiring(unittest.TestCase):
    """판정 입력 둘 다 실제 저장소에서 읽힌다 — 어느 쪽도 하드코딩이 아니다."""

    def test_tier_comes_from_real_definitions(self):
        self.assertEqual(hook.read_tier(REPO, "explorer"), "explore")
        self.assertEqual(hook.read_tier(REPO, "reviewer"), "design")
        self.assertIsNone(hook.read_tier(REPO, "general-purpose"))
        self.assertIsNone(hook.read_tier(REPO, "../../etc/passwd"))

    def test_lightweight_list_comes_from_real_registry(self):
        # REGISTRY.md는 미추적이라 설치처마다 다르다. 목록의 내용이 아니라
        # **판독이 성립하는지**를 본다 — 이 설치처는 절을 채워 두었다.
        names = hook.read_lightweight_models(REPO)
        self.assertTrue(names, "이 설치처의 REGISTRY.md에 「경량 모델」 절이 필요하다")
        self.assertTrue(all(n == n.lower() for n in names))

    def test_real_registry_blocks_a_listed_model(self):
        listed = sorted(hook.read_lightweight_models(REPO))[0]
        rc, err = run(payload("explorer", model=listed), REPO)
        self.assertEqual(rc, hook.BLOCK_EXIT)
        self.assertIn(listed, err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
