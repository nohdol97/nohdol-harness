#!/usr/bin/env python3
"""autoloop dashboard regression tests.

Runs only against temporary directories and a loopback ephemeral HTTP server.
"""
import http.client
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest

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


class TestCollection(DashboardTestBase):
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
                              "error": "conflict", "integration_worktree": "integration-1",
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


class TestHtmlContract(unittest.TestCase):
    def test_dynamic_content_uses_text_content_only(self):
        self.assertIn("textContent", dashboard.INDEX_HTML)
        self.assertNotIn("innerHTML", dashboard.INDEX_HTML)
        self.assertIn("측정 안 됨", dashboard.INDEX_HTML)
        self.assertIn("사용자 확인 필요", dashboard.INDEX_HTML)
        self.assertIn("병렬 dispatch / fallback", dashboard.INDEX_HTML)
        self.assertIn("writer fan-in / worktree", dashboard.INDEX_HTML)

    def test_refresh_is_pausable_focus_safe_and_truthful(self):
        self.assertIn("자동 갱신 일시정지", dashboard.INDEX_HTML)
        self.assertIn("preventScroll", dashboard.INDEX_HTML)
        self.assertIn("aria-pressed", dashboard.INDEX_HTML)
        self.assertIn("iteration.cost_measurement", dashboard.INDEX_HTML)
        self.assertIn("작업이 목록에서 사라졌습니다", dashboard.INDEX_HTML)


if __name__ == "__main__":
    unittest.main(verbosity=2)
