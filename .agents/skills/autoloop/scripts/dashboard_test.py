#!/usr/bin/env python3
"""autoloop dashboard regression tests.

Runs only against temporary directories and a loopback ephemeral HTTP server.
"""
import http.client
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

import dashboard  # noqa: E402


class DashboardTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="autoloop-dashboard-test-")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def task(self, slug="sample"):
        path = os.path.join(self.tmp, slug)
        os.makedirs(os.path.join(path, "iters"), exist_ok=True)
        return path

    @staticmethod
    def write_json(path, value):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False)

    @staticmethod
    def write_text(path, value):
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)

    def write_run(self, task, status, updated_at, pid=None, exit_reason=""):
        self.write_json(os.path.join(task, "run-status.json"), {
            "schema_version": 1,
            "status": "running" if status == "running" else "finished",
            "phase": "dispatching" if status == "running" else "finished",
            "exit_reason": exit_reason or ("" if status == "running" else status),
            "run": 1,
            "run_iteration": 1,
            "total_iterations": 1,
            "cost_measurement": "full",
            "pid": os.getpid() if pid is None else pid,
            "updated_at": updated_at,
        })


class TestCollection(DashboardTestBase):
    def test_attention_sorting_precedes_tracking_and_is_newest_first(self):
        now = "2026-08-19T12:00:00"
        fixtures = [
            ("structured-done", "done", "2026-08-19T11:59:59", True),
            ("unstructured-blocked", "blocked", "2026-08-19T11:40:00", False),
            ("structured-running", "running", "2026-08-19T11:59:58", True),
            ("unstructured-interrupted", "running", "2026-08-19T11:59:57", False),
            ("structured-stale", "running", "2026-08-19T11:59:29", True),
        ]
        for slug, status, updated, structured in fixtures:
            task = self.task(slug)
            self.write_run(task, status, updated,
                           pid=99999999 if slug == "unstructured-interrupted" else None)
            if structured:
                self.write_json(os.path.join(task, "orchestration.json"), {
                    "schema_version": 1, "orchestrate": {}, "tasks": []})
        with mock.patch.object(dashboard, "now_datetime",
                               return_value=dashboard.parse_timestamp(now)):
            values = dashboard.collect_tasks(self.tmp)
        self.assertEqual([item["slug"] for item in values], [
            "unstructured-interrupted", "unstructured-blocked", "structured-stale",
            "structured-running", "structured-done",
        ])
        self.assertEqual(values[0]["tracking"], "unstructured")
        self.assertEqual(values[2]["attention_reason"], "갱신 지연")

    def test_stale_boundary_is_inclusive_and_never_changes_running_status(self):
        task = self.task()
        self.write_run(task, "running", "2026-08-19T11:59:30")
        with mock.patch.object(dashboard, "now_datetime",
                               return_value=dashboard.parse_timestamp("2026-08-19T12:00:00")):
            at_boundary = dashboard.collect_task(self.tmp, "sample")
        self.assertTrue(at_boundary["stale"])
        self.assertEqual(at_boundary["status"], "running")
        self.write_run(task, "running", "2026-08-19T11:59:31")
        with mock.patch.object(dashboard, "now_datetime",
                               return_value=dashboard.parse_timestamp("2026-08-19T12:00:00")):
            before = dashboard.collect_task(self.tmp, "sample")
        self.assertFalse(before["stale"])

    def test_tracking_and_demo_provenance_are_explicit_only(self):
        task = self.task("demo-looking-name")
        value = dashboard.collect_task(self.tmp, "demo-looking-name")
        self.assertEqual(value["tracking"], "unstructured")
        self.assertEqual(value["provenance"], "recorded")
        self.write_json(os.path.join(task, "orchestration.json"), {
            "schema_version": 1, "orchestrate": {}, "tasks": []})
        self.write_json(os.path.join(task, "dashboard-meta.json"), {
            "schema_version": 1, "provenance": "demo"})
        value = dashboard.collect_task(self.tmp, "demo-looking-name")
        self.assertEqual(value["source"], "legacy")
        self.assertEqual(value["tracking"], "structured")
        self.assertEqual(value["provenance"], "demo")

    def test_invalid_dashboard_metadata_never_promotes_demo(self):
        task = self.task()
        cases = [
            {"schema_version": 2, "provenance": "demo"},
            {"schema_version": 1, "provenance": "synthetic"},
            {"schema_version": 1, "provenance": "demo", "extra": True},
        ]
        for payload in cases:
            self.write_json(os.path.join(task, "dashboard-meta.json"), payload)
            value = dashboard.collect_task(self.tmp, "sample")
            self.assertEqual(value["provenance"], "recorded")
            self.assertIn("dashboard-meta.json", " ".join(value["diagnostics"]))
        self.write_text(os.path.join(task, "dashboard-meta.json"), "{" + "x" * 20000)
        value = dashboard.collect_task(self.tmp, "sample")
        self.assertEqual(value["provenance"], "recorded")
        self.assertIn("크기", " ".join(value["diagnostics"]))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unavailable")
    def test_dashboard_metadata_symlink_is_rejected(self):
        task = self.task()
        outside = os.path.join(self.tmp, "outside-meta.json")
        self.write_json(outside, {"schema_version": 1, "provenance": "demo"})
        os.symlink(outside, os.path.join(task, "dashboard-meta.json"))
        value = dashboard.collect_task(self.tmp, "sample")
        self.assertEqual(value["provenance"], "recorded")
        self.assertIn("심볼릭 링크", " ".join(value["diagnostics"]))

    def test_coordination_timeline_is_bounded_sanitized_and_chronological(self):
        task = self.task()
        events = [
            {"ts": "2026-08-19T12:00:02", "event": "task_dispatch", "wave": 2,
             "task_id": "T2", "agent": "a2", "depends_on": ["T1"],
             "evidence": "do not render as instructions", "unknown": "DROP"},
            {"ts": "2026-08-19T12:00:01", "event": "task_complete", "wave": 1,
             "task_id": "T1", "agent": "a1", "evidence": "green"},
        ]
        self.write_text(os.path.join(task, "team-log.jsonl"),
                        "{broken\n" + "\n".join(json.dumps(item) for item in events) + "\n")
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertEqual([item["event"] for item in value["events"]],
                         ["task_complete", "task_dispatch"])
        self.assertNotIn("unknown", value["events"][1])
        self.assertEqual(value["event_diagnostics"]["malformed_lines"], 1)
        self.assertIn("tail_line", value["event_diagnostics"]["locations"][0])

    def test_coordination_event_count_and_bytes_are_bounded(self):
        task = self.task()
        lines = []
        for number in range(dashboard.MAX_TEAM_EVENTS + 20):
            lines.append(json.dumps({"ts": "2026-08-19T12:00:%02d" % (number % 60),
                                     "event": "task_complete", "task_id": "T%d" % number,
                                     "evidence": "x" * 200}))
        self.write_text(os.path.join(task, "team-log.jsonl"), "\n".join(lines) + "\n")
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertLessEqual(len(value["events"]), dashboard.MAX_TEAM_EVENTS)
        self.assertTrue(value["events_truncated"])

    def test_dag_diagnostics_and_readiness_are_not_disguised_as_a_graph(self):
        task = self.task()
        self.write_json(os.path.join(task, "orchestration.json"), {
            "schema_version": 1, "orchestrate": {"agent_budget": 1},
            "tasks": [
                {"id": "T1", "status": "pending", "depends_on": ["T2"]},
                {"id": "T2", "status": "pending", "depends_on": ["T1"]},
                {"id": "T3", "status": "pending", "depends_on": ["MISSING"]},
            ],
        })
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertFalse(value["dag"]["valid"])
        self.assertEqual(value["dag"]["edges"], [])
        self.assertIn("cycle", " ".join(value["dag"]["diagnostics"]).lower())
        self.assertIn("MISSING", " ".join(value["dag"]["diagnostics"]))
        self.assertFalse(value["tasks"][0]["ready"])
        self.assertTrue(value["tasks"][0]["blocked_reason"])

    def test_structured_projection_preserves_role_wave_commits_and_fan_in(self):
        task = self.task()
        self.write_json(os.path.join(task, "orchestration.json"), {
            "schema_version": 1,
            "orchestrate": {"agent_budget": 2},
            "tasks": [{
                "id": "T1", "owner": "implementer", "status": "complete", "depends_on": [],
                "requested_engine": "codex", "effective_engine": "claude",
                "engine_fallback": "recorded fallback", "base_commit": "base1",
                "task_commit": "task1", "agent": {"id": "a1", "status": "complete",
                "started_at": "start", "finished_at": "finish"},
            }],
            "dispatches": [{"wave": 3, "task_ids": ["T1"], "fallback": "budget limited"}],
            "integrations": [{"wave": 3, "task_ids": ["T1"], "ok": True,
                "commit": "integration1", "target_fast_forward": True,
                "status": "integrated", "cleanup": "retained_for_verified_cleanup"}],
            "worktrees": [{"kind": "writer", "wave": 3, "task_id": "T1",
                "path": "/tmp/writer", "base_commit": "base1", "commit": "task1",
                "status": "integrated", "cleanup": "retained_for_verified_cleanup"}],
        })
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertEqual(value["tasks"][0]["wave"], 3)
        self.assertEqual(value["agents"][0]["role"], "implementer")
        self.assertEqual(value["agents"][0]["requested_engine"], "codex")
        self.assertEqual(value["worktrees"][0]["commit"], "task1")
        self.assertTrue(value["integrations"][0]["target_fast_forward"])
    def test_orchestration_projection_exposes_tasks_agents_and_dependencies(self):
        task = self.task()
        self.write_json(os.path.join(task, "orchestration.json"), {
            "schema_version": 1,
            "contract_version": "autoloop-orchestrate-v1",
            "criteria": ["C1", "C2"],
            "orchestrate": {"verdict": "team", "agent_budget": 2, "reason": "parallel"},
            "tasks": [{
                "id": "T2", "criterion_ids": ["C2"], "deliverable": "second",
                "depends_on": ["T1"], "owner": "implementer", "mode": "worker",
                "mutability": "write", "expected_evidence": "test", "observed_evidence": "",
                "status": "running", "blocker": "", "worktree": "writer-T2",
                "requested_engine": "codex", "effective_engine": "claude",
                "engine_fallback": "Codex writers require the Claude gate",
                "agent": {"id": "agent-T2", "status": "running",
                          "started_at": "2026-08-19T12:00:00", "finished_at": ""},
            }],
            "dispatches": [{"wave": 1, "task_ids": ["T2"],
                            "started_at": "2026-08-19T12:00:00",
                            "fallback": "budget limited"}],
            "integrations": [{"wave": 1, "task_ids": ["T2"], "ok": False,
                              "error": "conflict", "failure_stage": "apply", "integration_worktree": "integration-1",
                              "cleanup": "retained_for_verified_cleanup"}],
            "worktrees": [{"kind": "writer", "wave": 1, "task_id": "T2",
                           "path": "writer-T2", "base_commit": "abc", "status": "retained_failed",
                           "cleanup": "retained_for_verified_cleanup"}],
        })
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertEqual(value["task_counts"]["running"], 1)
        self.assertEqual(value["tasks"][0]["depends_on"], ["T1"])
        self.assertEqual(value["agents"][0]["id"], "agent-T2")
        self.assertEqual(value["tasks"][0]["effective_engine"], "claude")
        self.assertIn("Claude gate", value["tasks"][0]["engine_fallback"])
        self.assertEqual(value["orchestrate_verdict"], "team")
        self.assertEqual(value["agent_counts"]["running"], 1)
        self.assertEqual(value["dispatches"][0]["wave"], 1)
        self.assertEqual(value["dispatches"][0]["task_ids"], ["T2"])
        self.assertEqual(value["dispatches"][0]["fallback"], "budget limited")
        self.assertEqual(value["integrations"][0]["error"], "conflict")
        self.assertEqual(value["integrations"][0]["failure_stage"], "apply")
        self.assertEqual(value["worktrees"][0]["status"], "retained_failed")

    def test_latest_iteration_is_the_display_authority(self):
        task = self.task()
        self.write_json(os.path.join(task, "state.json"), {
            "runs": 1, "total_iterations": 2, "total_cost_usd": 4.2,
            "prev_open": 5, "last_exit_reason": "done", "updated": "2026-08-19T10:00:00",
        })
        self.write_json(os.path.join(task, "run-status.json"), {
            "schema_version": 1, "status": "finished", "phase": "finished",
            "exit_reason": "done", "run": 1, "run_iteration": 2,
            "total_iterations": 2, "cost_measurement": "full", "pid": 123,
            "updated_at": "2026-08-19T10:00:01", "spec": "/tmp/spec.md",
            "project": "/tmp/project",
        })
        self.write_json(os.path.join(task, "iters", "iter-2.json"), {
            "iter": 2,
            "status": {"status": "done", "open_items": 0, "note": "complete", "parsed": True},
            "test": {"outcome": "green", "tail": "12 passed"},
            "cost": 1.2,
        })

        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertEqual(value["open_items"], 0)
        self.assertEqual(value["test_outcome"], "green")
        self.assertEqual(value["status"], "done")
        self.assertEqual(value["total_iterations"], 2)
        self.assertEqual(value["iterations"][0]["iter"], 2)

    def test_running_status_requires_a_live_pid(self):
        task = self.task()
        base = {
            "schema_version": 1, "status": "running", "phase": "implementing",
            "exit_reason": "", "run": 2, "run_iteration": 1, "total_iterations": 3,
            "cost_measurement": "unavailable", "updated_at": "2026-08-19T10:00:00",
        }
        self.write_json(os.path.join(task, "run-status.json"), dict(base, pid=os.getpid()))
        self.assertEqual(dashboard.collect_task(self.tmp, "sample")["status"], "running")

        self.write_json(os.path.join(task, "run-status.json"), dict(base, pid=99999999))
        self.assertEqual(dashboard.collect_task(self.tmp, "sample")["status"], "interrupted")

    def test_legacy_launch_log_and_stale_pid_are_handled(self):
        task = self.task()
        with open(os.path.join(task, "launch.log"), "w", encoding="utf-8") as f:
            f.write("[autoloop] 종료: blocked (로그: /tmp/sample/driver.log)\n")
        with open(os.path.join(task, "driver.pid"), "w", encoding="utf-8") as f:
            f.write("99999999\n")
        value = dashboard.collect_task(self.tmp, "sample")
        self.assertEqual(value["status"], "blocked")
        self.assertEqual(value["source"], "legacy")

    def test_corrupt_json_is_localized_to_diagnostics(self):
        broken = self.task("broken")
        healthy = self.task("healthy")
        with open(os.path.join(broken, "state.json"), "w", encoding="utf-8") as f:
            f.write("{not-json")
        self.write_json(os.path.join(healthy, "state.json"), {
            "runs": 1, "total_iterations": 1, "total_cost_usd": 1.0,
            "last_exit_reason": "done", "updated": "2026-08-19T10:00:00",
        })
        values = {item["slug"]: item for item in dashboard.collect_tasks(self.tmp)}
        self.assertIn("state.json", " ".join(values["broken"]["diagnostics"]))
        self.assertEqual(values["healthy"]["status"], "done")

    def test_nonfinite_json_is_localized_and_response_safe(self):
        broken = self.task("broken")
        self.task("healthy")
        with open(os.path.join(broken, "state.json"), "w", encoding="utf-8") as f:
            f.write('{"runs": 1, "total_cost_usd": NaN}')
        values = {item["slug"]: item for item in dashboard.collect_tasks(self.tmp)}
        self.assertIn("state.json", " ".join(values["broken"]["diagnostics"]))
        encoded = json.dumps({"tasks": list(values.values())}, allow_nan=False)
        json.loads(encoded, parse_constant=lambda value: self.fail("bare %s in response" % value))

    def test_corrupt_newest_iteration_does_not_promote_stale_values(self):
        task = self.task()
        self.write_json(os.path.join(task, "iters", "iter-1.json"), {
            "iter": 1,
            "status": {"status": "continue", "open_items": 7},
            "test": {"outcome": "red"},
        })
        with open(os.path.join(task, "iters", "iter-2.json"), "w", encoding="utf-8") as f:
            f.write("{broken")
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertIsNone(value["open_items"])
        self.assertEqual(value["test_outcome"], "n/a")
        self.assertIn("iter-2.json", " ".join(value["diagnostics"]))
        self.assertEqual(value["iterations"][0]["iter"], 1)

    def test_unknown_cost_is_not_reported_as_free(self):
        task = self.task()
        self.write_json(os.path.join(task, "state.json"), {
            "runs": 1, "total_iterations": 1, "total_cost_usd": 0.0,
            "last_exit_reason": "done", "updated": "2026-08-19T10:00:00",
        })
        value = dashboard.collect_task(self.tmp, "sample")
        self.assertEqual(value["cost_measurement"], "unknown")

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unavailable")
    def test_symlink_outside_the_workspace_is_not_discovered(self):
        outside = tempfile.mkdtemp(prefix="autoloop-dashboard-outside-")
        self.addCleanup(shutil.rmtree, outside, True)
        os.symlink(outside, os.path.join(self.tmp, "escape"))
        self.assertEqual(dashboard.collect_tasks(self.tmp), [])

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unavailable")
    def test_artifact_symlink_outside_task_is_not_read(self):
        task = self.task()
        outside = os.path.join(self.tmp, "outside.log")
        outside_state = os.path.join(self.tmp, "outside-state.json")
        with open(outside, "w", encoding="utf-8") as f:
            f.write("OUTSIDE-ROOT-SENTINEL")
        self.write_json(outside_state, {"runs": 999, "last_exit_reason": "done"})
        os.symlink(outside, os.path.join(task, "driver.log"))
        os.symlink(outside_state, os.path.join(task, "state.json"))
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertEqual(value["log_tail"], "")
        self.assertNotEqual(value["run"], 999)
        self.assertIn("심볼릭 링크", " ".join(value["diagnostics"]))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlink unavailable")
    def test_symlinked_iterations_directory_is_not_read(self):
        task = self.task()
        outside = tempfile.mkdtemp(prefix="autoloop-dashboard-iters-")
        self.addCleanup(shutil.rmtree, outside, True)
        self.write_json(os.path.join(outside, "iter-99.json"), {"iter": 99})
        shutil.rmtree(os.path.join(task, "iters"))
        os.symlink(outside, os.path.join(task, "iters"))
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertEqual(value["iterations"], [])
        self.assertIn("심볼릭 링크", " ".join(value["diagnostics"]))

    def test_detail_iteration_history_is_bounded_and_marked(self):
        task = self.task()
        for number in range(1, dashboard.MAX_DETAIL_ITERATIONS + 4):
            self.write_json(os.path.join(task, "iters", "iter-%d.json" % number), {
                "iter": number, "status": {"open_items": number}, "test": {"outcome": "green"},
            })
        value = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertEqual(len(value["iterations"]), dashboard.MAX_DETAIL_ITERATIONS)
        self.assertTrue(value["history_truncated"])
        self.assertEqual(value["iteration_count"], dashboard.MAX_DETAIL_ITERATIONS + 3)

    def test_summary_reads_only_the_highest_iteration(self):
        task = self.task()
        with open(os.path.join(task, "iters", "iter-1.json"), "w", encoding="utf-8") as f:
            f.write("{broken")
        self.write_json(os.path.join(task, "iters", "iter-2.json"), {
            "iter": 2, "status": {"open_items": 0}, "test": {"outcome": "green"},
        })
        summary = dashboard.collect_task(self.tmp, "sample")
        self.assertEqual(summary["open_items"], 0)
        self.assertNotIn("iter-1.json", " ".join(summary["diagnostics"]))
        detail = dashboard.collect_task(self.tmp, "sample", details=True)
        self.assertIn("iter-1.json", " ".join(detail["diagnostics"]))


class TestHttp(DashboardTestBase):
    def setUp(self):
        super().setUp()
        task = self.task()
        self.write_json(os.path.join(task, "state.json"), {
            "runs": 1, "total_iterations": 1, "total_cost_usd": 1.5,
            "last_exit_reason": "done", "updated": "2026-08-19T10:00:00",
        })
        self.server = dashboard.make_server(self.tmp, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    def request(self, method, path, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        if host is None:
            conn.request(method, path)
        else:
            conn.putrequest(method, path, skip_host=True)
            conn.putheader("Host", host)
            conn.endheaders()
        response = conn.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        conn.close()
        return response.status, headers, body

    def test_loopback_server_serves_list_and_detail_json(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, body = self.request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["tasks"][0]["slug"], "sample")
        self.assertIn("application/json", headers["Content-Type"])
        self.assertEqual(headers["X-Autoloop-Root-Id"], dashboard.root_id(self.tmp))

        status, _, body = self.request("GET", "/api/tasks/sample")
        self.assertEqual(status, 200)
        self.assertIn("iterations", json.loads(body))

    def test_fixed_built_assets_have_exact_types_and_unknown_assets_are_rejected(self):
        for path, expected in (("/", "text/html"), ("/assets/app.js", "text/javascript"),
                               ("/assets/app.css", "text/css")):
            status, headers, body = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertIn(expected, headers["Content-Type"])
            self.assertGreater(len(body), 0)
        self.assertEqual(self.request("GET", "/assets/../dashboard.py")[0], 404)

    def test_mutation_and_path_traversal_are_rejected(self):
        self.assertEqual(self.request("POST", "/api/tasks")[0], 405)
        self.assertEqual(self.request("GET", "/api/tasks/%2e%2e")[0], 404)
        self.assertEqual(self.request("GET", "/api/tasks/missing")[0], 404)

    def test_non_loopback_host_is_rejected(self):
        self.assertEqual(self.request("GET", "/api/tasks", "attacker.example")[0], 403)
        self.assertEqual(self.request("GET", "/api/tasks", "127.0.0.1:%d" % self.server.server_port)[0], 200)

    def test_nonfinite_artifact_keeps_list_response_valid_json(self):
        with open(os.path.join(self.tmp, "sample", "state.json"), "w", encoding="utf-8") as f:
            f.write('{"runs": 1, "total_cost_usd": Infinity}')
        status, _, body = self.request("GET", "/api/tasks")
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"),
                          parse_constant=lambda value: self.fail("bare %s in response" % value))
        self.assertIn("state.json", " ".join(data["tasks"][0]["diagnostics"]))

    def test_security_headers_are_set(self):
        for method, path, expected in (("GET", "/", 200), ("GET", "/api/tasks", 200),
                                       ("GET", "/missing", 404), ("POST", "/api/tasks", 405),
                                       ("OPTIONS", "/api/tasks", 405)):
            status, headers, _ = self.request(method, path)
            self.assertEqual(status, expected)
            self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("no-store", headers["Cache-Control"])


class TestStaticAssets(unittest.TestCase):
    def test_only_fixed_built_asset_paths_are_declared_with_exact_mime(self):
        self.assertEqual(set(dashboard.STATIC_ASSETS), {"/", "/assets/app.js", "/assets/app.css"})
        self.assertEqual(dashboard.STATIC_ASSETS["/assets/app.js"][1], "text/javascript; charset=utf-8")
        self.assertEqual(dashboard.STATIC_ASSETS["/assets/app.css"][1], "text/css; charset=utf-8")

    def test_asset_reader_rejects_traversal_and_symlink(self):
        self.assertIsNone(dashboard.dashboard_dist_path("../index.html"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
