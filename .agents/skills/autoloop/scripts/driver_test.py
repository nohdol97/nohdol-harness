#!/usr/bin/env python3
"""autoloop driver 회귀 테스트 — 스펙 docs/specs/2026-07-19-autoloop-driver.md 완료 기준(C1~C29).

실행: python3 .agents/skills/autoloop/scripts/driver_test.py
부수 효과: 임시 디렉토리만 사용하며 전부 정리한다. 실제 claude CLI를 호출하지 않는다
(fake claude 실행파일로 CLI 경계를 모킹 — R7⑦ 프로세스 실패까지 재현).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

import driver  # noqa: E402

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys
scen_path = os.environ["FAKE_SCENARIO"]
idx_path = scen_path + ".idx"
i = int(open(idx_path).read()) if os.path.exists(idx_path) else 0
with open(scen_path) as f:
    scen = json.load(f)
entry = scen[min(i, len(scen) - 1)]
open(idx_path, "w").write(str(i + 1))
rec = os.environ.get("FAKE_RECORD")
if rec:
    with open(os.path.join(rec, "call-%d.json" % i), "w") as f:
        json.dump(sys.argv[1:], f)
if entry.get("touch"):
    open(entry["touch"], "w").write("")
if entry.get("exit", 0) != 0:
    sys.exit(entry["exit"])
print(json.dumps({"result": entry.get("text", ""), "total_cost_usd": entry.get("cost", 0.01), "is_error": False}))
'''

FAKE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys
argv = sys.argv[1:]
scen_path = os.environ["FAKE_CODEX_SCENARIO"]
idx_path = scen_path + ".idx"
i = int(open(idx_path).read()) if os.path.exists(idx_path) else 0
with open(scen_path) as f:
    scen = json.load(f)
entry = scen[min(i, len(scen) - 1)]
open(idx_path, "w").write(str(i + 1))
rec = os.environ.get("FAKE_RECORD")
if rec:
    with open(os.path.join(rec, "codex-call-%d.json" % i), "w") as f:
        json.dump(argv, f)
# Codex는 --output-format json이 아니라 -o <file>로 최종 메시지를 쓴다
if "-o" in argv:
    open(argv[argv.index("-o") + 1], "w").write(entry.get("text", ""))
if entry.get("exit", 0) != 0:
    sys.exit(entry["exit"])
'''


def status_text(status, open_items, note="progress"):
    """세션 최종 출력 형태의 상태 블록 텍스트를 만든다."""
    block = json.dumps({"status": status, "open_items": open_items, "note": note})
    return "some work narrative...\n```json\n" + block + "\n```\n"


def verdict_text(verdict, reason="ok"):
    block = json.dumps({"verdict": verdict, "reason": reason})
    return "review narrative...\n```json\n" + block + "\n```\n"


class DriverTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="autoloop-test-")
        self.workdir = os.path.join(self.tmp, "work")
        self.fake = os.path.join(self.tmp, "fake_claude.py")
        with open(self.fake, "w") as f:
            f.write(FAKE_CLAUDE)
        self.fake_codex = os.path.join(self.tmp, "fake_codex.py")
        with open(self.fake_codex, "w") as f:
            f.write(FAKE_CODEX)
        self.codex_scenario_path = os.path.join(self.tmp, "codex_scenario.json")
        self.spec = os.path.join(self.tmp, "spec.md")
        with open(self.spec, "w") as f:
            f.write("# 스펙: 테스트 대상\n\n## 완료 기준\n- [ ] C1: something\n")
        self.scenario_path = os.path.join(self.tmp, "scenario.json")
        self.record_dir = os.path.join(self.tmp, "record")
        os.makedirs(self.record_dir)
        os.environ["FAKE_SCENARIO"] = self.scenario_path
        os.environ["FAKE_RECORD"] = self.record_dir

    def tearDown(self):
        os.environ.pop("FAKE_SCENARIO", None)
        os.environ.pop("FAKE_CODEX_SCENARIO", None)
        os.environ.pop("FAKE_RECORD", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_scenario(self, entries):
        with open(self.scenario_path, "w") as f:
            json.dump(entries, f)
        idx = self.scenario_path + ".idx"
        if os.path.exists(idx):
            os.remove(idx)

    def write_codex_scenario(self, entries):
        os.environ["FAKE_CODEX_SCENARIO"] = self.codex_scenario_path
        with open(self.codex_scenario_path, "w") as f:
            json.dump(entries, f)
        idx = self.codex_scenario_path + ".idx"
        if os.path.exists(idx):
            os.remove(idx)

    def make_config(self, **kw):
        defaults = dict(
            spec=self.spec,
            project=self.tmp,
            test_cmd="",
            max_iterations=10,
            stall_limit=3,
            max_cost_usd=0.0,
            work_name="test-work",
            workspace=self.workdir,
            claude_cmd=[sys.executable, self.fake],
            codex_cmd=[sys.executable, self.fake_codex],
            cwd=self.tmp,
        )
        defaults.update(kw)
        return driver.Config(**defaults)

    def recorded_prompt(self, call_index):
        with open(os.path.join(self.record_dir, "call-%d.json" % call_index)) as f:
            argv = json.load(f)
        return argv[argv.index("-p") + 1]


class TestC1StatusParsing(DriverTestBase):
    def test_last_valid_block_wins(self):
        text = status_text("continue", 5) + "more...\n" + status_text("done", 0)
        st = driver.parse_status_block(text)
        self.assertEqual(st["status"], "done")
        self.assertEqual(st["open_items"], 0)

    def test_invalid_falls_back_to_continue(self):
        for text in ["no block at all", "```json\n{broken\n```", '```json\n{"foo": 1}\n```']:
            st = driver.parse_status_block(text)
            self.assertEqual(st["status"], "continue", "폴백 실패: %r" % text)
            self.assertIsNone(st["open_items"])
            self.assertFalse(st["parsed"])


class TestC2Stall(DriverTestBase):
    def test_no_progress_stalls(self):
        self.write_scenario([{"text": status_text("continue", 2)}] * 10)
        cfg = self.make_config(stall_limit=2)
        self.assertEqual(driver.Driver(cfg).run(), "stalled")

    def test_progress_resets_counter(self):
        opens = [3, 2, 2, 1, 1, 1]
        self.write_scenario([{"text": status_text("continue", n)} for n in opens])
        cfg = self.make_config(stall_limit=3, max_iterations=6)
        # 리셋이 없다면 6번째에서 stalled — 리셋 덕에 exhausted 로 끝나야 한다
        self.assertEqual(driver.Driver(cfg).run(), "exhausted")

    def test_null_open_items_counts_as_no_progress(self):
        # M2 회귀: open_items 미보고(null)가 반복돼도 정체 게이트가 발동해야 한다
        self.write_scenario([{"text": status_text("continue", None)}] * 10)
        cfg = self.make_config(stall_limit=2)
        self.assertEqual(driver.Driver(cfg).run(), "stalled")

    def test_consecutive_parse_failures_stall(self):
        # L1 회귀(R4): 상태 블록 파싱 실패가 연속 2회면 정체로 종료한다
        self.write_scenario([{"text": "no status block here"}] * 5)
        cfg = self.make_config(stall_limit=99, max_iterations=5)
        self.assertEqual(driver.Driver(cfg).run(), "stalled")


class TestC3StopAndExhaust(DriverTestBase):
    def test_max_iterations_exhausts(self):
        self.write_scenario([{"text": status_text("continue", 1)}] * 3)
        cfg = self.make_config(max_iterations=2, stall_limit=99)
        self.assertEqual(driver.Driver(cfg).run(), "exhausted")

    def test_stop_file_stops_at_boundary(self):
        stop = os.path.join(self.workdir, "STOP")
        self.write_scenario([{"text": status_text("continue", 3), "touch": stop}] * 5)
        cfg = self.make_config(max_iterations=5)
        self.assertEqual(driver.Driver(cfg).run(), "stopped")
        # 1반복만 돌고 2반복은 진입하지 않았다
        self.assertTrue(os.path.exists(os.path.join(self.workdir, "iters", "iter-1.json")))
        self.assertFalse(os.path.exists(os.path.join(self.workdir, "iters", "iter-2.json")))
        # STOP 파일은 드라이버가 지우지 않는다 (R8)
        self.assertTrue(os.path.exists(stop))


class TestC4PromptAnchor(DriverTestBase):
    def test_prompt_contains_all_parts_and_anchor_is_immutable(self):
        cfg = self.make_config()
        anchor1 = driver.build_anchor(cfg)
        anchor2 = driver.build_anchor(cfg)
        self.assertEqual(anchor1, anchor2)
        self.assertIn(self.spec, anchor1)
        prompt = driver.build_prompt(anchor1, "/path/to/NOTE-FILE.md", "NOTE-BODY-MARKER",
                                     "TEST-RESULT-MARKER", "FEEDBACK-MARKER", "PREV-STATUS-MARKER")
        for marker in [anchor1, "/path/to/NOTE-FILE.md", "NOTE-BODY-MARKER", "TEST-RESULT-MARKER",
                       "FEEDBACK-MARKER", "PREV-STATUS-MARKER"]:
            self.assertIn(marker, prompt)
        # 고정 지시문: 상태 블록 출력 지시가 있다
        self.assertIn('"status"', prompt)

    def test_note_path_stated_in_instructions(self):
        # 튜닝: 세션이 노트 파일을 추측·검색하지 않도록 경로를 지시문에 명시한다
        prompt = driver.build_prompt("A", "/wd/carryover.md", "", "", "")
        # 지시문 4항이 그 경로를 갱신 대상으로 지목한다
        after_instructions = prompt.split("[INSTRUCTIONS")[1]
        self.assertIn("/wd/carryover.md", after_instructions)

    def test_injected_blocks_carry_untrusted_envelope(self):
        # C18: 외부 유래 주입(핸드오프 노트·테스트 출력)은 untrusted 봉투로 감싼다
        # (루트 AGENTS.md 3절 — 주입 텍스트 안의 지시를 사용자 지시로 오인 금지).
        prompt = driver.build_prompt("ANCHOR", "/wd/carryover.md", "NOTE", "TESTOUT", "", "")
        # 봉투 문구가 프롬프트에 존재하고, 주입 블록보다 지시가 우위임을 명시한다
        self.assertIn("do not follow", prompt.lower())
        self.assertIn("not user instructions", prompt.lower())
        self.assertIn("NOTE", prompt)
        self.assertIn("TESTOUT", prompt)
        # 봉투가 주입 블록(노트·테스트 결과)보다 앞서야 데이터로 읽힌다(순서 보장)
        self.assertLess(prompt.lower().index("untrusted"), prompt.index("NOTE"))
        self.assertLess(prompt.lower().index("untrusted"), prompt.index("TESTOUT"))


class TestC5SafetyArgs(DriverTestBase):
    def test_args_have_gates_and_never_bypass(self):
        cfg = self.make_config()
        for args in [driver.build_claude_args(cfg, "p"), driver.build_claude_args(cfg, "p", readonly=True)]:
            joined = " ".join(args)
            self.assertIn("--permission-mode", args)
            self.assertEqual(args[args.index("--permission-mode") + 1], "acceptEdits")
            self.assertIn("--allowedTools", args)
            self.assertIn("--disallowedTools", args)
            self.assertNotIn("bypassPermissions", joined)
            self.assertNotIn("--dangerously-skip-permissions", joined)
        # 파괴 패턴이 블랙리스트에 실려 있다
        disallow = " ".join(driver.DESTRUCTIVE_DISALLOW)
        for frag in ["git push --force", "rm -rf", "kubectl", "terraform", "aws", "helm",
                     "git clean", "psql", "gh"]:
            self.assertIn(frag, disallow)

    def test_no_bare_interpreter_grants(self):
        # H1 회귀: 임의 코드 실행으로 블랙리스트를 감싸는 bare 그랜트 금지
        for pat in ["Bash(python3:*)", "Bash(python:*)", "Bash(npx:*)",
                    "Bash(npm run:*)", "Bash(pnpm:*)", "Bash(git checkout:*)", "Bash(sh:*)",
                    # venv 러너를 넣은 뒤 생긴 변이면: 경로만 바꾼 bare 인터프리터
                    "Bash(.venv/bin/python:*)", "Bash(.venv/bin/python3:*)"]:
            self.assertNotIn(pat, driver.SAFE_ALLOW)
            self.assertNotIn(pat, driver.READONLY_ALLOW)

    def test_user_settings_are_not_inherited(self):
        # 설치처 사용자 설정을 상속하면 게이트가 두 방향으로 무너진다(실측 확인된 회귀):
        # 전역 permissions.allow 병합으로 bare 인터프리터 그랜트가 되살아나고,
        # Bash 명령을 재작성하는 PreToolUse 훅이 있으면 allow/disallow 양쪽이 빗나간다.
        cfg = self.make_config()
        for args in [driver.build_claude_args(cfg, "p"), driver.build_claude_args(cfg, "p", readonly=True)]:
            self.assertIn("--setting-sources", args)
            sources = args[args.index("--setting-sources") + 1].split(",")
            self.assertNotIn("user", sources)
            # project 는 남겨야 한다 — 빼면 하네스 항상-온이 로드되지 않는다(§12)
            self.assertIn("project", sources)

    def test_role_tier_model_routing(self):
        # 기능별 티어(§9): 검증(readonly)=design 티어 모델, 구현=implement 티어 모델.
        # 드라이버 코드엔 모델명이 없다 — 값은 기동 세션이 라인업에서 골라 넘긴다.
        cfg = self.make_config(implement_model="impl-tier-model", verify_model="design-tier-model")
        work = driver.build_claude_args(cfg, "p")
        verify = driver.build_claude_args(cfg, "p", readonly=True)
        self.assertEqual(work[work.index("--model") + 1], "impl-tier-model")
        self.assertEqual(verify[verify.index("--model") + 1], "design-tier-model")

    def test_role_model_falls_back_to_uniform_then_inherit(self):
        # 역할별 미지정 → 균일 --model, 그것도 없으면 --model 아예 미출력(세션 기본 상속)
        cfg = self.make_config(model="uniform-model")
        self.assertEqual(driver.resolve_model(cfg), "uniform-model")
        self.assertEqual(driver.resolve_model(cfg, readonly=True), "uniform-model")
        bare = self.make_config()
        self.assertEqual(driver.resolve_model(bare), "")
        self.assertNotIn("--model", driver.build_claude_args(bare, "p"))
        # 하드코딩된 모델명이 소스에 없다(§9 탈모델명)
        import inspect
        src = inspect.getsource(driver.build_claude_args) + inspect.getsource(driver.resolve_model)
        for name in ["opus", "sonnet", "haiku", "claude-"]:
            self.assertNotIn(name, src.lower())

    def test_allow_extra_is_explicit_and_not_readonly(self):
        # 사용자 명시 확장은 작업 세션에만 실리고, 검증 세션(readonly)에는 안 실린다
        cfg = self.make_config(allow_extra=["Bash(make test:*)"])
        self.assertIn("Bash(make test:*)", driver.build_claude_args(cfg, "p"))
        self.assertNotIn("Bash(make test:*)", driver.build_claude_args(cfg, "p", readonly=True))
        # 기본값은 빈 확장
        self.assertNotIn("Bash(make test:*)", driver.build_claude_args(self.make_config(), "p"))


class TestC6Blocked(DriverTestBase):
    def test_blocked_halts_and_records(self):
        self.write_scenario([{"text": status_text("blocked", 3, note="need kubectl apply approval")}])
        cfg = self.make_config()
        self.assertEqual(driver.Driver(cfg).run(), "blocked")
        with open(os.path.join(self.workdir, "carryover.md")) as f:
            note = f.read()
        self.assertIn("사용자 확인 필요", note)
        self.assertIn("need kubectl apply approval", note)


class TestC7IndependentTest(DriverTestBase):
    def test_red_test_beats_done_claim(self):
        self.write_scenario([{"text": status_text("done", 0)}] * 2)
        cfg = self.make_config(test_cmd="%s -c 'import sys; sys.exit(1)'" % sys.executable, max_iterations=1)
        result = driver.Driver(cfg).run()
        self.assertNotEqual(result, "done")  # green 주장 + red 실측 → done 불인정
        with open(os.path.join(self.workdir, "iters", "iter-1.json")) as f:
            rec = json.load(f)
        self.assertEqual(rec["test"]["outcome"], "red")

    def test_green_recorded(self):
        self.write_scenario([{"text": status_text("continue", 1)}])
        cfg = self.make_config(test_cmd="%s -c 'import sys; sys.exit(0)'" % sys.executable, max_iterations=1)
        driver.Driver(cfg).run()
        with open(os.path.join(self.workdir, "iters", "iter-1.json")) as f:
            rec = json.load(f)
        self.assertEqual(rec["test"]["outcome"], "green")


class TestC8VerifyGate(DriverTestBase):
    def test_block_feeds_back_then_pass_completes(self):
        self.write_scenario([
            {"text": status_text("done", 0)},
            {"text": verdict_text("BLOCK", reason="MISSING-EDGE-CASE-X")},
            {"text": status_text("done", 0)},
            {"text": verdict_text("PASS")},
        ])
        cfg = self.make_config(test_cmd="%s -c 'import sys; sys.exit(0)'" % sys.executable, max_iterations=5)
        self.assertEqual(driver.Driver(cfg).run(), "done")
        # BLOCK 사유가 다음 반복 프롬프트(call-2)에 실렸다
        self.assertIn("MISSING-EDGE-CASE-X", self.recorded_prompt(2))


class TestC9Preflight(DriverTestBase):
    def test_missing_spec_refused(self):
        cfg = self.make_config(spec=os.path.join(self.tmp, "no-such.md"))
        ok, reason = driver.startup_guard(cfg)
        self.assertFalse(ok)

    def test_spec_without_criteria_refused(self):
        bad = os.path.join(self.tmp, "bad-spec.md")
        with open(bad, "w") as f:
            f.write("# 스펙\n\n목표만 있음\n")
        ok, reason = driver.startup_guard(self.make_config(spec=bad))
        self.assertFalse(ok)
        self.assertIn("완료 기준", reason)

    def test_good_spec_passes(self):
        ok, _ = driver.startup_guard(self.make_config())
        self.assertTrue(ok)


class TestC10Resume(DriverTestBase):
    def test_note_carried_on_restart(self):
        self.write_scenario([{"text": status_text("continue", 2)}])
        cfg = self.make_config(max_iterations=1)
        self.assertEqual(driver.Driver(cfg).run(), "exhausted")
        # 재기동 — 기존 노트가 프롬프트에 실린다
        self.write_scenario([{"text": status_text("continue", 1)}])
        driver.Driver(self.make_config(max_iterations=1)).run()
        self.assertIn("Autoloop Carryover", self.recorded_prompt(0))

    def test_stop_file_refuses_startup(self):
        os.makedirs(self.workdir, exist_ok=True)
        with open(os.path.join(self.workdir, "STOP"), "w") as f:
            f.write("")
        ok, reason = driver.startup_guard(self.make_config())
        self.assertFalse(ok)
        self.assertIn("STOP", reason)


class TestHandoffFloor(DriverTestBase):
    """튜닝: 세션이 노트 파일을 안 채워도 드라이버가 직전 상태를 다음 프롬프트에 보장 주입."""

    def test_prev_status_injected_even_if_note_empty(self):
        # 두 반복 모두 노트 파일에 아무것도 쓰지 않는(touch 없는) 세션
        self.write_scenario([
            {"text": status_text("continue", 2, note="did step A")},
            {"text": status_text("continue", 1, note="did step B")},
        ])
        cfg = self.make_config(max_iterations=2, stall_limit=99)
        driver.Driver(cfg).run()
        # 2번째 반복(call-1) 프롬프트에 드라이버 기록 플로어와 직전 note가 실렸다
        second = self.recorded_prompt(1)
        self.assertIn("LAST STATUS (driver record", second)
        self.assertIn("did step A", second)


class TestC16EngineRouting(DriverTestBase):
    def test_role_engine_routing(self):
        # 구현=claude, 검증=codex 역할 라우팅(R13)
        cfg = self.make_config(implement_engine="claude", verify_engine="codex")
        self.assertEqual(driver.resolve_engine(cfg), "claude")
        self.assertEqual(driver.resolve_engine(cfg, readonly=True), "codex")

    def test_engine_default_and_fallback(self):
        self.assertEqual(driver.resolve_engine(self.make_config()), "claude")
        cfg = self.make_config(engine="codex")            # 균일 기본
        self.assertEqual(driver.resolve_engine(cfg), "codex")
        self.assertEqual(driver.resolve_engine(cfg, readonly=True), "codex")


class TestC17CodexSafety(DriverTestBase):
    def test_codex_edit_session_flags(self):
        cfg = self.make_config(project="/proj")
        out = "/wd/.codex-out.txt"
        args = driver.build_codex_args(cfg, "PROMPT", False, out)
        self.assertEqual(args[0], "exec")
        self.assertIn("--sandbox", args)
        self.assertEqual(args[args.index("--sandbox") + 1], "workspace-write")
        self.assertIn("--skip-git-repo-check", args)
        self.assertEqual(args[args.index("-C") + 1], "/proj")
        self.assertEqual(args[args.index("-o") + 1], out)
        self.assertIn("PROMPT", args)

    def test_codex_verify_session_is_read_only(self):
        cfg = self.make_config()
        args = driver.build_codex_args(cfg, "P", True, "/wd/o.txt")
        self.assertEqual(args[args.index("--sandbox") + 1], "read-only")

    def test_codex_model_flag(self):
        cfg = self.make_config(implement_model="impl-m", verify_model="ver-m")
        work = driver.build_codex_args(cfg, "P", False, "/o")
        verify = driver.build_codex_args(cfg, "P", True, "/o")
        self.assertEqual(work[work.index("-m") + 1], "impl-m")
        self.assertEqual(verify[verify.index("-m") + 1], "ver-m")

    def test_no_bypass_in_either_engine(self):
        cfg = self.make_config()
        codex = " ".join(driver.build_codex_args(cfg, "P", False, "/o")
                         + driver.build_codex_args(cfg, "P", True, "/o"))
        claude = " ".join(driver.build_claude_args(cfg, "P")
                          + driver.build_claude_args(cfg, "P", readonly=True))
        for bad in ["--dangerously-bypass-approvals-and-sandbox", "danger-full-access",
                    "--dangerously-skip-permissions", "bypassPermissions"]:
            self.assertNotIn(bad, codex)
            self.assertNotIn(bad, claude)

    def test_codex_engine_run_parses_output_file(self):
        # 순수 codex 엔진 1반복 — -o 파일에서 상태 블록 파싱, 완주
        self.write_scenario([])  # claude 미사용
        self.write_codex_scenario([{"text": status_text("continue", 1)}])
        cfg = self.make_config(engine="codex", max_iterations=1)
        self.assertEqual(driver.Driver(cfg).run(), "exhausted")
        with open(os.path.join(self.workdir, "iters", "iter-1.json")) as f:
            rec = json.load(f)
        self.assertEqual(rec["status"]["status"], "continue")


class TestC11ProcessFailure(DriverTestBase):
    def test_two_consecutive_failures_error(self):
        self.write_scenario([{"exit": 1}, {"exit": 1}])
        cfg = self.make_config()
        self.assertEqual(driver.Driver(cfg).run(), "error")

    def test_single_failure_recovers(self):
        self.write_scenario([{"exit": 1}, {"text": status_text("continue", 1)}, {"text": status_text("continue", 1)}])
        cfg = self.make_config(max_iterations=2, stall_limit=99)
        self.assertEqual(driver.Driver(cfg).run(), "exhausted")


class TestC12Artifacts(DriverTestBase):
    def test_artifacts_created(self):
        self.write_scenario([{"text": status_text("continue", 1)}])
        cfg = self.make_config(max_iterations=1)
        driver.Driver(cfg).run()
        self.assertTrue(os.path.exists(os.path.join(self.workdir, "carryover.md")))
        self.assertTrue(os.path.exists(os.path.join(self.workdir, "iters", "iter-1.json")))
        with open(os.path.join(self.workdir, "driver.log")) as f:
            log = f.read()
        self.assertIn("EXIT", log)
        self.assertIn("exhausted", log)


class TestCostCeiling(DriverTestBase):
    """R7⑥ 비용 상한 (스펙 C 목록 외 보강 테스트)."""

    def test_cost_ceiling_stops(self):
        self.write_scenario([{"text": status_text("continue", 5), "cost": 0.6}] * 5)
        cfg = self.make_config(max_cost_usd=1.0, stall_limit=99)
        self.assertEqual(driver.Driver(cfg).run(), "cost")


class TestC21Checkpoint(DriverTestBase):
    """R16 — 재기동이 게이트를 초기화하지 않는다."""

    def test_state_file_records_execution_position(self):
        self.write_scenario([{"text": status_text("continue", 2), "cost": 0.05}])
        cfg = self.make_config(max_iterations=1)
        self.assertEqual(driver.Driver(cfg).run(), "exhausted")
        with open(os.path.join(self.workdir, "state.json")) as f:
            st = json.load(f)
        self.assertEqual(st["runs"], 1)
        self.assertEqual(st["total_iterations"], 1)
        self.assertAlmostEqual(st["total_cost_usd"], 0.05)
        self.assertTrue(st["seen_valid"])
        self.assertEqual(st["prev_open"], 2)
        self.assertIn("open_items=2", st["prev_status"])
        self.assertEqual(st["last_exit_reason"], "exhausted")

    def test_stall_counter_survives_restart(self):
        # 런1: 첫 반복만 진전(seen_valid) → 2번째 반복은 무진전이라 stall=1 로 끝난다
        self.write_scenario([{"text": status_text("continue", 2)}] * 2)
        self.assertEqual(driver.Driver(self.make_config(max_iterations=2, stall_limit=2)).run(),
                         "exhausted")
        # 런2: 체크포인트가 없으면 첫 반복이 공짜 진전이 되어 정체 게이트가 영구 우회된다
        self.write_scenario([{"text": status_text("continue", 2)}])
        self.assertEqual(driver.Driver(self.make_config(max_iterations=1, stall_limit=2)).run(),
                         "stalled")

    def test_reviewer_feedback_and_last_status_survive_restart(self):
        self.write_scenario([
            {"text": status_text("done", 0, note="claimed complete")},
            {"text": verdict_text("BLOCK", "criterion C1 has no live assertion")},
        ])
        self.assertEqual(driver.Driver(self.make_config(max_iterations=1)).run(), "exhausted")
        self.write_scenario([{"text": status_text("continue", 1)}])
        driver.Driver(self.make_config(max_iterations=1)).run()
        first = self.recorded_prompt(0)
        self.assertIn("REVIEWER FEEDBACK", first)
        self.assertIn("criterion C1 has no live assertion", first)
        self.assertIn("open_items=0", first)      # 핸드오프 플로어도 함께 이어진다

    def test_feedback_survives_a_session_process_failure(self):
        # 세션이 뜨지도 못한 반복은 피드백 '소비'가 아니다 — 지우면 다음 반복이 왜 막혔는지
        # 모른 채 같은 done 주장을 반복해 design 티어 검증 세션을 한 번 더 태운다.
        self.write_scenario([
            {"text": status_text("done", 0)},                        # iter1 구현
            {"text": verdict_text("BLOCK", "MARKER-REASON")},        # iter1 검증 → 피드백 설정
            {"exit": 1},                                             # iter2 프로세스 실패
            {"text": status_text("continue", 1)},                    # iter3
        ])
        driver.Driver(self.make_config(max_iterations=3, stall_limit=99)).run()
        self.assertIn("MARKER-REASON", self.recorded_prompt(3))

    def test_iter_records_are_not_overwritten_by_a_restart(self):
        # 파일명이 런당 n 이면 재기동이 직전 런의 iter-1.json 을 덮어 감사 기록이 사라진다.
        self.write_scenario([{"text": status_text("continue", 5)}])
        driver.Driver(self.make_config(max_iterations=1)).run()
        self.write_scenario([{"text": status_text("continue", 4)}])
        driver.Driver(self.make_config(max_iterations=1)).run()
        self.assertEqual(sorted(os.listdir(os.path.join(self.workdir, "iters"))),
                         ["iter-1.json", "iter-2.json"])


class TestC22CumulativeBudget(DriverTestBase):
    """R16 — 비용 상한은 작업 누적, 반복 상한은 런당."""

    def test_cost_accumulates_across_restarts(self):
        self.write_scenario([{"text": status_text("continue", 5), "cost": 0.6}])
        self.assertEqual(
            driver.Driver(self.make_config(max_iterations=1, max_cost_usd=1.0, stall_limit=99)).run(),
            "exhausted")                                  # 0.6 — 상한 미만
        self.write_scenario([{"text": status_text("continue", 4), "cost": 0.6}])
        self.assertEqual(
            driver.Driver(self.make_config(max_iterations=1, max_cost_usd=1.0, stall_limit=99)).run(),
            "cost")                                       # 누적 1.2 — 재기동이 예산을 되살리지 않는다

    def test_startup_over_budget_exits_without_iterating(self):
        self.write_scenario([{"text": status_text("continue", 5), "cost": 1.5}])
        self.assertEqual(
            driver.Driver(self.make_config(max_iterations=1, max_cost_usd=1.0, stall_limit=99)).run(),
            "cost")
        self.write_scenario([{"text": status_text("continue", 4), "cost": 0.1}])
        self.assertEqual(
            driver.Driver(self.make_config(max_iterations=5, max_cost_usd=1.0, stall_limit=99)).run(),
            "cost")
        with open(os.path.join(self.workdir, "state.json")) as f:
            st = json.load(f)
        self.assertEqual(st["total_iterations"], 1)        # 두 번째 런은 반복을 돌리지 않았다

    def test_iteration_cap_stays_per_run(self):
        for _ in range(2):
            self.write_scenario([{"text": status_text("continue", 2)}] * 4)
            self.assertEqual(
                driver.Driver(self.make_config(max_iterations=2, stall_limit=99)).run(), "exhausted")
        with open(os.path.join(self.workdir, "state.json")) as f:
            st = json.load(f)
        self.assertEqual(st["runs"], 2)
        self.assertEqual(st["total_iterations"], 4)        # 누적은 기록만, 상한은 런당 2회


class TestC23StateIntegrity(DriverTestBase):
    """R16 — 읽을 수 없는 체크포인트는 fail-open 하지 않는다."""

    def test_unparseable_state_refuses_startup(self):
        os.makedirs(self.workdir, exist_ok=True)
        with open(os.path.join(self.workdir, "state.json"), "w") as f:
            f.write("{not json")
        ok, reason = driver.startup_guard(self.make_config())
        self.assertFalse(ok)
        self.assertIn("state.json", reason)

    def test_missing_state_is_a_normal_first_launch(self):
        ok, reason = driver.startup_guard(self.make_config())
        self.assertTrue(ok, reason)

    def test_state_write_goes_through_a_temp_file(self):
        # 원자성은 R16이 손상 state 를 fail-closed 로 두는 근거다 — 직접 쓰기로 바꾸면 부분
        # 기록이 정상 경로가 되고, 그러면 기동 거부가 결함을 막는 게이트가 아니라 멀쩡한
        # 재개를 막는 장치로 바뀐다. os.replace 를 막아 대상 파일이 안 생기는지로 검사한다.
        cfg = self.make_config()
        os.makedirs(self.workdir, exist_ok=True)
        target = os.path.join(self.workdir, "state.json")
        calls, original = [], driver.os.replace

        def spy(src, dst):
            calls.append((src, dst))
            raise OSError("replace blocked for this test")

        driver.os.replace = spy
        try:
            with self.assertRaises(OSError):
                driver.save_state(cfg, dict(driver.STATE_DEFAULTS))
        finally:
            driver.os.replace = original
        self.assertEqual([c[1] for c in calls], [target])
        self.assertTrue(calls[0][0].endswith(".tmp"), "임시 파일을 경유하지 않았다: %s" % calls[0][0])
        self.assertFalse(os.path.exists(target), "대상 파일에 직접 쓰고 있다 — 원자적이 아니다")

    def test_write_leaves_no_partial_file(self):
        self.write_scenario([{"text": status_text("continue", 2)}])
        driver.Driver(self.make_config(max_iterations=1)).run()
        self.assertFalse(os.path.exists(os.path.join(self.workdir, "state.json.tmp")))
        with open(os.path.join(self.workdir, "state.json")) as f:
            json.load(f)


BROKEN_RUNNER = "autoloop-no-such-runner-xyz"


class TestC24TestRunnerError(DriverTestBase):
    """R5-1·R7⑦ — 러너 고장은 '깨진 테스트'가 아니다."""

    def test_unrunnable_command_is_error_not_red(self):
        self.write_scenario([{"text": status_text("continue", 2)}] * 3)
        cfg = self.make_config(test_cmd=BROKEN_RUNNER, max_iterations=3, stall_limit=99)
        self.assertEqual(driver.Driver(cfg).run(), "error")      # 연속 2회 → R7⑦
        with open(os.path.join(self.workdir, "iters", "iter-1.json")) as f:
            self.assertEqual(json.load(f)["test"]["outcome"], "error")
        second = self.recorded_prompt(1)
        self.assertIn("TEST RUNNER ERROR", second)
        self.assertIn("Do NOT edit", second)                     # 제품 코드를 쫓지 말라는 라벨
        with open(os.path.join(self.workdir, "carryover.md")) as f:
            note = f.read()
        self.assertIn("사용자 확인 필요", note)
        self.assertIn("test-runner-error", note)
        self.assertIn(BROKEN_RUNNER, note)                       # 어떤 명령이 문제인지

    def test_error_outcome_never_confirms_done(self):
        self.write_scenario([{"text": status_text("done", 0)}] * 3)
        cfg = self.make_config(test_cmd=BROKEN_RUNNER, max_iterations=3, stall_limit=99)
        self.assertEqual(driver.Driver(cfg).run(), "error")
        calls = sorted(f for f in os.listdir(self.record_dir) if f.startswith("call-"))
        self.assertEqual(calls, ["call-0.json", "call-1.json"])  # 검증 세션이 돌지 않았다

    def test_error_to_green_counts_as_progress(self):
        marker = os.path.join(self.tmp, "runner-fixed")
        self.write_scenario([
            {"text": status_text("continue", 2)},
            {"text": status_text("continue", 2), "touch": marker},
            {"text": status_text("continue", 2)},
        ])
        cfg = self.make_config(test_cmd="test -f %s || %s" % (marker, BROKEN_RUNNER),
                               max_iterations=3, stall_limit=2)
        # error→green 전환을 진전으로 인정하지 않으면 3번째 반복에서 stalled 가 된다
        self.assertEqual(driver.Driver(cfg).run(), "exhausted")


class TestC25TestRatchet(DriverTestBase):
    """R17 — 실패하는 단정을 지워 green을 만드는 회피를 양쪽 프롬프트에서 막는다."""

    def test_iteration_prompt_forbids_weakening_tests(self):
        prompt = driver.build_prompt(driver.build_anchor(self.make_config()),
                                     "/tmp/note.md", "note body", "", "")
        self.assertIn("TEST RATCHET", prompt)
        for phrase in ["delete", "skip", "weaken", "blocked"]:
            self.assertIn(phrase, prompt.lower(), "래칫 금지 문구 누락: %s" % phrase)

    def test_verify_prompt_requires_live_assertion_per_criterion(self):
        verify = driver.build_verify_prompt(self.make_config())
        self.assertIn("TEST RATCHET CHECK", verify)
        self.assertIn("BLOCK", verify)
        for phrase in ["assertion", "skipped", "commented out"]:
            self.assertIn(phrase, verify.lower(), "래칫 판정 문구 누락: %s" % phrase)


class TestTestCmdPreflight(DriverTestBase):
    """R9 계열 — 실행조차 못 하는 `--test-cmd` 로는 기동하지 않는다(실측 2026-08-02).

    `.venv` 는 gitignore 되어 새 worktree(R18)에 구조적으로 없다. 그런 명령으로 기동한 런은
    매 반복 test=error 를 기록하며 검증 불가능한 반복에 예산을 태웠다($15/반복). 기동자가
    사용자와 명령을 합의하는 것으로는 잡히지 않는다 — 한 번 실행해 봐야 드러난다."""

    def test_launch_without_test_cmd_is_unchanged(self):
        # --test-cmd 없는 루프는 이전과 똑같이 기동한다(증거 약화 모드 경고만 — R9)
        self.assertEqual(driver.test_cmd_guard(self.make_config()), "")
        ok, reason = driver.startup_guard(self.make_config())
        self.assertTrue(ok, reason)

    def test_unrunnable_command_is_refused_with_the_reason(self):
        cfg = self.make_config(test_cmd=BROKEN_RUNNER)
        ok, reason = driver.startup_guard(cfg)
        self.assertFalse(ok, "실행할 수 없는 --test-cmd 인데 기동이 허용됐다")
        self.assertIn(BROKEN_RUNNER, reason)          # 어떤 명령인지
        self.assertIn("실행조차", reason)              # 무슨 일이 일어났는지
        self.assertIn(os.path.realpath(self.tmp), reason)   # 어느 디렉터리에서 안 됐는지
        # **실패 사유 자체**가 실린다 — 앞의 "실행조차"는 템플릿 산문이라 사유를 빼도 남는다.
        # 분류기가 만든 사유 문자열로 대조해야 이 하위 절이 실제로 고정된다(독립 검증 F1).
        measured = driver.run_test_cmd(cfg)
        self.assertIn(measured["tail"][:120], reason,
                      "거부 메시지가 분류기의 실패 사유를 나르지 않는다")
        self.assertIn("127", reason)                  # 셸이 돌려준 실제 종료 코드

    def test_missing_venv_style_command_is_refused(self):
        # 실측 사례의 형태 그대로 — gitignore 된 인터프리터 경로는 새 worktree 에 없다
        ok, reason = driver.startup_guard(
            self.make_config(test_cmd=".venv/bin/python -m pytest tests/ -q"))
        self.assertFalse(ok, "대상에 없는 인터프리터 경로인데 기동이 허용됐다")
        self.assertIn(".venv/bin/python", reason)

    def test_failing_suite_still_launches(self):
        # red 는 TDD 루프의 정상 출발 상태다 — 여기서 막으면 이 도구의 주 용도가 막힌다.
        cfg = self.make_config(test_cmd="%s -c 'import sys; sys.exit(1)'" % sys.executable)
        self.assertEqual(driver.run_test_cmd(cfg)["outcome"], "red")   # 전제: 실제로 red 다
        ok, reason = driver.startup_guard(cfg)
        self.assertTrue(ok, "실패하는 테스트(red)로 기동이 거부됐다: %s" % reason)

    def test_passing_suite_launches(self):
        cfg = self.make_config(test_cmd="%s -c 'import sys; sys.exit(0)'" % sys.executable)
        ok, reason = driver.startup_guard(cfg)
        self.assertTrue(ok, reason)

    def test_check_runs_last_so_a_refused_launch_never_executes_it(self):
        """순서는 비용 문제가 아니라 안전 속성이다(독립 검증 F3).

        검사가 앞에 오면, 거부될 대상에서 **사용자가 준 임의의 셸 명령이 먼저 실행된다** —
        STOP 이 걸린 작업이든 `worktree_guard` 가 거부할 공유 체크아웃이든 마찬가지고,
        그 거부들은 정확히 그 실행을 막으려고 있는 것이다."""
        marker = "preflight-must-not-run"
        # ① 이른 거부(STOP) — 명시적으로 멈춘 작업에서 명령이 돌면 안 된다
        os.makedirs(self.workdir, exist_ok=True)
        stop = os.path.join(self.workdir, "STOP")
        with open(stop, "w") as f:
            f.write("")
        ok, _ = driver.startup_guard(self.make_config(test_cmd="touch %s" % marker))
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, marker)),
                         "STOP 으로 거부되는 기동인데 테스트 명령이 먼저 실행됐다")
        os.remove(stop)
        # ② 직전 거부(R18 공유 체크아웃) — 남의 체크아웃에서 임의 명령을 돌리면 안 된다
        repo = os.path.join(self.tmp, "shared-repo")
        os.makedirs(repo)
        for args in (["init", "-q", repo],
                     ["-C", repo, "commit", "-q", "--allow-empty", "-m", "init"]):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + args,
                           capture_output=True, text=True, check=True)
        ok, _ = driver.startup_guard(
            self.make_config(project=repo, test_cmd="touch %s" % marker))
        self.assertFalse(ok)
        self.assertFalse(os.path.exists(os.path.join(repo, marker)),
                         "worktree 게이트가 거부할 저장소인데 테스트 명령이 먼저 실행됐다")

    def test_check_runs_in_the_target_directory_not_the_launch_directory(self):
        """대상 디렉터리에서 돌지 않으면 검사가 의미를 잃는다 — 잡으려는 실패가 정확히
        '사용자 체크아웃에서는 돌고 대상에서는 안 되는 명령'이기 때문이다."""
        project = os.path.join(self.tmp, "target")
        launch = os.path.join(self.tmp, "launch")
        os.makedirs(project)
        os.makedirs(launch)
        cfg = self.make_config(project=project, cwd=launch, test_cmd="touch preflight-ran-here")
        ok, reason = driver.startup_guard(cfg)
        self.assertTrue(ok, reason)
        self.assertTrue(os.path.exists(os.path.join(project, "preflight-ran-here")),
                        "대상 디렉터리에서 실행되지 않았다")
        self.assertFalse(os.path.exists(os.path.join(launch, "preflight-ran-here")),
                         "기동 디렉터리에서 실행됐다 — 대상이 아니라 런처를 검사한 셈이다")

    def test_timeout_is_classified_error_under_the_declared_limit(self):
        """타임아웃 갈래는 실행이 불가능해 실제로 재현할 수 없다 — 경계를 모킹해 고정한다."""
        cfg = self.make_config(test_cmd="sleep 999999")
        seen, original = {}, driver.subprocess.run

        def fake_run(*args, **kwargs):
            seen.update(kwargs)
            raise driver.subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout"))

        driver.subprocess.run = fake_run
        try:
            result = driver.run_test_cmd(cfg)
        finally:
            driver.subprocess.run = original
        self.assertEqual(result["outcome"], "error")      # 통과도 실패도 아니다(R5-1)
        self.assertEqual(result["kind"], "timeout")       # 실행 불가와 갈린다
        self.assertEqual(seen.get("timeout"), driver.TEST_TIMEOUT,
                         "선언된 상한이 실제로 subprocess 에 걸리지 않는다")

    def test_timeout_refusal_does_not_read_like_a_missing_runner(self):
        """30분을 기다린 사용자에게 '실행조차 못 했다 / `.venv` 를 확인하라'는 오답이다.

        명령 자체는 **즉시 끝나는 것**을 쓴다 — 여기서 검사하는 것은 메시지 갈래지 대기가
        아니고, 실제로 안 끝나는 명령을 쓰면 이 패치를 우회하는 변이가 걸렸을 때 테스트가
        실패하는 대신 영원히 매달린다(멈춘 스위트는 판정을 주지 못한다)."""
        cfg = self.make_config(test_cmd="%s -c 'pass'" % sys.executable)
        original = driver.run_test_cmd
        driver.run_test_cmd = lambda c: {
            "outcome": "error", "kind": "timeout",
            "tail": "test runner timed out after 1800s: TAIL-TIMEOUT-MARK"}
        try:
            ok, reason = driver.startup_guard(cfg)
        finally:
            driver.run_test_cmd = original
        self.assertFalse(ok, "타임아웃인데 기동이 허용됐다")
        self.assertIn("제한 시간", reason)
        self.assertIn("TAIL-TIMEOUT-MARK", reason)        # 사유는 이쪽 갈래에서도 실린다
        self.assertNotIn(".venv", reason)                 # 없는 러너 처방을 붙이지 않는다
        self.assertNotIn("실행조차", reason)

    def test_preflight_uses_the_loop_classifier(self):
        """사전 검사에 두 번째 분류기를 두면 루프의 것과 드리프트한다 — 같은 경로를 쓴다."""
        cfg = self.make_config(test_cmd=BROKEN_RUNNER)
        seen, original = [], driver.run_test_cmd
        driver.run_test_cmd = lambda c: (seen.append(c.test_cmd), original(c))[1]
        try:
            ok, _ = driver.startup_guard(cfg)
        finally:
            driver.run_test_cmd = original
        self.assertFalse(ok)
        self.assertEqual(seen, [BROKEN_RUNNER], "사전 검사가 run_test_cmd 를 쓰지 않는다")
        # 루프 쪽도 같은 함수를 지난다(한쪽만 바꾸면 분류가 갈린다)
        seen.clear()
        driver.run_test_cmd = lambda c: (seen.append(c.test_cmd), original(c))[1]
        try:
            driver.Driver(cfg)._run_test()
        finally:
            driver.run_test_cmd = original
        self.assertEqual(seen, [BROKEN_RUNNER], "루프가 run_test_cmd 를 쓰지 않는다")


class TestVerifyPromptCarriesMeasurement(DriverTestBase):
    """R5·R6 — 읽기 전용 검증 세션에 드라이버 실측을 준다(실측 2026-08-02).

    그 런의 검증 세션은 "pytest 실행이 거부돼 완료 기준 1을 직접 재지 못했다"를 BLOCK 사유로
    적었다. 드라이버는 그 값을 이미 독립 실행으로 갖고 있었다."""

    def test_measurement_is_stated_as_the_drivers_own(self):
        verify = driver.build_verify_prompt(self.make_config(),
                                            {"outcome": "green", "tail": "TAIL-MARKER-42"})
        self.assertIn("TAIL-MARKER-42", verify)                 # 원시 tail 그대로
        self.assertIn("GREEN", verify)                          # 분류 라벨
        low = verify.lower()
        self.assertIn("driver's own independent measurement", low)
        self.assertIn("not the implementing session's claim", low)

    def test_all_three_outcomes_are_labelled(self):
        for outcome, label in [("green", "GREEN"), ("red", "RED"), ("error", "ERROR")]:
            verify = driver.build_verify_prompt(self.make_config(),
                                                {"outcome": outcome, "tail": "T-%s" % outcome})
            self.assertIn(label, verify)
            self.assertIn("T-%s" % outcome, verify)
        # error 는 통과도 실패도 아니라는 것이 함께 실린다(R5-1)
        err = driver.build_verify_prompt(self.make_config(), {"outcome": "error", "tail": "t"})
        self.assertIn("absence of evidence", err.lower())

    def test_measurement_does_not_settle_criterion_coverage(self):
        """green 을 커버리지 증거로 읽으면 R17 래칫이 통째로 무력해진다."""
        verify = driver.build_verify_prompt(self.make_config(),
                                            {"outcome": "green", "tail": "ok"})
        self.assertIn("TEST RATCHET CHECK", verify)             # 래칫 검사는 그대로 선다
        low = verify.lower()
        self.assertIn("does not settle", low)
        self.assertIn("proves nothing about", low)
        self.assertIn("coverage", low)
        # 자가 실행 금지 — 자기가 만든 결과로 판정하면 독립성이 사라진다
        self.assertIn("cannot run the suite yourself", low)

    def test_injected_tail_is_marked_as_data(self):
        # 프로세스 출력 주입이므로 untrusted 봉투가 필요하다(루트 3절·R2⑥과 같은 부류)
        verify = driver.build_verify_prompt(self.make_config(),
                                            {"outcome": "red", "tail": "INJECTED"})
        low = verify.lower()
        self.assertIn("not user instructions", low)
        self.assertLess(low.index("not user instructions"), verify.index("INJECTED"))

    def test_absent_test_cmd_says_there_is_no_measurement(self):
        verify = driver.build_verify_prompt(self.make_config(), None)
        self.assertIn("no independent measurement", verify.lower())
        self.assertNotIn("GREEN", verify)     # 없는 측정을 통과로 읽히게 두지 않는다

    def test_verify_session_prompt_carries_the_measured_tail(self):
        # 경계 통과 확인 — 호출부가 실측을 넘기지 않으면 프롬프트에 tail 이 없다
        self.write_scenario([
            {"text": status_text("done", 0)},
            {"text": verdict_text("PASS")},
        ])
        cfg = self.make_config(max_iterations=2, test_cmd=(
            "%s -c \"print('MEASURED-TAIL-MARKER')\"" % sys.executable))
        self.assertEqual(driver.Driver(cfg).run(), "done")
        verify_prompt = self.recorded_prompt(1)
        self.assertIn("MEASURED-TAIL-MARKER", verify_prompt)
        self.assertIn("DRIVER-MEASURED TEST RESULT", verify_prompt)

    def test_readonly_allow_is_not_widened(self):
        """실측을 주는 것이 권한 변경의 대체재다 — 검증 세션은 여전히 러너를 못 쥔다."""
        self.assertEqual(driver.READONLY_ALLOW, [
            "Read", "Glob", "Grep",
            "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)",
            "Bash(ls:*)", "Bash(cat:*)",
        ])
        joined = " ".join(driver.READONLY_ALLOW).lower()
        for runner in ["pytest", "npm", "pnpm", "go test", "cargo", "python", "make"]:
            self.assertNotIn(runner, joined)
        # 사용자 확장 그랜트도 검증 세션에는 실리지 않는다(R3)
        cfg = self.make_config(allow_extra=["Bash(pytest:*)"])
        self.assertNotIn("Bash(pytest:*)", driver.build_claude_args(cfg, "p", readonly=True))


class TestC27WorktreeGuard(DriverTestBase):
    """R18 — 하위 프로젝트의 공유 체크아웃을 대상으로 한 무인 루프는 기동하지 않는다(ADR 035)."""

    def git(self, *args):
        proc = subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(args),
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, "git %s 실패: %s" % (args, proc.stderr))
        return proc.stdout

    def make_repo(self):
        """커밋 1개짜리 저장소(main 체크아웃)를 만들고 경로를 돌려준다."""
        repo = os.path.join(self.tmp, "repo")
        os.makedirs(repo)
        self.git("init", "-q", repo)
        self.git("-C", repo, "commit", "-q", "--allow-empty", "-m", "init")
        return repo

    def test_shared_checkout_is_refused_with_worktree_guidance(self):
        self._force_profile("개인")  # 실제 REGISTRY.md를 읽으면 설치처마다 문구가 달라진다
        repo = self.make_repo()
        ok, reason = driver.startup_guard(self.make_config(project=repo))
        self.assertFalse(ok, "공유 체크아웃 대상인데 기동이 허용됐다")
        self.assertIn("worktree", reason)
        self.assertIn("R18", reason)

    def _force_profile(self, value):
        """`install_profile` 을 고정한다 — REGISTRY.md 는 미추적이라 기계마다 다르고,
        이 검사가 그 파일의 실제 내용에 걸리면 다른 설치처에서 임의로 빨개진다."""
        original = driver.install_profile
        driver.install_profile = lambda: value
        self.addCleanup(lambda: setattr(driver, "install_profile", original))

    def test_corporate_profile_refuses_without_telling_you_to_make_a_worktree(self):
        """사내에서는 기존 안내가 ADR 043 이 금지한 것을 시키는 말이 된다."""
        self._force_profile("사내")
        repo = self.make_repo()
        ok, reason = driver.startup_guard(self.make_config(project=repo))
        self.assertFalse(ok, "사내라고 공유 체크아웃이 허용되면 안 된다 — 거부는 프로필과 무관하다")
        self.assertIn("ADR 043", reason)
        self.assertNotIn("worktree add", reason)

    def test_non_corporate_profile_keeps_the_worktree_guidance(self):
        self._force_profile("개인")
        repo = self.make_repo()
        ok, reason = driver.startup_guard(self.make_config(project=repo))
        self.assertFalse(ok)
        self.assertIn("worktree add", reason)
        self.assertNotIn("ADR 043", reason)

    def test_unreadable_profile_still_refuses(self):
        """프로필은 안내 문구만 고른다 — 판독 실패가 통과로 바뀌면 게이트가 프로필에 인질이 된다."""
        self._force_profile(None)
        repo = self.make_repo()
        ok, reason = driver.startup_guard(self.make_config(project=repo))
        self.assertFalse(ok, "프로필 미상인데 공유 체크아웃이 통과했다")
        self.assertIn("R18", reason)

    def test_install_profile_returns_none_when_the_load_fails(self):
        """판독 실패는 예외가 아니라 None 이어야 한다 — 무인 드라이버 안에서 돌기 때문이다.

        빈 디렉터리를 루트로 물리면 `_common.py` 도 `REGISTRY.md` 도 없다. 이 단언이
        `install_profile` 의 try/except 를 붙잡는다(그것을 지우면 여기서 FileNotFoundError 가 샌다(`spec_from_file_location` 이 `.py` 경로에 `SourceFileLoader` 를 주므로 import 해석이 아니라 `get_data` 에서 터진다 — 실측))."""
        empty = tempfile.mkdtemp(dir=self.tmp)
        original = driver.harness_root
        driver.harness_root = lambda: empty
        self.addCleanup(lambda: setattr(driver, "harness_root", original))
        self.assertIsNone(driver.install_profile())

    def test_install_profile_reads_the_hooks_common_module(self):
        """경로가 하드코딩이라, `_common.py` 가 옮겨지면 문구가 조용히 금지된 안내로 되돌아간다.

        거부 자체는 살아남으므로 이것은 가시성 검사다 — 게이트가 조용히 잠드는 쪽을 붙잡는다."""
        path = os.path.join(driver.harness_root(), ".agents", "hooks", "_common.py")
        self.assertTrue(os.path.isfile(path), "프로필 판정 원본이 그 자리에 없다: %s" % path)

    def test_linked_worktree_passes(self):
        repo = self.make_repo()
        wt = os.path.join(self.tmp, "wt")
        self.git("-C", repo, "worktree", "add", "-q", wt, "-b", "feat/x")
        ok, reason = driver.startup_guard(self.make_config(project=wt))
        self.assertTrue(ok, "전용 worktree인데 거부됐다: %s" % reason)

    def test_subdirectory_of_shared_checkout_is_refused(self):
        """rev-parse가 상대·절대를 섞어 내놓는 지점 — 정규화 없이 비교하면 여기서 통과해버린다."""
        repo = self.make_repo()
        sub = os.path.join(repo, "src")
        os.makedirs(sub)
        ok, _ = driver.startup_guard(self.make_config(project=sub))
        self.assertFalse(ok, "공유 체크아웃 하위 디렉터리인데 기동이 허용됐다")

    def test_launch_directory_cannot_create_an_exemption(self):
        """면제 기준점은 기동 위치가 아니라 드라이버 파일의 위치다(독립 검증 F1).

        `os.getcwd()`를 기준으로 삼으면 하위 프로젝트 안에서 기동하는 것만으로 그 저장소가
        '루트'가 되어 면제가 자기 자신에게 발동하고, 게이트가 통째로 무효가 된다."""
        repo = self.make_repo()
        sub = os.path.join(repo, "src")
        os.makedirs(sub)
        for cwd in (repo, sub):
            ok, _ = driver.startup_guard(self.make_config(project=repo, cwd=cwd))
            self.assertFalse(ok, "대상 저장소 안(%s)에서 기동했다고 게이트가 면제됐다" % cwd)

    def test_git_env_overrides_do_not_defeat_the_check(self):
        """`GIT_DIR` 류가 환경에 있으면 rev-parse 가 대상 대신 그걸 답해 두 값이 항상 같아진다."""
        repo = self.make_repo()
        os.environ["GIT_DIR"] = os.path.join(repo, ".git")
        try:
            ok, _ = driver.startup_guard(self.make_config(project=repo))
        finally:
            os.environ.pop("GIT_DIR", None)
        self.assertFalse(ok, "GIT_DIR 환경변수로 게이트가 통과됐다")

    def test_harness_repository_is_exempt(self):
        """하네스 저장소는 main 직커밋이 규칙이다(§5) — 그 아래 `_workspace/` 샌드박스도 함께 들어온다.

        기준점이 드라이버 파일의 위치이므로, 실제 하네스 저장소로만 이 면제를 검사할 수 있다."""
        here = os.path.dirname(os.path.realpath(driver.__file__))
        if driver.harness_repo_common_dir() is None:
            self.skipTest("드라이버가 git 저장소 안에 있지 않다")
        ok, reason = driver.startup_guard(self.make_config(project=here))
        self.assertTrue(ok, "하네스 저장소 대상인데 거부됐다: %s" % reason)

    def test_non_git_directory_passes(self):
        ok, reason = driver.startup_guard(self.make_config(project=self.tmp))
        self.assertTrue(ok, "git 저장소가 아닌데 거부됐다: %s" % reason)

    def test_unreadable_git_state_is_refused_not_exempted(self):
        """판정 불가는 면제가 아니다 — 통과로 두면 R16을 fail-closed로 만든 이유가 무너진다."""
        cfg = self.make_config(project=self.tmp)
        original = driver.resolve_git_dirs
        driver.resolve_git_dirs = lambda path: (None, None, "git 실행 실패(테스트)")
        try:
            ok, reason = driver.startup_guard(cfg)
        finally:
            driver.resolve_git_dirs = original
        self.assertFalse(ok, "git 상태를 못 읽었는데 기동이 허용됐다")
        self.assertIn("판정", reason)

    def test_missing_project_directory_is_refused(self):
        ok, _ = driver.startup_guard(self.make_config(project=os.path.join(self.tmp, "nope")))
        self.assertFalse(ok, "존재하지 않는 대상 디렉터리인데 기동이 허용됐다")

    def test_driver_holds_no_worktree_grant(self):
        """만드는 쪽은 기동 세션이다 — Claude 엔진의 무인 게이트는 넓히지 않는다.

        문자열 부재만 보면 `Bash(git:*)` 같은 광역 그랜트가 통과하므로 그쪽도 함께 막는다."""
        for pattern in driver.SAFE_ALLOW + driver.READONLY_ALLOW:
            self.assertNotIn("worktree", pattern)
            self.assertNotIn(pattern, ("Bash(git:*)", "Bash(git)", "Bash(*)", "Bash"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
