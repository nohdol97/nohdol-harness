#!/usr/bin/env python3
"""autoloop driver 회귀 테스트 — 스펙 docs/specs/2026-07-19-autoloop-driver.md 완료 기준(C1~C12).

실행: python3 .agents/skills/autoloop/scripts/driver_test.py
부수 효과: 임시 디렉토리만 사용하며 전부 정리한다. 실제 claude CLI를 호출하지 않는다
(fake claude 실행파일로 CLI 경계를 모킹 — R7⑦ 프로세스 실패까지 재현).
"""
import json
import os
import shutil
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
                    "Bash(npm run:*)", "Bash(pnpm:*)", "Bash(git checkout:*)", "Bash(sh:*)"]:
            self.assertNotIn(pat, driver.SAFE_ALLOW)
            self.assertNotIn(pat, driver.READONLY_ALLOW)

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
        note = open(os.path.join(self.workdir, "carryover.md")).read()
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
        self.assertFalse(rec["test"]["green"])

    def test_green_recorded(self):
        self.write_scenario([{"text": status_text("continue", 1)}])
        cfg = self.make_config(test_cmd="%s -c 'import sys; sys.exit(0)'" % sys.executable, max_iterations=1)
        driver.Driver(cfg).run()
        with open(os.path.join(self.workdir, "iters", "iter-1.json")) as f:
            rec = json.load(f)
        self.assertTrue(rec["test"]["green"])


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
        open(os.path.join(self.workdir, "STOP"), "w").write("")
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
        log = open(os.path.join(self.workdir, "driver.log")).read()
        self.assertIn("EXIT", log)
        self.assertIn("exhausted", log)


class TestCostCeiling(DriverTestBase):
    """R7⑥ 비용 상한 (스펙 C 목록 외 보강 테스트)."""

    def test_cost_ceiling_stops(self):
        self.write_scenario([{"text": status_text("continue", 5), "cost": 0.6}] * 5)
        cfg = self.make_config(max_cost_usd=1.0, stall_limit=99)
        self.assertEqual(driver.Driver(cfg).run(), "cost")


if __name__ == "__main__":
    unittest.main(verbosity=2)
