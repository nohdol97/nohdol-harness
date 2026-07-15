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
    ("harness_review_reminder_hook", "harness-review-reminder.py"),
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
