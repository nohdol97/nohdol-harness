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
MAX_META_BYTES = 16 * 1024
MAX_TEAM_LOG_BYTES = 256 * 1024
MAX_TEAM_EVENTS = 200
MAX_DETAIL_ITERATIONS = 200
STALE_AFTER_SECONDS = 30
ITER_FILE = re.compile(r"^iter-(\d+)\.json$")
EXIT_LINE = re.compile(
    r"^\[autoloop\] 종료: (done|blocked|stalled|exhausted|stopped|cost|error)"
    r"(?: \(로그: .+\))?\s*$", re.MULTILINE)
EXIT_REASONS = {"done", "blocked", "stalled", "exhausted", "stopped", "cost", "error"}
TEAM_EVENTS = {"team_create", "task_dispatch", "task_complete", "task_failed",
               "integration_complete", "shutdown_request", "team_delete"}
STATIC_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/assets/app.js": ("assets/app.js", "text/javascript; charset=utf-8"),
    "/assets/app.css": ("assets/app.css", "text/css; charset=utf-8"),
}



def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def now_datetime():
    return datetime.datetime.now()


def parse_timestamp(value):
    """Parse an artifact timestamp into a comparable local-naive datetime."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


def freshness(updated_at):
    parsed = parse_timestamp(updated_at)
    if parsed is None:
        return {"age_seconds": None, "stale": False, "relative": "시각 미확인"}
    age = max(0, int((now_datetime() - parsed).total_seconds()))
    if age < 60:
        relative = "%d초 전" % age
    elif age < 3600:
        relative = "%d분 전" % (age // 60)
    elif age < 86400:
        relative = "%d시간 전" % (age // 3600)
    else:
        relative = "%d일 전" % (age // 86400)
    return {"age_seconds": age, "stale": age >= STALE_AFTER_SECONDS,
            "relative": relative}


def root_id(path):
    return hashlib.sha256(os.fsencode(os.path.realpath(path))).hexdigest()


def dashboard_dist_path(relative):
    """Return a regular, non-symlink committed dashboard asset or None."""
    dist = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "dashboard-ui", "dist"))
    candidate = os.path.join(dist, relative)
    try:
        if os.path.islink(candidate) or not os.path.isfile(candidate):
            return None
        if os.path.commonpath((dist, os.path.realpath(candidate))) != dist:
            return None
        return candidate
    except (OSError, ValueError):
        return None


def read_dashboard_asset(relative):
    path = dashboard_dist_path(relative)
    if path is None:
        return None
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


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


def read_json(path, diagnostics, boundary=None, limit=MAX_JSON_BYTES):
    if boundary is not None:
        path = confined_path(path, boundary, diagnostics)
        if path is None:
            return None
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as f:
            raw = f.read(limit + 1)
        if len(raw.encode("utf-8")) > limit:
            raise ValueError("크기 제한 %d bytes 초과" % limit)
        value = json.loads(raw, parse_constant=reject_nonfinite)
        if not isinstance(value, dict):
            raise ValueError("top level is not an object")
        ensure_finite(value)
        return value
    except (OSError, UnicodeError, ValueError, RecursionError) as e:
        diagnostics.append("%s 읽기 실패: %s" % (os.path.basename(path), e))
        return None


def artifact_exists(path, diagnostics, boundary):
    confined = confined_path(path, boundary, diagnostics)
    if confined is None or not os.path.exists(confined):
        return False
    if not os.path.isfile(confined):
        diagnostics.append("%s regular file 아님" % os.path.basename(path))
        return False
    return True


def dashboard_provenance(task_path, diagnostics):
    path = os.path.join(task_path, "dashboard-meta.json")
    if not artifact_exists(path, diagnostics, task_path):
        return "recorded"
    value = read_json(path, diagnostics, boundary=task_path, limit=MAX_META_BYTES)
    if value == {"schema_version": 1, "provenance": "demo"}:
        return "demo"
    diagnostics.append("dashboard-meta.json 스키마 또는 값 거부")
    return "recorded"


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


def coordination_events(task_path, diagnostics):
    """Read only the bounded tail of the append-only coordination audit."""
    path = os.path.join(task_path, "team-log.jsonl")
    path = confined_path(path, task_path, diagnostics)
    empty = {"events": [], "events_truncated": False,
             "event_diagnostics": {"malformed_lines": 0, "rejected_events": 0,
                                   "locations": []}}
    if path is None or not os.path.exists(path):
        return empty
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            offset = max(0, size - MAX_TEAM_LOG_BYTES)
            handle.seek(offset)
            raw = handle.read(MAX_TEAM_LOG_BYTES)
        byte_truncated = offset > 0
        if byte_truncated:
            split = raw.find(b"\n")
            raw = raw[split + 1:] if split >= 0 else b""
        lines = raw.decode("utf-8", errors="replace").splitlines()
    except OSError as exc:
        diagnostics.append("team-log.jsonl 읽기 실패: %s" % exc)
        return empty

    malformed = 0
    rejected = 0
    locations = []
    accepted = []

    def text(value, limit=1000):
        return str(value or "")[:limit]

    def string_list(value):
        if not isinstance(value, list):
            return []
        return [str(item)[:200] for item in value if isinstance(item, (str, int))]

    for index, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line, parse_constant=reject_nonfinite)
            ensure_finite(item)
            if not isinstance(item, dict):
                raise ValueError("event is not an object")
        except (ValueError, TypeError, RecursionError):
            malformed += 1
            if len(locations) < 20:
                locations.append({"tail_line": index})
            continue
        kind = item.get("event")
        if kind not in TEAM_EVENTS:
            rejected += 1
            continue
        event = {
            "ts": text(item.get("ts"), 100),
            "event": kind,
            "wave": item.get("wave") if isinstance(item.get("wave"), int) else None,
            "task_id": text(item.get("task_id"), 200),
            "task_ids": string_list(item.get("task_ids")),
            "agent": text(item.get("agent"), 200),
            "depends_on": string_list(item.get("depends_on")),
            "worktree": text(item.get("worktree")),
            "evidence": text(item.get("evidence")),
            "reason": text(item.get("reason") or item.get("error")),
            "ok": item.get("ok") if isinstance(item.get("ok"), bool) else None,
            "commit": text(item.get("commit"), 200),
        }
        accepted.append(event)
    count_truncated = len(accepted) > MAX_TEAM_EVENTS
    if count_truncated:
        accepted = accepted[-MAX_TEAM_EVENTS:]
    accepted.sort(key=lambda item: (parse_timestamp(item["ts"]) or datetime.datetime.min,
                                    item["event"], item["task_id"]))
    return {
        "events": accepted,
        "events_truncated": byte_truncated or count_truncated,
        "event_diagnostics": {"malformed_lines": malformed, "rejected_events": rejected,
                              "locations": locations},
    }


def dag_projection(tasks):
    ids = {task["id"] for task in tasks if task["id"]}
    diagnostics = []
    edges = []
    missing = set()
    dependencies = {task["id"]: task["depends_on"] for task in tasks if task["id"]}
    complete = {task["id"] for task in tasks if task["status"] == "complete"}
    for task in tasks:
        absent = [dependency for dependency in task["depends_on"] if dependency not in ids]
        missing.update(absent)
        unmet = [dependency for dependency in task["depends_on"] if dependency not in complete]
        task["ready"] = task["status"] == "pending" and not absent and not unmet
        task["blocked_reason"] = task["blocker"] or (
            "누락 dependency: %s" % ", ".join(absent) if absent else
            ("dependency 대기: %s" % ", ".join(unmet) if unmet else ""))
        for dependency in task["depends_on"]:
            if dependency in ids:
                edges.append({"from": dependency, "to": task["id"]})

    visiting = set()
    visited = set()
    cycle = False

    def visit(task_id):
        nonlocal cycle
        if task_id in visiting:
            cycle = True
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies.get(task_id, []):
            if dependency in ids:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in ids:
        visit(task_id)
    if missing:
        diagnostics.append("누락 dependency: %s" % ", ".join(sorted(missing)))
    if cycle:
        diagnostics.append("cycle detected")
    valid = not diagnostics
    return {"valid": valid, "edges": edges if valid else [], "diagnostics": diagnostics}


def orchestration_projection(task_path, diagnostics, details=False):
    """Expose only the bounded task/agent fields needed by the dashboard."""
    orchestration_path = os.path.join(task_path, "orchestration.json")
    tracking = ("structured" if artifact_exists(orchestration_path, diagnostics, task_path)
                else "unstructured")
    raw = read_json(orchestration_path, diagnostics, boundary=task_path) or {}
    raw_tasks = raw.get("tasks") if isinstance(raw.get("tasks"), list) else []
    raw_dispatches = raw.get("dispatches") if isinstance(raw.get("dispatches"), list) else []
    raw_integrations = raw.get("integrations") if isinstance(raw.get("integrations"), list) else []
    raw_worktrees = raw.get("worktrees") if isinstance(raw.get("worktrees"), list) else []
    tasks = []
    agents = []
    counts = {}
    agent_counts = {}
    orchestrate = raw.get("orchestrate") if isinstance(raw.get("orchestrate"), dict) else {}
    allowed_status = {"pending", "running", "complete", "blocked", "failed", "skipped"}
    def string_list(value):
        if isinstance(value, list):
            return [str(item) for item in value if isinstance(item, (str, int))]
        if isinstance(value, (str, int)) and str(value):
            return [str(value)]
        return []

    def bounded_text(value, limit=1000):
        return str(value or "")[:limit]

    dispatch_wave = {}
    for dispatch in raw_dispatches:
        if isinstance(dispatch, dict):
            for task_id in string_list(dispatch.get("task_ids", [])):
                dispatch_wave[task_id] = dispatch.get("wave")

    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "pending")
        if status not in allowed_status:
            status = "unknown"
        counts[status] = counts.get(status, 0) + 1
        agent = item.get("agent") if isinstance(item.get("agent"), dict) else {}
        task = {
            "id": str(item.get("id") or ""),
            "criterion_ids": string_list(item.get("criterion_ids", [])),
            "depends_on": string_list(item.get("depends_on", [])),
            "owner": str(item.get("owner") or ""),
            "mode": str(item.get("mode") or ""),
            "mutability": str(item.get("mutability") or ""),
            "status": status,
            "worktree": str(item.get("worktree") or agent.get("worktree") or ""),
            "agent_id": str(agent.get("id") or item.get("agent_id") or ""),
            "wave": dispatch_wave.get(str(item.get("id") or ""), item.get("wave")),
            "requested_engine": str(item.get("requested_engine") or ""),
            "effective_engine": str(item.get("effective_engine") or ""),
            "engine_fallback": bounded_text(item.get("engine_fallback")),
            "started_at": str(agent.get("started_at") or ""),
            "finished_at": str(agent.get("finished_at") or ""),
            "observed_evidence": string_list(item.get("observed_evidence", [])),
            "blocker": str(item.get("blocker") or ""),
            "base_commit": bounded_text(item.get("base_commit"), 200),
            "task_commit": bounded_text(item.get("task_commit") or item.get("commit"), 200),
        }
        tasks.append(task)
        if task["agent_id"]:
            agent_counts[status] = agent_counts.get(status, 0) + 1
            agents.append({
                "id": task["agent_id"],
                "task_id": task["id"],
                "status": status,
                "worktree": task["worktree"],
                "started_at": str(agent.get("started_at") or ""),
                "finished_at": str(agent.get("finished_at") or ""),
                "role": task["owner"],
                "wave": task["wave"],
                "requested_engine": task["requested_engine"],
                "effective_engine": task["effective_engine"],
                "engine_fallback": task["engine_fallback"],
            })
    dag = dag_projection(tasks)
    result = {
        "tracking": tracking,
        "orchestrate_verdict": str(orchestrate.get("verdict") or ""),
        "agent_budget": orchestrate.get("agent_budget"),
        "task_counts": counts,
        "agent_counts": agent_counts,
        "dag": dag,
    }
    if details:
        dispatches = []
        for item in raw_dispatches:
            if not isinstance(item, dict):
                continue
            dispatches.append({
                "wave": item.get("wave"),
                "task_ids": string_list(item.get("task_ids", [])),
                "started_at": bounded_text(item.get("started_at"), 100),
                "finished_at": bounded_text(item.get("finished_at"), 100),
                "fallback": bounded_text(item.get("fallback")),
            })
        integrations = []
        for item in raw_integrations:
            if not isinstance(item, dict):
                continue
            integrations.append({
                "wave": item.get("wave"),
                "task_ids": string_list(item.get("task_ids", [])),
                "ok": item.get("ok") is True,
                "commit": bounded_text(item.get("commit"), 200),
                "error": bounded_text(item.get("error")),
                "failure_stage": bounded_text(item.get("failure_stage"), 100),
                "integration_worktree": bounded_text(item.get("integration_worktree")),
                "cleanup": bounded_text(item.get("cleanup"), 200),
                "status": bounded_text(item.get("status"), 100),
                "target_fast_forward": item.get("target_fast_forward") is True,
                "base_commit": bounded_text(item.get("base_commit"), 200),
            })
        worktrees = []
        for item in raw_worktrees:
            if not isinstance(item, dict):
                continue
            worktrees.append({
                "kind": bounded_text(item.get("kind"), 100),
                "wave": item.get("wave"),
                "task_id": bounded_text(item.get("task_id"), 200),
                "path": bounded_text(item.get("path")),
                "base_commit": bounded_text(item.get("base_commit"), 200),
                "commit": bounded_text(item.get("commit") or item.get("task_commit"), 200),
                "status": bounded_text(item.get("status"), 100),
                "cleanup": bounded_text(item.get("cleanup"), 200),
            })
        result.update({"tasks": tasks, "agents": agents, "dispatches": dispatches,
                       "integrations": integrations, "worktrees": worktrees})
    return result


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
    orchestration = orchestration_projection(task_path, diagnostics, details=details)
    provenance = dashboard_provenance(task_path, diagnostics)

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

    current_freshness = freshness(updated)
    stale = status == "running" and current_freshness["stale"]
    attention_statuses = {"blocked", "stalled", "error", "interrupted", "stopped",
                          "exhausted", "cost"}
    if status in attention_statuses:
        attention_rank = 0
        attention_reason = "운영 확인 필요"
    elif stale:
        attention_rank = 1
        attention_reason = "갱신 지연"
    elif status == "running":
        attention_rank = 2
        attention_reason = "정상 실행"
    elif status == "done":
        attention_rank = 3
        attention_reason = "완료"
    else:
        attention_rank = 4
        attention_reason = "상태 확인 필요"

    result = {
        "slug": slug,
        "status": status,
        "phase": phase,
        "source": source,
        "provenance": provenance,
        "run": (run_status or {}).get("run", state.get("runs")),
        "run_iteration": (run_status or {}).get("run_iteration"),
        "total_iterations": state.get("total_iterations", (run_status or {}).get("total_iterations", 0)),
        "open_items": latest_status.get("open_items"),
        "test_outcome": latest_test.get("outcome", "n/a"),
        "total_cost_usd": state.get("total_cost_usd", (run_status or {}).get("total_cost_usd", 0.0)),
        "cost_measurement": (run_status or {}).get(
            "cost_measurement", state.get("cost_measurement", "unknown")),
        "updated_at": updated,
        "updated_relative": current_freshness["relative"],
        "age_seconds": current_freshness["age_seconds"],
        "stale": stale,
        "stale_after_seconds": STALE_AFTER_SECONDS,
        "attention_rank": attention_rank,
        "attention_reason": attention_reason,
        "spec": (run_status or {}).get("spec", ""),
        "project": (run_status or {}).get("project", ""),
        "diagnostics": diagnostics,
    }
    result.update(orchestration)
    if details:
        result.update({
            "iterations": iterations,
            "iteration_count": history["count"],
            "history_truncated": history["truncated"],
            "carryover": read_tail(os.path.join(task_path, "carryover.md"), diagnostics, boundary=task_path),
            "log_tail": read_tail(os.path.join(task_path, "driver.log"), diagnostics, boundary=task_path),
        })
        result.update(coordination_events(task_path, diagnostics))
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
    def key(task):
        updated = parse_timestamp(task["updated_at"]) or datetime.datetime.min
        return (task["attention_rank"], -updated.timestamp() if updated != datetime.datetime.min else 0,
                0 if task["tracking"] == "structured" else 1, task["slug"])

    tasks.sort(key=key)
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
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
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
            if parsed.path in STATIC_ASSETS:
                relative, content_type = STATIC_ASSETS[parsed.path]
                body = read_dashboard_asset(relative)
                if body is None:
                    self.send_json(503, {"error": "대시보드 build asset을 찾을 수 없습니다"})
                    return
                self.send_bytes(200, body, content_type)
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
