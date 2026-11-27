#!/usr/bin/env python3
"""_common(훅 공통 부트스트랩) 회귀 테스트 — 스펙 완료 기준 C1~C4.

스펙: docs/specs/2026-07-15-hooks-common-bootstrap.md
C5(훅 3종 기존 테스트 통과)는 각 훅의 *_test.py 실행으로 판정한다.
"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# 훅들이 쓰는 정식 import 경로와 같은 인스턴스(sys.modules 캐시)를 봐야
# C3의 동일성(assertIs) 비교가 유효하다 — 파일 로드로 별도 인스턴스를 만들면
# 함수 객체가 달라져 단일 원본 여부를 판정할 수 없다.
import _common as common  # noqa: E402


def load_module(name, filename, block_common=False):
    """훅·모듈을 파일 경로로 로드한다(파일명이 하이픈 포함이라 통상 import 불가).

    block_common=True면 `_common` import를 차단해 폴백 경로(C4)를 검증한다.
    """
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    module = importlib.util.module_from_spec(spec)
    if block_common:
        # sys.modules에 None을 심으면 import가 ImportError를 던진다 — 유실 상황 재현.
        with mock.patch.dict(sys.modules, {"_common": None}):
            spec.loader.exec_module(module)
    else:
        spec.loader.exec_module(module)
    return module


HOOK_FILES = [
    # tdd-gate는 git 훅 계층(.agents/githooks/ — ADR 015)이라 교차 디렉토리 import다.
    ("tdd_gate_hook", os.path.join(os.pardir, "githooks", "tdd-gate.py")),
    ("agentsview_daemon_hook", "agentsview-daemon.py"),
    ("worklog_reminder_hook", "worklog-reminder.py"),
    # 발행 게이트도 _common 소비자다. tier-gate는 ADR 037 때 이 목록에
    # 들어오지 않아 C3·C4(공통 사용·유실 폴백)가 검사되지 않고 있었다(독립 검증 F6).
    ("tier_gate_hook", "tier-gate.py"),
    # stdin까지 재구성하게 된 뒤(C-05) 입력을 읽는 두 번째 소비자도 단일 원본을 써야 한다.
    ("gate_reminder_hook", "gate-reminder.py"),
]


class TestUtf8Stdio(unittest.TestCase):
    def test_c1_cp949_stdout_reconfigured_to_utf8(self):  # C1 (R1)
        buf = io.BytesIO()
        cp949 = io.TextIOWrapper(buf, encoding="cp949")
        with contextlib.redirect_stdout(cp949):
            common.utf8_stdio()
            print("리마인더 — em dash 포함")  # cp949였다면 U+2014에서 예외
            sys.stdout.flush()
        self.assertIn("리마인더 — em dash 포함".encode("utf-8"), buf.getvalue())

    def test_c1_cp949_stdin_reconfigured_to_utf8(self):  # C1 (R1) — 입력 방향(C-05)
        cp949 = io.TextIOWrapper(io.BytesIO("검증 — 리뷰".encode("utf-8")), encoding="cp949")
        with mock.patch("sys.stdin", cp949):
            common.utf8_stdio()
            self.assertEqual(sys.stdin.read(), "검증 — 리뷰")

    def test_c2_unreconfigurable_stream_passes(self):  # C2 (R1)
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            common.utf8_stdio()  # StringIO는 reconfigure 불가 — 예외 없이 통과해야 한다


class TestHooksUseCommon(unittest.TestCase):
    def test_c3_hooks_share_single_source(self):  # C3 (R2)
        for name, filename in HOOK_FILES:
            with self.subTest(hook=filename):
                hook = load_module(name, filename)
                self.assertIs(
                    hook.utf8_stdio, common.utf8_stdio,
                    f"{filename}이 _common.utf8_stdio가 아니라 복제본을 쓴다",
                )

    def test_c4_missing_common_falls_back_noop(self):  # C4 (R3)
        for name, filename in HOOK_FILES:
            with self.subTest(hook=filename):
                hook = load_module(name + "_no_common", filename, block_common=True)
                hook.utf8_stdio()  # 폴백 no-op — 로드·호출 모두 예외 없어야 한다
                self.assertIsNot(hook.utf8_stdio, common.utf8_stdio)

class TestRegistryReaders(unittest.TestCase):
    """C6~C9 (R4, ADR 040) — 경량 판독기는 자기 절만 읽고 절 밖을 읽지 않는다."""

    @contextlib.contextmanager
    def registry(self, body):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "REGISTRY.md"), "w", encoding="utf-8") as f:
                f.write(body)
            yield d

    def test_c6_lightweight_read_from_its_own_section(self):  # C6
        with self.registry(
            "## 설치처 프로필\n\n- **개인** — 설명\n\n"
            "## 경량 모델 (9절 판정 입력)\n\n- **haiku** — 최저가\n- **nano** — 가상\n"
        ) as d:
            self.assertEqual(common.read_lightweight_models(d), {"haiku", "nano"})

    def test_c7_absent_or_empty_section_is_empty_set(self):  # C7
        for body in ("## 설치처 프로필\n\n- **사내** — 설명\n",
                     "## 경량 모델\n\n설명만 있고 항목이 없다\n"):
            with self.registry(body) as d:
                self.assertEqual(common.read_lightweight_models(d), set())
        with self.registry("") as d:  # 파일은 있으나 빈 경우
            self.assertEqual(common.read_lightweight_models(d), set())
        self.assertEqual(common.read_lightweight_models("/nonexistent"), set())

    def test_c8_prose_outside_the_section_is_not_read(self):  # C8
        # 절 밖의 굵은 라벨과 코드 펜스 안의 예시는 판정 입력이 아니다 — 전체
        # 검색이면 다른 절의 산문이 경량 목록으로 읽힌다.
        with self.registry(
            "## 다른 절\n\n- **haiku** — 여기 있는 것은 목록이 아니다\n\n"
            "## 경량 모델\n\n```\n- **fenced** — 예시일 뿐\n```\n\n- **real** — 실제 항목\n"
        ) as d:
            self.assertEqual(common.read_lightweight_models(d), {"real"})

    def test_c9_heading_accepts_a_parenthetical(self):  # C9
        # 경량 절은 접두 매칭이라 설명을 붙여도 읽히고, 낱말 경계 덕에 다른
        # 절을 삼키지도 않는다.
        with self.registry("## 경량 모델 (9절 경량 금지의 판정 입력)\n\n- **haiku** — x\n") as d:
            self.assertEqual(common.read_lightweight_models(d), {"haiku"})
        with self.registry("## 경량 모델링 도구\n\n- **haiku** — 다른 절이다\n") as d:
            self.assertEqual(common.read_lightweight_models(d), set())



class SectionParser(unittest.TestCase):
    """공유 절 파서(`_section_items`)의 경계 — 경량 판독기로 고정한다.

    ADR 062 전까지 이 경계들은 프로필 판독기 테스트가 붙잡았다. 그 판독기가
    소비자를 잃어 지워졌으므로, 같은 파서를 쓰는 남은 소비자로 옮겼다.
    """

    def _registry(self, tmpdir, content):
        with open(os.path.join(tmpdir, common.REGISTRY), "w", encoding="utf-8") as f:
            f.write(content)

    def test_only_reads_its_own_section(self):
        # **대상 절을 뒤에 둔다** — 앞에 두면 파일 전체를 훑는 구현도 같은 답을
        # 내 절 한정을 고정하지 못한다(독립 검증 2026-08-03 B2).
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "## 배포처 이관 경계\n\n- **haiku** 후속 작업은 …\n\n"
                              "## 경량 모델\n\n- **nano** — 실제 항목\n")
            self.assertEqual(common.read_lightweight_models(d), {"nano"})

    def test_section_ends_at_the_next_heading_of_any_level(self):
        # `##`만 절을 닫으면 `#`·`###` 뒤의 라벨을 절 내용으로 읽는다(독립 검증 B3).
        for closing in ("# 다른 문서", "### 하위 절"):
            with tempfile.TemporaryDirectory() as d:
                self._registry(d, "## 경량 모델\n\n아직 기록하지 않았다.\n\n"
                                  "%s\n\n- **haiku** — 여기는 목록이 아니다\n" % closing)
                self.assertEqual(common.read_lightweight_models(d), set(), closing)

    def test_label_must_be_first_content_of_a_bullet(self):
        # 굵은 라벨이 목록 항목의 첫 내용일 때만 잡는다(독립 검증 2026-08-03 B1).
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "## 경량 모델\n\n- 모델: **haiku**\n- haiku — 굵지 않음\n")
            self.assertEqual(common.read_lightweight_models(d), set())

    def test_unreadable_registry(self):
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "## 경량 모델\n\n- **haiku** — x\n")
            with mock.patch("builtins.open", side_effect=PermissionError):
                self.assertEqual(common.read_lightweight_models(d), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
