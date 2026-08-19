#!/usr/bin/env python3
"""Local read-only dashboard for autoloop work directories.

The dashboard deliberately treats every log and agent-produced string as data.
It binds only to loopback and exposes no mutation endpoint.
"""
import argparse
import datetime
import hashlib
import heapq
import json
import math
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse, urlsplit


LOOPBACK = "127.0.0.1"
MAX_JSON_BYTES = 1024 * 1024
MAX_TEXT_BYTES = 128 * 1024
MAX_DETAIL_ITERATIONS = 200
ITER_FILE = re.compile(r"^iter-(\d+)\.json$")
EXIT_LINE = re.compile(
    r"^\[autoloop\] 종료: (done|blocked|stalled|exhausted|stopped|cost|error)"
    r"(?: \(로그: .+\))?\s*$", re.MULTILINE)
EXIT_REASONS = {"done", "blocked", "stalled", "exhausted", "stopped", "cost", "error"}


INDEX_HTML = r'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>autoloop 진행 대시보드</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --panel: #131b2f;
      --panel-2: #19243b;
      --line: #2a3854;
      --text: #e9eef8;
      --muted: #9ba9bf;
      --accent: #79a8ff;
      --green: #4fd1a5;
      --yellow: #f2c66d;
      --red: #ff7b86;
      --purple: #b69cff;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: radial-gradient(circle at top, #16213b 0, var(--bg) 42rem); color: var(--text); font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif; }
    button { font: inherit; }
    header { position: sticky; top: 0; z-index: 5; display: flex; justify-content: space-between; gap: 1rem; align-items: center; padding: 1rem clamp(1rem, 4vw, 3rem); border-bottom: 1px solid rgba(255,255,255,.08); background: rgba(11,16,32,.88); backdrop-filter: blur(16px); }
    h1, h2, h3, p { margin-top: 0; }
    h1 { margin-bottom: .15rem; font-size: clamp(1.25rem, 3vw, 1.8rem); letter-spacing: -.02em; }
    header p { margin-bottom: 0; color: var(--muted); font-size: .88rem; }
    .controls { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: .55rem; }
    .refresh { min-height: 2.75rem; border: 1px solid var(--line); border-radius: .7rem; padding: .55rem .85rem; color: var(--text); background: var(--panel-2); cursor: pointer; }
    .refresh:hover, .refresh:focus-visible { border-color: var(--accent); outline: 2px solid transparent; }
    main { width: min(1500px, 100%); margin: 0 auto; padding: 1.4rem clamp(1rem, 4vw, 3rem) 4rem; }
    .summary { display: flex; flex-wrap: wrap; gap: .65rem; margin-bottom: 1.25rem; }
    .summary span { padding: .35rem .65rem; border: 1px solid var(--line); border-radius: 999px; background: rgba(19,27,47,.7); color: var(--muted); }
    .layout { display: grid; grid-template-columns: minmax(270px, 390px) minmax(0, 1fr); gap: 1rem; align-items: start; }
    .tasks { display: grid; gap: .75rem; }
    .card { width: 100%; border: 1px solid var(--line); border-radius: 1rem; padding: 1rem; text-align: left; color: var(--text); background: linear-gradient(145deg, rgba(25,36,59,.96), rgba(19,27,47,.96)); cursor: pointer; box-shadow: 0 12px 30px rgba(0,0,0,.12); }
    .card:hover, .card:focus-visible, .card.selected { border-color: var(--accent); outline: none; transform: translateY(-1px); }
    .card-head { display: flex; justify-content: space-between; gap: .75rem; align-items: start; margin-bottom: .8rem; }
    .slug { font-weight: 750; overflow-wrap: anywhere; }
    .badge { flex: none; padding: .18rem .52rem; border-radius: 999px; font-size: .76rem; font-weight: 750; background: #293650; color: var(--muted); }
    .badge.running, .badge.done { color: var(--green); background: rgba(79,209,165,.12); }
    .badge.blocked, .badge.stalled, .badge.cost { color: var(--yellow); background: rgba(242,198,109,.12); }
    .badge.error, .badge.interrupted { color: var(--red); background: rgba(255,123,134,.12); }
    .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .45rem .8rem; color: var(--muted); font-size: .83rem; }
    .metric-grid strong { display: block; color: var(--text); font-size: .92rem; font-weight: 650; }
    .detail { min-height: 28rem; border: 1px solid var(--line); border-radius: 1rem; background: rgba(19,27,47,.9); overflow: hidden; }
    .empty { padding: 3rem 1.3rem; color: var(--muted); text-align: center; }
    .detail-head { padding: 1.25rem; border-bottom: 1px solid var(--line); background: rgba(25,36,59,.62); }
    .detail-head h2 { margin-bottom: .3rem; overflow-wrap: anywhere; }
    .detail-head p { margin-bottom: 0; color: var(--muted); overflow-wrap: anywhere; }
    .facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: .7rem; padding: 1rem 1.25rem; border-bottom: 1px solid var(--line); }
    .fact { min-width: 0; }
    .fact span { display: block; color: var(--muted); font-size: .78rem; }
    .fact strong { display: block; overflow-wrap: anywhere; }
    section { padding: 1.1rem 1.25rem; border-bottom: 1px solid var(--line); }
    section:last-child { border-bottom: 0; }
    section h3 { margin-bottom: .7rem; font-size: 1rem; }
    pre { max-height: 22rem; margin: 0; padding: .85rem; overflow: auto; border: 1px solid var(--line); border-radius: .65rem; white-space: pre-wrap; overflow-wrap: anywhere; background: #0a0f1d; color: #dce5f5; font: 12px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; min-width: 640px; border-collapse: collapse; font-size: .84rem; }
    th, td { padding: .55rem .45rem; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-weight: 600; }
    td.note { max-width: 30rem; overflow-wrap: anywhere; }
    .diagnostic { color: var(--yellow); }
    .error-box { margin-bottom: 1rem; padding: .8rem 1rem; border: 1px solid rgba(255,123,134,.5); border-radius: .7rem; background: rgba(255,123,134,.08); color: var(--red); }
    .muted { color: var(--muted); }
    @media (max-width: 850px) {
      .layout { grid-template-columns: 1fr; }
      .tasks { grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); }
      header { position: static; }
    }
  </style>
</head>
<body>
  <header>
    <div><h1>autoloop 진행 대시보드</h1><p>로컬 파일을 읽기만 하며 2초마다 갱신합니다.</p></div>
    <div class="controls">
      <button class="refresh" id="toggle-refresh" type="button" aria-pressed="false">자동 갱신 일시정지</button>
      <button class="refresh" id="refresh" type="button">지금 새로고침</button>
    </div>
  </header>
  <main>
    <div id="error" role="status" aria-live="polite"></div>
    <div class="summary" id="summary"></div>
    <div class="layout">
      <div class="tasks" id="tasks"></div>
      <article class="detail" id="detail"><p class="empty">왼쪽에서 작업을 선택하세요.</p></article>
    </div>
  </main>
  <script>
    const labels = {
      running: "실행 중", done: "완료", blocked: "사용자 확인 필요", stalled: "정체",
      exhausted: "반복 소진", stopped: "정지됨", cost: "비용 상한", error: "오류",
      interrupted: "중단 의심", unknown: "상태 미확인"
    };
    const phases = {
      starting: "기동 중", implementing: "구현 세션", testing: "독립 테스트",
      verifying: "독립 검증", finished: "종료", unknown: "확인 불가"
    };
    const tests = { green: "GREEN", red: "RED", error: "RUNNER ERROR", "n/a": "측정 없음" };
    let selected = "";
    let busy = false;
    let autoRefresh = true;

    function el(tag, className, value) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (value !== undefined && value !== null) node.textContent = String(value);
      return node;
    }

    function clear(node) { node.replaceChildren(); }
    function value(value, fallback = "—") { return value === null || value === undefined || value === "" ? fallback : value; }
    function cost(task) {
      if (task.cost_measurement === "full") return `$${Number(task.total_cost_usd || 0).toFixed(2)}`;
      if (task.cost_measurement === "partial") return `$${Number(task.total_cost_usd || 0).toFixed(2)} (일부)`;
      return "측정 안 됨";
    }
    function iterationCost(iteration) {
      if (iteration.cost_measurement === "full") return `$${Number(iteration.cost || 0).toFixed(2)}`;
      if (iteration.cost_measurement === "partial") return `$${Number(iteration.cost || 0).toFixed(2)} (일부)`;
      return "측정 안 됨";
    }
    function fact(name, content) {
      const node = el("div", "fact");
      node.append(el("span", "", name), el("strong", "", value(content)));
      return node;
    }
    function setError(message) {
      const root = document.getElementById("error");
      clear(root);
      if (message) root.append(el("div", "error-box", message));
    }

    function renderSummary(tasks) {
      const root = document.getElementById("summary");
      clear(root);
      const running = tasks.filter(task => task.status === "running").length;
      const attention = tasks.filter(task => ["blocked", "stalled", "error", "interrupted"].includes(task.status)).length;
      root.append(el("span", "", `전체 ${tasks.length}`), el("span", "", `실행 중 ${running}`), el("span", "", `확인 필요 ${attention}`));
    }

    function renderCards(tasks) {
      const root = document.getElementById("tasks");
      const focusedSlug = document.activeElement && document.activeElement.dataset
        ? document.activeElement.dataset.slug : "";
      let focusTarget = null;
      clear(root);
      if (!tasks.length) {
        root.append(el("p", "empty", "표시할 autoloop 작업이 없습니다."));
        return;
      }
      tasks.forEach(task => {
        const card = el("button", `card${task.slug === selected ? " selected" : ""}`);
        card.type = "button";
        card.dataset.slug = task.slug;
        card.setAttribute("aria-pressed", String(task.slug === selected));
        if (task.slug === focusedSlug) focusTarget = card;
        const head = el("div", "card-head");
        head.append(el("span", "slug", task.slug), el("span", `badge ${task.status}`, labels[task.status] || task.status));
        const metrics = el("div", "metric-grid");
        metrics.append(
          fact("현재 단계", phases[task.phase] || task.phase),
          fact("반복", `${value(task.run_iteration, "?")} / 누적 ${value(task.total_iterations, 0)}`),
          fact("테스트", tests[task.test_outcome] || value(task.test_outcome)),
          fact("남은 항목", value(task.open_items)),
          fact("비용", cost(task)),
          fact("갱신", value(task.updated_at))
        );
        card.append(head, metrics);
        card.addEventListener("click", () => { selected = task.slug; renderCards(tasks); loadDetail(); });
        root.append(card);
      });
      if (focusTarget) focusTarget.focus({ preventScroll: true });
    }

    function detailSection(title, content, className) {
      const section = el("section");
      section.append(el("h3", "", title));
      if (content) section.append(el("pre", className || "", content));
      else section.append(el("p", "muted", "기록 없음"));
      return section;
    }

    function renderIterations(task) {
      const iterations = task.iterations || [];
      const section = el("section");
      section.append(el("h3", "", "반복 타임라인"));
      if (task.history_truncated) section.append(el("p", "muted", `최근 ${iterations.length}개만 표시합니다 (전체 ${task.iteration_count}개).`));
      if (!iterations.length) {
        section.append(el("p", "muted", "반복 기록 없음"));
        return section;
      }
      const table = el("table");
      const head = el("tr");
      ["누적 반복", "상태", "남은 항목", "테스트", "비용", "메모"].forEach(name => head.append(el("th", "", name)));
      const thead = el("thead"); thead.append(head); table.append(thead);
      const tbody = el("tbody");
      iterations.forEach(iteration => {
        const row = el("tr");
        row.append(
          el("td", "", value(iteration.iter)),
          el("td", "", value(iteration.status && iteration.status.status)),
          el("td", "", value(iteration.status && iteration.status.open_items)),
          el("td", "", tests[iteration.test && iteration.test.outcome] || "측정 없음"),
          el("td", "", iterationCost(iteration)),
          el("td", "note", value(iteration.status && iteration.status.note))
        );
        tbody.append(row);
      });
      table.append(tbody);
      const wrap = el("div", "table-wrap"); wrap.append(table); section.append(wrap); return section;
    }

    function renderEmptyDetail(message) {
      const root = document.getElementById("detail");
      clear(root);
      root.append(el("p", "empty", message || "왼쪽에서 작업을 선택하세요."));
    }

    function renderDetail(task) {
      const root = document.getElementById("detail");
      clear(root);
      const head = el("div", "detail-head");
      head.append(el("h2", "", task.slug), el("p", "", value(task.spec, "스펙 경로 미기록")));
      const facts = el("div", "facts");
      facts.append(
        fact("상태", labels[task.status] || task.status), fact("단계", phases[task.phase] || task.phase),
        fact("기동 횟수", task.run), fact("현재 / 누적 반복", `${value(task.run_iteration, "?")} / ${value(task.total_iterations, 0)}`),
        fact("최신 테스트", tests[task.test_outcome] || value(task.test_outcome)), fact("남은 항목", task.open_items),
        fact("누적 비용", cost(task)), fact("마지막 갱신", task.updated_at)
      );
      root.append(head, facts);
      if (task.diagnostics && task.diagnostics.length) root.append(detailSection("진단", task.diagnostics.join("\n"), "diagnostic"));
      root.append(detailSection("사용자 확인 필요 / carryover", task.carryover));
      root.append(renderIterations(task));
      root.append(detailSection("driver.log 최근 기록", task.log_tail));
    }

    async function loadDetail() {
      if (!selected) return;
      try {
        const response = await fetch(`/api/tasks/${encodeURIComponent(selected)}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`상세 조회 실패: HTTP ${response.status}`);
        renderDetail(await response.json());
      } catch (error) { setError(String(error)); }
    }

    async function refresh() {
      if (busy) return;
      busy = true;
      try {
        const response = await fetch("/api/tasks", { cache: "no-store" });
        if (!response.ok) throw new Error(`목록 조회 실패: HTTP ${response.status}`);
        const data = await response.json();
        setError("");
        renderSummary(data.tasks);
        if (selected && !data.tasks.some(task => task.slug === selected)) {
          selected = "";
          renderEmptyDetail("선택한 작업이 목록에서 사라졌습니다.");
        }
        renderCards(data.tasks);
        if (selected) await loadDetail();
      } catch (error) { setError(String(error)); }
      finally { busy = false; }
    }

    document.getElementById("refresh").addEventListener("click", refresh);
    document.getElementById("toggle-refresh").addEventListener("click", event => {
      autoRefresh = !autoRefresh;
      event.currentTarget.setAttribute("aria-pressed", String(!autoRefresh));
      event.currentTarget.textContent = autoRefresh ? "자동 갱신 일시정지" : "자동 갱신 다시 시작";
    });
    refresh();
    setInterval(() => { if (autoRefresh) refresh(); }, 2000);
  </script>
</body>
</html>
'''


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def root_id(path):
    return hashlib.sha256(os.fsencode(os.path.realpath(path))).hexdigest()


def confined_path(path, boundary, diagnostics):
    """Reject paths leaving a task and all symlinked artifact components."""
    boundary_real = os.path.realpath(boundary)
    candidate = os.path.abspath(path)
    try:
        relative = os.path.relpath(candidate, boundary_real)
        if relative == os.pardir or relative.startswith(os.pardir + os.sep):
            raise ValueError("outside task")
        cursor = boundary_real
        for part in relative.split(os.sep):
            if part in ("", "."):
                continue
            cursor = os.path.join(cursor, part)
            if os.path.islink(cursor):
                diagnostics.append("%s 심볼릭 링크 거부" % os.path.basename(path))
                return None
        if os.path.commonpath([boundary_real, os.path.realpath(candidate)]) != boundary_real:
            raise ValueError("outside task")
    except ValueError:
        diagnostics.append("%s 작업 경계 밖 경로 거부" % os.path.basename(path))
        return None
    return candidate


def reject_nonfinite(value):
    raise ValueError("non-finite JSON number: %s" % value)


def ensure_finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    if isinstance(value, dict):
        for child in value.values():
            ensure_finite(child)
    elif isinstance(value, list):
        for child in value:
            ensure_finite(child)


def read_json(path, diagnostics, boundary=None):
    if boundary is not None:
        path = confined_path(path, boundary, diagnostics)
        if path is None:
            return None
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            raw = f.read(MAX_JSON_BYTES + 1)
        if len(raw.encode("utf-8")) > MAX_JSON_BYTES:
            raise ValueError("file exceeds %d bytes" % MAX_JSON_BYTES)
        value = json.loads(raw, parse_constant=reject_nonfinite)
        if not isinstance(value, dict):
            raise ValueError("top level is not an object")
        ensure_finite(value)
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as e:
        diagnostics.append("%s 읽기 실패: %s" % (os.path.basename(path), e))
        return None


def read_tail(path, diagnostics, limit=MAX_TEXT_BYTES, boundary=None):
    if boundary is not None:
        path = confined_path(path, boundary, diagnostics)
        if path is None:
            return ""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - limit))
            data = f.read(limit)
        return data.decode("utf-8", errors="replace")
    except OSError as e:
        diagnostics.append("%s 읽기 실패: %s" % (os.path.basename(path), e))
        return ""


def pid_alive(pid):
    try:
        pid = int(pid)
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, TypeError, ValueError):
        return False


def safe_task_path(root, slug):
    if not slug or slug in (".", "..") or os.path.basename(slug) != slug:
        return None
    root_real = os.path.realpath(root)
    candidate = os.path.join(root_real, slug)
    if not os.path.isdir(candidate):
        return None
    candidate_real = os.path.realpath(candidate)
    try:
        if os.path.commonpath([root_real, candidate_real]) != root_real:
            return None
    except ValueError:
        return None
    return candidate_real


def read_pid(path, diagnostics, boundary):
    path = confined_path(path, boundary, diagnostics)
    if path is None:
        return None
    try:
        with open(path, "r", encoding="ascii", errors="strict") as f:
            return int(f.read(32).strip())
    except (OSError, UnicodeError, TypeError, ValueError):
        return None


def load_iterations(task_path, diagnostics, limit):
    directory = os.path.join(task_path, "iters")
    directory = confined_path(directory, task_path, diagnostics)
    if directory is None:
        return {"items": [], "latest": None, "count": 0, "truncated": False}
    if not os.path.isdir(directory):
        return {"items": [], "latest": None, "count": 0, "truncated": False}
    numbered = []
    count = 0
    try:
        for entry in os.scandir(directory):
            match = ITER_FILE.match(entry.name)
            if match:
                count += 1
                item = (int(match.group(1)), entry.name)
                if len(numbered) < limit:
                    heapq.heappush(numbered, item)
                elif item > numbered[0]:
                    heapq.heapreplace(numbered, item)
    except OSError as e:
        diagnostics.append("iters 읽기 실패: %s" % e)
        return {"items": [], "latest": None, "count": 0, "truncated": False}
    result = []
    ordered = sorted(numbered, reverse=True)
    latest = None
    for index, (_, name) in enumerate(ordered):
        value = read_json(os.path.join(directory, name), diagnostics, boundary=task_path)
        if value is not None:
            result.append(value)
            if index == 0:
                latest = value
    return {"items": result, "latest": latest, "count": count, "truncated": count > limit}


def legacy_status(task_path, state, launch_log, diagnostics):
    match = None
    for match in EXIT_LINE.finditer(launch_log):
        pass
    if match:
        return match.group(1), "finished"
    pid = read_pid(os.path.join(task_path, "driver.pid"), diagnostics, task_path)
    if pid_alive(pid):
        return "running", "implementing"
    if launch_log:
        return "interrupted", "unknown"
    reason = str((state or {}).get("last_exit_reason", ""))
    if reason in EXIT_REASONS:
        return reason, "finished"
    return "unknown", "unknown"


def collect_task(root, slug, details=False):
    task_path = safe_task_path(root, slug)
    if task_path is None:
        raise KeyError(slug)
    diagnostics = []
    state = read_json(os.path.join(task_path, "state.json"), diagnostics, boundary=task_path) or {}
    run_status = read_json(os.path.join(task_path, "run-status.json"), diagnostics, boundary=task_path)
    history = load_iterations(task_path, diagnostics, MAX_DETAIL_ITERATIONS if details else 1)
    iterations = history["items"]
    latest = history["latest"] or {}
    latest_status = latest.get("status") if isinstance(latest.get("status"), dict) else {}
    latest_test = latest.get("test") if isinstance(latest.get("test"), dict) else {}
    launch_log = read_tail(os.path.join(task_path, "launch.log"), diagnostics, boundary=task_path)

    if run_status:
        source = "run-status"
        if run_status.get("status") == "finished":
            reason = str(run_status.get("exit_reason", ""))
            status = reason if reason in EXIT_REASONS else "unknown"
            phase = "finished"
        elif run_status.get("status") == "running":
            status = "running" if pid_alive(run_status.get("pid")) else "interrupted"
            phase = str(run_status.get("phase") or "unknown") if status == "running" else "unknown"
        else:
            status, phase = "unknown", "unknown"
    else:
        source = "legacy"
        status, phase = legacy_status(task_path, state, launch_log, diagnostics)

    updated = ""
    if run_status:
        updated = str(run_status.get("updated_at") or "")
    if not updated:
        updated = str(state.get("updated") or "")
    if not updated:
        try:
            updated = datetime.datetime.fromtimestamp(os.path.getmtime(task_path)).isoformat(timespec="seconds")
        except OSError:
            pass

    result = {
        "slug": slug,
        "status": status,
        "phase": phase,
        "source": source,
        "run": (run_status or {}).get("run", state.get("runs")),
        "run_iteration": (run_status or {}).get("run_iteration"),
        "total_iterations": state.get("total_iterations", (run_status or {}).get("total_iterations", 0)),
        "open_items": latest_status.get("open_items"),
        "test_outcome": latest_test.get("outcome", "n/a"),
        "total_cost_usd": state.get("total_cost_usd", (run_status or {}).get("total_cost_usd", 0.0)),
        "cost_measurement": (run_status or {}).get(
            "cost_measurement", state.get("cost_measurement", "unknown")),
        "updated_at": updated,
        "spec": (run_status or {}).get("spec", ""),
        "project": (run_status or {}).get("project", ""),
        "diagnostics": diagnostics,
    }
    if details:
        result.update({
            "iterations": iterations,
            "iteration_count": history["count"],
            "history_truncated": history["truncated"],
            "carryover": read_tail(os.path.join(task_path, "carryover.md"), diagnostics, boundary=task_path),
            "log_tail": read_tail(os.path.join(task_path, "driver.log"), diagnostics, boundary=task_path),
        })
    return result


def collect_tasks(root):
    root_real = os.path.realpath(root)
    if not os.path.isdir(root_real):
        return []
    tasks = []
    try:
        names = sorted(os.listdir(root_real))
    except OSError:
        return []
    for name in names:
        if safe_task_path(root_real, name) is None:
            continue
        try:
            tasks.append(collect_task(root_real, name))
        except KeyError:
            continue
    priority = {"running": 0, "blocked": 1, "stalled": 2, "error": 3, "interrupted": 4}
    tasks.sort(key=lambda task: (priority.get(task["status"], 5), task["slug"]))
    return tasks


def make_handler(root):
    root = os.path.realpath(root)

    class Handler(BaseHTTPRequestHandler):
        server_version = "AutoloopDashboard/1"
        sys_version = ""

        def log_message(self, format_string, *args):
            return

        def security_headers(self):
            self.send_header("X-Autoloop-Root-Id", root_id(root))
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Referrer-Policy", "no-referrer")

        def send_bytes(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.security_headers()
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def send_json(self, status, value):
            try:
                body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
            except (TypeError, ValueError):
                status = 500
                body = b'{"error":"response serialization failed"}'
            self.send_bytes(status, body, "application/json; charset=utf-8")

        def send_error(self, code, message=None, explain=None):
            self.send_json(code, {"error": message or "요청을 처리할 수 없습니다"})

        def valid_host(self):
            values = self.headers.get_all("Host", [])
            if len(values) != 1:
                return False
            try:
                parsed = urlsplit("//" + values[0])
                parsed.port
            except ValueError:
                return False
            return (parsed.username is None and parsed.password is None
                    and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
                    and parsed.path == "")

        def require_local_host(self):
            if self.valid_host():
                return True
            self.send_json(403, {"error": "loopback Host만 허용됩니다"})
            return False

        def do_GET(self):
            if not self.require_local_host():
                return
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self.send_bytes(200, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
                return
            if parsed.path == "/api/tasks":
                self.send_json(200, {"tasks": collect_tasks(root), "generated_at": now_iso()})
                return
            prefix = "/api/tasks/"
            if parsed.path.startswith(prefix):
                slug = unquote(parsed.path[len(prefix):])
                try:
                    self.send_json(200, collect_task(root, slug, details=True))
                except KeyError:
                    self.send_json(404, {"error": "작업을 찾을 수 없습니다"})
                return
            self.send_json(404, {"error": "경로를 찾을 수 없습니다"})

        def do_HEAD(self):
            self.do_GET()

        def mutation_rejected(self):
            if not self.require_local_host():
                return
            self.send_json(405, {"error": "읽기 전용 대시보드입니다"})

        do_POST = mutation_rejected
        do_PUT = mutation_rejected
        do_PATCH = mutation_rejected
        do_DELETE = mutation_rejected
        do_OPTIONS = mutation_rejected

    return Handler


def make_server(root, port=8765):
    return ThreadingHTTPServer((LOOPBACK, port), make_handler(root))


def main(argv=None):
    parser = argparse.ArgumentParser(description="autoloop local read-only progress dashboard")
    parser.add_argument("--root", default="_workspace/autoloop", help="autoloop work directory root")
    parser.add_argument("--port", type=int, default=8765, help="loopback HTTP port (0 selects a free port)")
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    server = make_server(os.path.abspath(args.root), port=args.port)
    url = "http://%s:%d" % (LOOPBACK, server.server_port)
    print("[autoloop dashboard] %s (root: %s, read-only)" % (url, os.path.abspath(args.root)))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
