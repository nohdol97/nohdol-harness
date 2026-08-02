#!/usr/bin/env python3
"""harness-review-reminder 훅 회귀 테스트 — 스펙 완료 기준 C1~C14.

스펙: docs/specs/2026-07-14-harness-review-reminder-hook.md
"""
import contextlib
import datetime
import importlib.util
import io
import os
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "harness_review_reminder_hook", os.path.join(HERE, "harness-review-reminder.py")
)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

TODAY = datetime.date(2026, 7, 14)


class DaysSince(unittest.TestCase):
    def test_eight_days(self):
        self.assertEqual(hook.days_since("2026-07-06", TODAY), 8)

    def test_today_with_newline(self):
        self.assertEqual(hook.days_since("2026-07-14\n", TODAY), 0)

    def test_missing_or_garbage(self):
        self.assertIsNone(hook.days_since(None, TODAY))
        self.assertIsNone(hook.days_since("어제쯤", TODAY))
        self.assertIsNone(hook.days_since("", TODAY))

    def test_kst_offset(self):  # C9 — 경과 판정의 '오늘'은 KST(UTC+9) 기준
        self.assertEqual(hook.KST.utcoffset(None), datetime.timedelta(hours=9))
        self.assertEqual(hook.today_kst(), datetime.datetime.now(hook.KST).date())

    def test_kst_deterministic_across_date_boundary(self):
        # C9 보강 — UTC 날짜와 KST 날짜가 갈리는 고정 시각으로 검증한다.
        # now(KST) 비교만으로는 UTC 00~15시에 date.today() 회귀를 못 잡는다(감사 HOOK-F3).
        utc = datetime.timezone.utc
        self.assertEqual(
            hook.today_kst(datetime.datetime(2026, 7, 15, 16, 0, tzinfo=utc)),
            datetime.date(2026, 7, 16))  # UTC 15일 16시 = KST 16일 01시
        self.assertEqual(
            hook.today_kst(datetime.datetime(2026, 7, 15, 14, 59, tzinfo=utc)),
            datetime.date(2026, 7, 15))  # UTC 15일 14:59 = KST 15일 23:59


class DecideMode(unittest.TestCase):
    def test_weekly_overdue_wins(self):  # C1 — 전체가 일일보다 우선
        self.assertEqual(hook.decide_mode(7, 0), "full")
        self.assertEqual(hook.decide_mode(10, 5), "full")

    def test_no_weekly_record_is_full(self):  # C3
        self.assertEqual(hook.decide_mode(None, 0), "full")

    def test_daily_overdue(self):  # C2 — 주간 이내 + 일일 경과
        self.assertEqual(hook.decide_mode(3, 1), "daily")
        self.assertEqual(hook.decide_mode(3, None), "daily")

    def test_all_fresh_silent(self):  # C4
        self.assertIsNone(hook.decide_mode(3, 0))
        self.assertIsNone(hook.decide_mode(0, 0))

    def test_c11_corporate_profile_suppresses_daily(self):
        # C11 — 사내 설치처는 하네스 수정·커밋·푸시가 금지(§5·ADR 012)라
        # 일일 점검이 찾은 확장 신호를 적용할 수 없다. 탐지만 하는 회차의
        # 비용($1.95/회 실측)을 없앤다.
        self.assertIsNone(hook.decide_mode(3, 1, "사내"))
        self.assertIsNone(hook.decide_mode(3, None, "사내"))

    def test_c12_corporate_profile_keeps_weekly(self):
        # C12 — 주간은 억제하지 않는다. 무결성 점검(심볼릭 링크·Codex 어댑터
        # 드리프트)은 하네스를 고치지 않아도 사내에서 즉시 값이 있다.
        self.assertEqual(hook.decide_mode(7, 1, "사내"), "full")
        self.assertEqual(hook.decide_mode(None, None, "사내"), "full")

    def test_c13_personal_profile_unchanged(self):
        # C13 — 개인 프로필은 기존 동작 그대로.
        self.assertEqual(hook.decide_mode(3, 1, "개인"), "daily")
        self.assertEqual(hook.decide_mode(7, 1, "개인"), "full")

    def test_c14_unknown_profile_fails_open_to_daily(self):
        # C14 — 프로필 미상(REGISTRY.md 부재·절 부재·판독 실패)은 점검 유도다.
        # 억제 방향으로 fail하면 개인 설치처에서 판독이 한 번 어긋난 순간
        # 일일 점검이 영구 침묵한다(R2 실패 방향과 같은 논리).
        self.assertEqual(hook.decide_mode(3, 1, None), "daily")
        self.assertEqual(hook.decide_mode(3, 1, "미상값"), "daily")


class ReadProfile(unittest.TestCase):
    def _registry(self, tmpdir, content):
        with open(os.path.join(tmpdir, hook.REGISTRY), "w", encoding="utf-8") as f:
            f.write(content)

    def test_personal(self):
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "# REGISTRY\n\n## 설치처 프로필\n\n"
                              "- **개인** — 하네스 파일 수정·커밋·푸시 가능.\n")
            self.assertEqual(hook.read_profile(d), "개인")

    def test_corporate(self):
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "# REGISTRY\n\n## 설치처 프로필\n\n"
                              "- **사내** — 하네스 수정·푸시 금지, 개선은 대기 큐\n")
            self.assertEqual(hook.read_profile(d), "사내")

    def test_only_reads_the_profile_section(self):
        # 다른 절의 굵은 라벨을 프로필로 읽지 않는다. **프로필 절을 뒤에 둔다** —
        # 앞에 두면 파일 전체를 훑어 첫 매치를 잡는 구현도 같은 답을 내므로
        # 이 테스트가 절 한정을 전혀 고정하지 못한다(독립 검증 2026-08-03 B2:
        # 절 한정을 제거하는 변이가 36/36 통과로 살아남았다).
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "## 배포처 이관 경계\n\n- **사내** 후속 작업은 …\n\n"
                              "## 설치처 프로필\n\n- **개인** — 수정 가능.\n")
            self.assertEqual(hook.read_profile(d), "개인")

    def test_section_ends_at_the_next_heading_of_any_level(self):
        # 프로필 절이 끝난 뒤의 굵은 라벨은 프로필이 아니다. `##`만 절을 닫으면
        # `#`·`###` 뒤의 라벨을 프로필로 읽는다 — 억제 방향 위양성이라
        # 그 설치처가 아닌 값으로 일일 점검이 꺼진다(독립 검증 B3).
        # 프로필 절 자체는 라벨 없이 두어야 이 축이 실제로 발동한다 —
        # 라벨이 있으면 첫 매치에서 반환해 뒤를 아예 읽지 않는다.
        for closing in ("# 다른 문서", "### 하위 절"):
            with tempfile.TemporaryDirectory() as d:
                self._registry(d, "## 설치처 프로필\n\n아직 기록하지 않았다.\n\n"
                                  "%s\n\n- **사내** — 여기는 프로필이 아니다\n" % closing)
                self.assertIsNone(hook.read_profile(d), closing)

    def test_missing_file_and_missing_section(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(hook.read_profile(d))  # REGISTRY.md 부재
            self._registry(d, "# REGISTRY\n\n## 프로젝트 레지스트리\n\n표…\n")
            self.assertIsNone(hook.read_profile(d))  # 절 부재

    def test_label_mismatch_is_unknown(self):
        # C14의 '라벨 불일치' 갈래 — 절은 있으나 굵은 라벨 목록 형식이 아니면
        # 미상이고, 미상은 억제하지 않는다.
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "## 설치처 프로필\n\n사내 설치처입니다.\n")
            self.assertIsNone(hook.read_profile(d))
            self._registry(d, "## 설치처 프로필\n\n- 사내 — 굵은 라벨이 아님\n")
            self.assertIsNone(hook.read_profile(d))

    def test_fenced_example_is_not_the_profile(self):
        # 코드 펜스 안의 예시를 프로필로 읽으면 그 설치처가 아닌 값으로 일일이
        # 꺼진다(억제 방향 위양성 — 독립 검증 2026-08-03 F4).
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "# REGISTRY\n\n예시 형식:\n\n```markdown\n"
                              "## 설치처 프로필\n\n- **사내** — 예시일 뿐\n```\n\n"
                              "## 설치처 프로필\n\n- **개인** — 실제 값\n")
            self.assertEqual(hook.read_profile(d), "개인")

    def test_unreadable_registry(self):
        with tempfile.TemporaryDirectory() as d:
            self._registry(d, "## 설치처 프로필\n\n- **사내** — 금지\n")
            with mock.patch("builtins.open", side_effect=PermissionError):
                self.assertIsNone(hook.read_profile(d))


class BuildMessage(unittest.TestCase):
    def test_full_message(self):  # C1
        msg = hook.build_message("full", 8, 0)
        self.assertIn("전체", msg)
        self.assertIn("8일", msg)
        self.assertIn(".harness-review-last", msg)
        self.assertIn(".harness-review-daily-last", msg)  # 전체 완료 시 두 마커 갱신
        # 서브에이전트 위임 실행 — 메인 루프가 직접 점검하면 첫 응답이 점검에
        # 점유되어 사용자 요청이 밀린다(2026-07-14 사용자 확정)
        self.assertIn("첫 응답에서", msg)
        self.assertIn("서브에이전트", msg)
        self.assertIn("발행", msg)
        self.assertIn("병행", msg)  # 사용자 요청 병행 처리
        # 발행 타입 명시 — 스킬이 explorer를 명문화한 뒤에도 리마인더 경로의
        # 발행이 general-purpose로 반복 유출(2026-07-17 실측, 신호 ③)
        self.assertIn("explorer", msg)
        self.assertIn("낮은 추론 등급", msg)  # explore 티어 기본값(루트 9절 표)

    def test_full_message_no_record(self):  # C3
        self.assertIn("기록이 없습니다", hook.build_message("full", None, None))

    def test_daily_message(self):  # C2
        msg = hook.build_message("daily", 3, 1)
        self.assertIn("일일 경량", msg)
        self.assertIn(".harness-review-daily-last", msg)
        self.assertIn("첫 응답에서", msg)
        self.assertIn("서브에이전트", msg)
        self.assertIn("explorer", msg)  # 발행 타입 명시(C1과 동일 근거)
        self.assertIn("낮은 추론 등급", msg)  # explore 티어 기본값(루트 9절 표)

    def test_silent_when_fresh(self):  # C4 재개정(2026-07-16) — 기한 전엔 무출력(노이즈 제거)
        self.assertIsNone(hook.build_message(None, 3, 0))
        self.assertIsNone(hook.build_message(None, 0, 0))


def run_main_in(tmpdir):
    out = io.StringIO()
    with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": tmpdir}), \
         contextlib.redirect_stdout(out):
        rc = hook.main()
    return rc, out.getvalue()


class MainFlow(unittest.TestCase):
    def _write(self, tmpdir, relpath, content):
        os.makedirs(os.path.join(tmpdir, "_workspace"), exist_ok=True)
        with open(os.path.join(tmpdir, relpath), "w", encoding="utf-8") as f:
            f.write(content)

    def test_c1_weekly_stale_full_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            old = (hook.today_kst() - datetime.timedelta(days=8)).isoformat()
            today = hook.today_kst().isoformat()
            self._write(d, hook.WEEKLY_MARKER, old)
            self._write(d, hook.DAILY_MARKER, today)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("전체", out)

    def test_c2_daily_stale_daily_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            recent = (hook.today_kst() - datetime.timedelta(days=2)).isoformat()
            yesterday = (hook.today_kst() - datetime.timedelta(days=1)).isoformat()
            self._write(d, hook.WEEKLY_MARKER, recent)
            self._write(d, hook.DAILY_MARKER, yesterday)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("일일 경량", out)

    def test_c3_no_markers_full_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("기록이 없습니다", out)

    def test_c4_all_fresh_silent(self):  # C4 재개정(2026-07-16) — 기한 전엔 무출력
        with tempfile.TemporaryDirectory() as d:
            today = hook.today_kst().isoformat()
            self._write(d, hook.WEEKLY_MARKER, today)
            self._write(d, hook.DAILY_MARKER, today)
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def _profile(self, tmpdir, value):
        with open(os.path.join(tmpdir, hook.REGISTRY), "w", encoding="utf-8") as f:
            f.write("# REGISTRY\n\n## 설치처 프로필\n\n- **%s** — …\n" % value)

    def test_c11_main_corporate_daily_silent(self):
        with tempfile.TemporaryDirectory() as d:
            recent = (hook.today_kst() - datetime.timedelta(days=2)).isoformat()
            yesterday = (hook.today_kst() - datetime.timedelta(days=1)).isoformat()
            self._write(d, hook.WEEKLY_MARKER, recent)
            self._write(d, hook.DAILY_MARKER, yesterday)
            self._profile(d, "사내")
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")  # 억제 — 안내 줄도 남기지 않는다(2026-07-16 노이즈 결정)

    def test_c12_main_corporate_weekly_still_fires(self):
        with tempfile.TemporaryDirectory() as d:
            old = (hook.today_kst() - datetime.timedelta(days=8)).isoformat()
            self._write(d, hook.WEEKLY_MARKER, old)
            self._write(d, hook.DAILY_MARKER, hook.today_kst().isoformat())
            self._profile(d, "사내")
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("전체", out)

    def test_c14_main_no_registry_daily_fires(self):
        with tempfile.TemporaryDirectory() as d:
            recent = (hook.today_kst() - datetime.timedelta(days=2)).isoformat()
            yesterday = (hook.today_kst() - datetime.timedelta(days=1)).isoformat()
            self._write(d, hook.WEEKLY_MARKER, recent)
            self._write(d, hook.DAILY_MARKER, yesterday)
            rc, out = run_main_in(d)  # REGISTRY.md 없음
            self.assertEqual(rc, 0)
            self.assertIn("일일 경량", out)

    def test_c5_garbage_weekly_marker_full(self):
        with tempfile.TemporaryDirectory() as d:
            self._write(d, hook.WEEKLY_MARKER, "not-a-date")
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("전체", out)

    def test_c10_unreadable_marker_treated_as_no_record(self):
        # C10 — 마커가 존재하나 읽기 실패(권한 등)면 "기록 없음"으로 취급해
        # 점검을 유도해야 한다(R2 실패 방향). 예외가 main까지 새면 리마인더가
        # 영구 침묵한다(감사 HOOK-F6 — exit 0이라 발견도 안 되는 침묵 사망).
        with tempfile.TemporaryDirectory() as d:
            self._write(d, hook.WEEKLY_MARKER, "2026-07-01")
            self._write(d, hook.DAILY_MARKER, "2026-07-01")
            with mock.patch("builtins.open", side_effect=PermissionError):
                self.assertIsNone(hook.read_marker(d, hook.WEEKLY_MARKER))
                rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("기록이 없습니다", out)  # 침묵이 아니라 전체 모드 유도

    def test_c10_invalid_utf8_marker_treated_as_no_record(self):
        # C10의 인코딩 갈래 — 마커가 UTF-8이 아니면 UnicodeDecodeError가
        # main까지 새고 fail-open이 삼켜 리마인더가 통째로 침묵했다. R2가 고정한
        # 실패 방향은 침묵이 아니라 점검 유도다(독립 검증 2026-08-03 F6 재현).
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "_workspace"), exist_ok=True)
            with open(os.path.join(d, hook.WEEKLY_MARKER), "wb") as f:
                f.write(b"\xff\xfe invalid")
            self.assertIsNone(hook.days_since(
                hook.read_marker(d, hook.WEEKLY_MARKER), hook.today_kst()))
            rc, out = run_main_in(d)
            self.assertEqual(rc, 0)
            self.assertIn("기록이 없습니다", out)  # 침묵이 아니라 전체 모드 유도

    def test_c8_cp949_stdout_still_outputs(self):  # C8 — 한글 Windows 콘솔(cp949)에서 em dash
        with tempfile.TemporaryDirectory() as d:
            buf = io.BytesIO()
            cp949 = io.TextIOWrapper(buf, encoding="cp949")
            with mock.patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": d}), \
                 contextlib.redirect_stdout(cp949):
                rc = hook.main()  # 마커 부재 → 전체 모드 메시지(em dash 포함)
            cp949.flush()
            self.assertEqual(rc, 0)
            # cp949였다면 print가 예외를 던지고 fail-open이 삼켜 무출력이 됐다 —
            # UTF-8 재구성 후에는 메시지가 실제로 출력되어야 한다.
            self.assertIn("리마인더".encode("utf-8"), buf.getvalue())

    def test_c6_exception_fail_open(self):
        with mock.patch.object(hook, "build_message", side_effect=RuntimeError), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(hook.main(), 0)
            self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
