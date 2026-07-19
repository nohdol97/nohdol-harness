#!/usr/bin/env python3
"""autoloop driver — 자율 멀티세션 루프 (스펙: docs/specs/2026-07-19-autoloop-driver.md).

세션 바깥에서 `claude -p`(headless)를 반복 기동한다. 새 프로세스 = 새 컨텍스트이므로
/clear 없이 컨텍스트가 매 반복 리셋되고, 반복 간 상태는 carryover 노트로 넘긴다.

게이트 3종이 이 스크립트의 존재 이유다:
- 안전(R3): acceptEdits + allow/disallow 목록. bypassPermissions는 어떤 경로로도 금지(§3).
- 검증(R5·R6): 테스트는 드라이버가 독립 실행한 결과만 증거. done 주장은 reviewer 검증 반복을 통과해야 확정.
- 정지(R7): done/blocked/stalled/exhausted/stopped/cost/error — 반드시 하나로 끝난다.

실행: python3 driver.py --spec <경로> [--project DIR] [--test-cmd CMD] [--max-iterations N]
                        [--stall-limit N] [--max-cost-usd X] [--work-name SLUG]
테스트: python3 driver_test.py (수정 시 반드시 통과 — C1~C12)
"""
import argparse
import dataclasses
import datetime
import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# 안전 게이트 목록 (R3) — 읽기·편집·안전 Bash만 무인 허용, 파괴 패턴은 명시 차단.
# disallow가 allow보다 우선한다(CLI 의미론). 전면 bypass는 절대 추가하지 않는다(§3).
#
# bare 인터프리터·러너 그랜트(python3:*, python:*, npx:*, npm run:*, pnpm:*,
# git checkout:*)는 금지 — 임의 코드 실행으로 블랙리스트를 감싸 우회할 수 있어
# 게이트가 지시 수준으로 격하된다(리뷰 H1). 프로젝트별 러너가 더 필요하면
# --allow-extra 로 사용자가 명시적으로 그랜트한다(§3 정합).
# ---------------------------------------------------------------------------
SAFE_ALLOW = [
    "Read", "Glob", "Grep", "Edit", "Write", "Task", "TodoWrite",
    "Bash(git add:*)", "Bash(git commit:*)", "Bash(git status:*)",
    "Bash(git diff:*)", "Bash(git log:*)", "Bash(git branch:*)", "Bash(git checkout -b:*)",
    "Bash(npm test:*)", "Bash(npm run test:*)", "Bash(npm run build:*)", "Bash(npm run lint:*)",
    "Bash(pnpm test:*)", "Bash(pnpm run test:*)",
    "Bash(pytest:*)", "Bash(python3 -m pytest:*)",
    "Bash(go test:*)", "Bash(go build:*)", "Bash(cargo test:*)", "Bash(cargo build:*)",
    "Bash(ls:*)", "Bash(cat:*)", "Bash(mkdir:*)",
]
READONLY_ALLOW = [
    "Read", "Glob", "Grep",
    "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(ls:*)", "Bash(cat:*)",
]
DESTRUCTIVE_DISALLOW = [
    "Bash(git push --force:*)", "Bash(git push -f:*)", "Bash(git reset --hard:*)",
    "Bash(git clean:*)", "Bash(rm -rf:*)", "Bash(sudo:*)",
    "Bash(kubectl:*)", "Bash(helm:*)", "Bash(terraform:*)", "Bash(aws:*)", "Bash(gcloud:*)",
    "Bash(docker push:*)", "Bash(docker rm:*)", "Bash(docker rmi:*)", "Bash(docker compose down:*)",
    "Bash(alembic:*)", "Bash(prisma migrate:*)", "Bash(flyway:*)",
    "Bash(psql:*)", "Bash(mysql:*)", "Bash(gh:*)",
]

VALID_STATUS = {"done", "continue", "blocked"}
JSON_FENCE = re.compile(r"```json\s*\n(.*?)\n\s*```", re.DOTALL)


@dataclasses.dataclass
class Config:
    spec: str
    project: str = "."
    test_cmd: str = ""
    max_iterations: int = 10
    stall_limit: int = 3
    max_cost_usd: float = 0.0
    work_name: str = ""
    workspace: str = ""          # 산출 디렉토리(기본: <cwd>/_workspace/autoloop/<work_name>)
    claude_cmd: list = dataclasses.field(default_factory=lambda: ["claude"])
    cwd: str = "."               # claude 실행 cwd — 하네스 루트여야 항상-온 로드(§12)
    model: str = ""
    claude_timeout: int = 3600   # 반복 1회 상한(초)
    allow_extra: list = dataclasses.field(default_factory=list)  # 사용자 명시 확장 그랜트(R3)

    def workdir(self):
        if self.workspace:
            return self.workspace
        name = self.work_name or os.path.splitext(os.path.basename(self.spec))[0]
        return os.path.join(self.cwd, "_workspace", "autoloop", name)


# ---------------------------------------------------------------------------
# 순수 함수 (테스트 가능 경계)
# ---------------------------------------------------------------------------

def parse_status_block(text):
    """세션 출력에서 마지막 유효 상태 블록을 채택한다(R4). 실패 시 continue 폴백."""
    fallback = {"status": "continue", "open_items": None, "note": "", "parsed": False}
    result = fallback
    for match in JSON_FENCE.finditer(text or ""):
        try:
            data = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue
        if not isinstance(data, dict) or data.get("status") not in VALID_STATUS:
            continue
        try:
            open_items = int(data["open_items"]) if data.get("open_items") is not None else None
        except (ValueError, TypeError):
            open_items = None
        result = {"status": data["status"], "open_items": open_items,
                  "note": str(data.get("note", "")), "parsed": True}
    return result


def parse_verdict_block(text):
    """검증 세션 출력에서 마지막 PASS/BLOCK 판정을 채택한다(R6). 실패 시 BLOCK(보수적)."""
    result = {"verdict": "BLOCK", "reason": "verdict block missing or unparseable", "parsed": False}
    for match in JSON_FENCE.finditer(text or ""):
        try:
            data = json.loads(match.group(1))
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict) and data.get("verdict") in ("PASS", "BLOCK"):
            result = {"verdict": data["verdict"], "reason": str(data.get("reason", "")), "parsed": True}
    return result


def build_anchor(cfg):
    """불변 앵커(R2) — 반복이 지나도 절대 바뀌지 않는 목표 선언. 드리프트 방지의 축."""
    return (
        "[ANCHOR - immutable goal, never rewrite this]\n"
        "Target spec: %s\n"
        "Target project directory: %s\n"
        "Read the spec first. Its completion criteria (완료 기준) checklist is the ONLY finish line.\n"
        "You are ONE iteration of an unattended autonomous loop. Your context will be discarded;\n"
        "only the handoff note and committed code survive to the next iteration."
        % (cfg.spec, cfg.project)
    )


def build_prompt(anchor, note_text, test_result, feedback):
    """반복 프롬프트(R2): 앵커 + 직전 노트 + 독립 테스트 결과 + 피드백 + 고정 지시문."""
    parts = [
        anchor,
        "\n[HANDOFF NOTE from previous iteration]\n" + (note_text or "(first iteration - no note yet)"),
        "\n[INDEPENDENT TEST RESULT (driver-run, this is the only trusted evidence)]\n"
        + (test_result or "(not yet run)"),
    ]
    if feedback:
        parts.append("\n[REVIEWER FEEDBACK - fix these before claiming done]\n" + feedback)
    parts.append(
        "\n[INSTRUCTIONS - fixed]\n"
        "1. Follow the harness rules loaded from this workspace (routing, SDD/TDD, guardrails).\n"
        "2. Pick the highest-priority open item from the note (or derive from the spec) and complete it.\n"
        "3. NEVER attempt destructive operations (deploy, resource deletion, force push, DB migration,\n"
        "   IAM changes). If one becomes necessary, stop and report status \"blocked\".\n"
        "4. Update the handoff note file (Korean, keep sections: 한 일/진행 중 · 다음 할 일/막힌 점/참조).\n"
        "   Keep '한 줄 요약' current. List remaining work as concrete open items.\n"
        "5. End your final reply with EXACTLY one fenced json block:\n"
        "```json\n{\"status\": \"done|continue|blocked\", \"open_items\": <int>, \"note\": \"<one line>\"}\n```\n"
        "   \"done\" ONLY when every completion criterion is met and open_items is 0."
    )
    return "\n".join(parts)


def build_verify_prompt(cfg):
    """done 주장 검증용 reviewer 프롬프트(R6) — 읽기 전용, 스펙 완료 기준 대비 판정."""
    return (
        "[VERIFY - read-only review]\n"
        "An autonomous session claims the work for spec %s is complete.\n"
        "Check each completion criterion (완료 기준) in the spec against the actual code/diff in %s.\n"
        "Do NOT modify anything. Judge strictly: unverified criteria mean BLOCK.\n"
        "End with EXACTLY one fenced json block:\n"
        "```json\n{\"verdict\": \"PASS|BLOCK\", \"reason\": \"<what is missing, if BLOCK>\"}\n```"
        % (cfg.spec, cfg.project)
    )


def build_claude_args(cfg, prompt, readonly=False):
    """headless 인자 조립(R3). bypassPermissions·--dangerously-skip-permissions 금지(§3)."""
    args = ["-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits"]
    if cfg.model:
        args += ["--model", cfg.model]
    # 검증 세션(readonly)에는 사용자 확장 그랜트도 주지 않는다 — 판정자는 최소 권한.
    args += ["--allowedTools"] + (READONLY_ALLOW if readonly else SAFE_ALLOW + list(cfg.allow_extra))
    args += ["--disallowedTools"] + DESTRUCTIVE_DISALLOW
    return args


def startup_guard(cfg):
    """기동 사전 검사(R9·R10). 오라클 없는 루프·명시 정지 상태의 무단 재개를 거부한다."""
    if not os.path.isfile(cfg.spec):
        return False, "스펙 파일이 없습니다: %s" % cfg.spec
    with open(cfg.spec, encoding="utf-8", errors="replace") as f:
        body = f.read()
    if "완료 기준" not in body and "Completion Criteria" not in body:
        return False, "스펙에 '완료 기준' 절이 없습니다 — 완료 판정 오라클 없이는 기동하지 않습니다(R9)"
    if os.path.exists(os.path.join(cfg.workdir(), "STOP")):
        return False, "STOP 파일이 있습니다(%s) — 명시적으로 삭제한 뒤 재기동하세요(R10)" % os.path.join(cfg.workdir(), "STOP")
    return True, "ok"


NOTE_TEMPLATE = """# Autoloop Carryover: %(name)s

- 대상 스펙: %(spec)s
- 대상 프로젝트: %(project)s
- 한 줄 요약: (세션이 갱신)

## 한 일 (완료)

## 진행 중 · 다음 할 일

## 막힌 점 · 미해결

## 사용자 확인 필요

## 참조
"""


# ---------------------------------------------------------------------------
# 드라이버 본체
# ---------------------------------------------------------------------------

class Driver:
    def __init__(self, cfg):
        self.cfg = cfg
        self.workdir = cfg.workdir()
        self.note_path = os.path.join(self.workdir, "carryover.md")
        self.log_path = os.path.join(self.workdir, "driver.log")
        self.iters_dir = os.path.join(self.workdir, "iters")

    # -- 파일 유틸 ---------------------------------------------------------
    def _ensure_workdir(self):
        os.makedirs(self.iters_dir, exist_ok=True)
        if not os.path.exists(self.note_path):
            with open(self.note_path, "w", encoding="utf-8") as f:
                f.write(NOTE_TEMPLATE % {
                    "name": self.cfg.work_name or os.path.basename(self.workdir),
                    "spec": self.cfg.spec, "project": self.cfg.project})

    def _read_note(self):
        try:
            with open(self.note_path, encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return ""

    def _log(self, line):
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write("%s | %s\n" % (stamp, line))

    # -- 외부 프로세스 경계 -------------------------------------------------
    def _run_claude(self, prompt, readonly=False):
        """claude 1회 실행. 반환: (ok, result_text, cost)."""
        cmd = list(self.cfg.claude_cmd) + build_claude_args(self.cfg, prompt, readonly=readonly)
        try:
            proc = subprocess.run(cmd, cwd=self.cfg.cwd, capture_output=True, text=True,
                                  timeout=self.cfg.claude_timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            return False, "process error: %s" % e, 0.0
        if proc.returncode != 0:
            return False, "exit %d: %s" % (proc.returncode, (proc.stderr or "")[-500:]), 0.0
        try:
            data = json.loads(proc.stdout)
        except ValueError:
            return False, "unparseable stdout: %s" % proc.stdout[-500:], 0.0
        cost = data.get("total_cost_usd") or 0.0
        return True, str(data.get("result", "")), float(cost)

    def _run_test(self):
        """독립 검증(R5) — 이 결과만이 증거다. 반환: dict 또는 None(test_cmd 없음)."""
        if not self.cfg.test_cmd:
            return None
        try:
            proc = subprocess.run(self.cfg.test_cmd, shell=True, cwd=self.cfg.project,
                                  capture_output=True, text=True, timeout=1800)
            green, tail = proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
        except (OSError, subprocess.TimeoutExpired) as e:
            green, tail = False, "test runner error: %s" % e
        return {"green": green, "tail": tail}

    # -- 루프 --------------------------------------------------------------
    def run(self):
        cfg = self.cfg
        self._ensure_workdir()
        anchor = build_anchor(cfg)
        last_test, feedback = None, ""
        prev_open, stall, proc_fail, parse_fail, total_cost = None, 0, 0, 0, 0.0
        seen_valid, prev_green = False, None  # M2: 최초 유효 반복만 기본 진전으로 인정
        self._log("START spec=%s project=%s max_iter=%d stall_limit=%d"
                  % (cfg.spec, cfg.project, cfg.max_iterations, cfg.stall_limit))
        if not cfg.test_cmd:
            self._log("WARN no --test-cmd: independent evidence is weakened (R9)")

        exit_reason = "exhausted"
        for n in range(1, cfg.max_iterations + 1):
            # R7⑤ 정지 파일 — 반복 경계에서만, 파일은 보존(해제는 사용자 몫)
            if os.path.exists(os.path.join(self.workdir, "STOP")):
                exit_reason = "stopped"
                break

            prompt = build_prompt(anchor, self._read_note(),
                                  self._format_test(last_test), feedback)
            feedback = ""  # L4: 피드백은 1회 주입 후 소거(다음 판정에서 재설정)
            ok, text, cost = self._run_claude(prompt)
            total_cost += cost
            if not ok:
                proc_fail += 1
                self._log("iter %d | claude failure (%d consecutive): %s" % (n, proc_fail, text[:200]))
                if proc_fail >= 2:                      # R7⑦
                    exit_reason = "error"
                    break
                continue
            proc_fail = 0

            status = parse_status_block(text)
            parse_fail = 0 if status["parsed"] else parse_fail + 1
            last_test = self._run_test()                # R5: 세션 주장과 무관하게 실측
            self._write_iter(n, status, last_test, cost)
            self._log("iter %d | status=%s open=%s test=%s cost=%.4f"
                      % (n, status["status"], status["open_items"], self._short_test(last_test), cost))

            if status["status"] == "blocked":           # R3·R7②
                self._append_note_blocked(status["note"])
                exit_reason = "blocked"
                break

            if parse_fail >= 2:                         # R4: 연속 파싱 실패 = 정체
                exit_reason = "stalled"
                break

            # R6 완료 판정: done 주장 + open 0 + 실측 green → 검증 반복
            if (status["status"] == "done" and status["open_items"] == 0
                    and (last_test is None or last_test["green"])):
                v_ok, v_text, v_cost = self._run_claude(build_verify_prompt(cfg), readonly=True)
                total_cost += v_cost
                verdict = parse_verdict_block(v_text) if v_ok else \
                    {"verdict": "BLOCK", "reason": "verify session failed: %s" % v_text[:200]}
                self._log("iter %d | verify=%s %s" % (n, verdict["verdict"], verdict["reason"][:200]))
                if verdict["verdict"] == "PASS":
                    exit_reason = "done"
                    break
                feedback = verdict["reason"]            # BLOCK → 사유를 다음 반복에 주입
            elif status["status"] == "done":
                feedback = ("You claimed done but the driver-run test is red or open_items != 0. "
                            "Fix the failing tests / remaining items first.")

            # R7③ 진전 판정: 첫 유효 반복(1회만) or open 감소 or 테스트 red→green.
            # open_items 미보고(null) 반복은 첫 유효 반복 이후 무진전으로 센다(M2 —
            # "파싱만 되면 진전" 처리는 정체 게이트를 영구 우회시킨다).
            progressed = False
            if status["parsed"] and not seen_valid:
                progressed, seen_valid = True, True
            elif (status["open_items"] is not None and prev_open is not None
                  and status["open_items"] < prev_open):
                progressed = True
            elif last_test and last_test["green"] and prev_green is False:
                progressed = True
            prev_green = last_test["green"] if last_test else prev_green
            if status["open_items"] is not None:
                prev_open = status["open_items"]
            stall = 0 if progressed else stall + 1
            if stall >= cfg.stall_limit:
                exit_reason = "stalled"
                break

            # R7⑥ 비용 상한(결과 JSON이 비용을 제공할 때만)
            if cfg.max_cost_usd and total_cost > cfg.max_cost_usd:
                exit_reason = "cost"
                break

        self._log("EXIT reason=%s total_cost=%.4f" % (exit_reason, total_cost))
        return exit_reason

    # -- 기록 --------------------------------------------------------------
    @staticmethod
    def _format_test(t):
        if t is None:
            return ""
        return "%s\n%s" % ("GREEN (exit 0)" if t["green"] else "RED (nonzero exit)", t["tail"])

    @staticmethod
    def _short_test(t):
        return "n/a" if t is None else ("green" if t["green"] else "red")

    def _write_iter(self, n, status, test, cost):
        with open(os.path.join(self.iters_dir, "iter-%d.json" % n), "w", encoding="utf-8") as f:
            json.dump({"iter": n, "status": status, "test": test, "cost": cost}, f, ensure_ascii=False)

    def _append_note_blocked(self, note):
        stamp = datetime.datetime.now().isoformat(timespec="seconds")
        with open(self.note_path, "a", encoding="utf-8") as f:
            f.write("\n## 사용자 확인 필요 (driver — blocked %s)\n- %s\n" % (stamp, note or "(사유 미보고)"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="autoloop driver (스펙: docs/specs/2026-07-19-autoloop-driver.md)")
    parser.add_argument("--spec", required=True)
    parser.add_argument("--project", default=".")
    parser.add_argument("--test-cmd", default="")
    parser.add_argument("--max-iterations", type=int, default=10)
    parser.add_argument("--stall-limit", type=int, default=3)
    parser.add_argument("--max-cost-usd", type=float, default=0.0)
    parser.add_argument("--work-name", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--allow-extra", action="append", default=[],
                        help="추가 허용 도구 패턴(반복 가능) — 사용자 명시 그랜트(R3)")
    args = parser.parse_args(argv)

    cfg = Config(spec=os.path.abspath(args.spec), project=os.path.abspath(args.project),
                 test_cmd=args.test_cmd, max_iterations=args.max_iterations,
                 stall_limit=args.stall_limit, max_cost_usd=args.max_cost_usd,
                 work_name=args.work_name, cwd=os.getcwd(), model=args.model,
                 allow_extra=args.allow_extra)
    ok, reason = startup_guard(cfg)
    if not ok:
        print("[autoloop] 기동 거부: %s" % reason, file=sys.stderr)
        return 2
    reason = Driver(cfg).run()
    print("[autoloop] 종료: %s (로그: %s)" % (reason, os.path.join(cfg.workdir(), "driver.log")))
    return 0 if reason == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
