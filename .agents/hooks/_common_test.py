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
    ("worklog_reminder_hook", "worklog-reminder.py"),
    # 발행 게이트도 _common 소비자다. tier-gate는 ADR 037 때 이 목록에 들어오지
    # 않아 C3·C4(공통 사용·유실 폴백)가 검사되지 않고 있었다(독립 검증 F6).
    # 같은 계층에 있던 dispatch-gate는 ADR 045로 삭제됐다.
    ("tier_gate_hook", "tier-gate.py"),
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

    def test_c4b_fallback_profile_reader_never_reports_corporate(self):  # C4b (ADR 045)
        """`_common` 유실 시의 폴백 `read_profile`은 항상 미상을 돌려준다.

        폴백이 `사내`를 돌려주면 **개인 설치처에서 일일 하네스 점검이 영구히
        억제된다**(harness-review-reminder의 프로필 분기) — 판독 실패가 억제로
        떨어지면 안 된다는 fail-open 방향을 정면으로 어긴다. C4가 `utf8_stdio`만
        확인해 이 갈래에 커버리지가 0이었고(독립 검증 2026-08-04 C-02),
        `CORPORATE`를 돌려주는 변이가 스위트를 통과했다.

        **대상을 파일명이 아니라 `read_profile` 보유 여부로 고른다.** 파일명에
        `gate`가 든 것만 보던 동안, ADR 045가 `dispatch-gate`를 지우자 이 케이스는
        **어서션을 한 번도 실행하지 않는 상태**가 됐다 — 남은 `gate` 파일 둘
        (`tdd-gate`·`tier-gate`)이 프로필을 읽지 않아 전부 건너뛰고, 정작 유일한
        소비자인 `harness-review-reminder`는 이름에 `gate`가 없어 제외됐다(독립 검증
        2026-08-07, 규칙 축 F1·코드 축 C-01이 각각 같은 변이로 확인). 그래서 아래
        `checked` 어서션이 함께 있어야 한다 — 대상이 0이 되는 것 자체가 회귀다.
        """
        checked = 0
        for name, filename in HOOK_FILES:
            with self.subTest(hook=filename):
                hook = load_module(name + "_no_common_profile", filename,
                                   block_common=True)
                reader = getattr(hook, "read_profile", None)
                if reader is None:
                    continue  # 프로필을 읽지 않는 훅은 이 계약의 대상이 아니다
                checked += 1
                self.assertIsNone(reader("/nonexistent"))
                self.assertNotEqual(reader("/nonexistent"), hook.CORPORATE)
        self.assertGreater(checked, 0,
                           "폴백 read_profile을 가진 훅이 하나도 없다 — 이 케이스가 "
                           "조용히 무검사가 됐다는 뜻이다(HOOK_FILES를 확인할 것)")


class TestRegistryReaders(unittest.TestCase):
    """C6~C9 (R4, ADR 040) — 두 판독기가 절 파서를 공유하고 절 밖을 읽지 않는다."""

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
            self.assertEqual(common.read_profile(d), "개인")  # 서로 섞이지 않는다

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

    def test_c9b_profile_heading_accepts_a_parenthetical(self):  # C9b (ADR 042)
        """프로필 절 제목도 접두+낱말경계로 읽는다 — 정확 일치로 되돌리면 여기서 죽는다.

        ADR 042 전까지 이 절은 정확 일치였고, `## 설치처 프로필 (ADR 012)`처럼
        괄호 설명을 다는 것만으로 조용히 미상이 됐다. 그때는 미상의 대가가
        `reviewer` 하나가 다시 도는 것이었지만, 지금은 **발행 차단 전체가
        꺼지는 것**이다(독립 검증 C-04가 실측으로 재현). 그래서 경량 절과
        같은 판정으로 맞췄고, 이 케이스가 그 동작을 붙잡는다.
        """
        with self.registry("## 설치처 프로필 (ADR 012)\n\n- **사내** — x\n") as d:
            self.assertEqual(common.read_profile(d), "사내")
        with self.registry("## 설치처 프로필별 메모\n\n- **사내** — 다른 절이다\n") as d:
            self.assertIsNone(common.read_profile(d))

    def test_c9_heading_accepts_a_parenthetical(self):  # C9
        # 두 절이 이제 같은 판정을 쓴다. 경량 절은 접두 매칭이라 설명을 붙여도
        # 읽히고, 낱말 경계 덕에 다른 절을 삼키지도 않는다.
        with self.registry("## 경량 모델 (9절 경량 금지의 판정 입력)\n\n- **haiku** — x\n") as d:
            self.assertEqual(common.read_lightweight_models(d), {"haiku"})
        with self.registry("## 경량 모델링 도구\n\n- **haiku** — 다른 절이다\n") as d:
            self.assertEqual(common.read_lightweight_models(d), set())


if __name__ == "__main__":
    unittest.main(verbosity=2)
