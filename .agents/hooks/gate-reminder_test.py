"""gate-reminder.py 회귀 테스트 — 스펙 docs/specs/2026-07-22-gate-reminder-hook.md.

훅을 서브프로세스로 실행해 실계약(stdin JSON → exit code·stderr·상태 파일)을
검증한다 — 등록 래퍼와 동일한 경계에서 테스트해야 settings.json 계약과
어긋나지 않는다. CLAUDE_PROJECT_DIR을 임시 디렉토리로 주입해 실제
_workspace를 오염시키지 않는다.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gate-reminder.py")
SID = "test-session-1"


def run_hook(mode, payload, project_dir):
    """payload: dict → stdin JSON, str → 원문 그대로(깨진 입력 테스트용)."""
    stdin = json.dumps(payload) if isinstance(payload, dict) else payload
    env = dict(os.environ, CLAUDE_PROJECT_DIR=project_dir)
    return subprocess.run(
        [sys.executable, HOOK, mode],
        input=stdin, capture_output=True, text=True, env=env, timeout=30,
    )


def state_path(project_dir, sid=SID):
    return os.path.join(project_dir, "_workspace", ".gate-reminder", sid)


def read_state(project_dir, sid=SID):
    try:
        with open(state_path(project_dir, sid), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def bash_event(command, sid=SID):
    return {"session_id": sid, "tool_name": "Bash", "tool_input": {"command": command}}


def edit_event(file_path, sid=SID, tool="Edit"):
    return {"session_id": sid, "tool_name": tool, "tool_input": {"file_path": file_path}}


class RecordTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_diag_command_arms_state(self):
        """R1: kubectl 등 진단 명령 → 상태 파일 'diag'."""
        r = run_hook("--record", bash_event("kubectl get pods -n live-editor"), self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(read_state(self.dir), "diag")

    def test_more_diag_patterns(self):
        """R1: argocd·docker logs·journalctl·helm status도 무장한다."""
        for i, cmd in enumerate(["argocd app get live-editor", "docker logs api-1",
                                 "journalctl -u kubelet", "helm status web"]):
            sid = f"s-{i}"
            run_hook("--record", bash_event(cmd, sid=sid), self.dir)
            self.assertEqual(read_state(self.dir, sid), "diag", cmd)

    def test_plain_command_does_not_arm(self):
        """R1: 비진단 명령은 상태를 만들지 않는다."""
        r = run_hook("--record", bash_event("ls -la && git status"), self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertIsNone(read_state(self.dir))

    def test_record_does_not_rearm_after_reminded(self):
        """R1: reminded 상태를 diag로 되돌리지 않는다 — 세션당 1회."""
        os.makedirs(os.path.dirname(state_path(self.dir)), exist_ok=True)
        with open(state_path(self.dir), "w", encoding="utf-8") as f:
            f.write("reminded")
        run_hook("--record", bash_event("kubectl get pods"), self.dir)
        self.assertEqual(read_state(self.dir), "reminded")

    def test_malformed_stdin_fails_open(self):
        """R4: 깨진 JSON·빈 입력 → exit 0."""
        for payload in ("{not json", ""):
            r = run_hook("--record", payload, self.dir)
            self.assertEqual(r.returncode, 0, repr(payload))


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def arm(self):
        run_hook("--record", bash_event("kubectl get pods"), self.dir)

    def test_no_state_allows(self):
        """R3: 진단 이력 없는 세션 → 통과."""
        r = run_hook("--check", edit_event("/repo/src/app.py"), self.dir)
        self.assertEqual(r.returncode, 0)

    def test_armed_product_edit_blocks_once(self):
        """R2: diag 상태 + 제품 코드 경로 → exit 2 + 게이트 지시 + reminded 전이."""
        self.arm()
        r = run_hook("--check", edit_event("/repo/src/app.py"), self.dir)
        self.assertEqual(r.returncode, 2)
        self.assertIn("gate-reminder", r.stderr)
        self.assertIn("orchestrate", r.stderr)
        self.assertEqual(read_state(self.dir), "reminded")

    def test_second_check_allows(self):
        """R2: 차단은 세션당 1회 — 재시도는 통과."""
        self.arm()
        run_hook("--check", edit_event("/repo/src/app.py"), self.dir)
        r = run_hook("--check", edit_event("/repo/src/app.py"), self.dir)
        self.assertEqual(r.returncode, 0)

    def test_workspace_path_excluded(self):
        """R3: _workspace 리포트 쓰기는 통과하고 상태를 소모하지 않는다."""
        self.arm()
        r = run_hook("--check", edit_event("/repo/_workspace/job/phase1_report.md", tool="Write"), self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(read_state(self.dir), "diag")

    def test_tmp_path_excluded(self):
        """R3: 시스템 임시 경로 쓰기는 통과하고 상태를 소모하지 않는다."""
        self.arm()
        r = run_hook("--check", edit_event("/tmp/claude-0/scratch/x.py", tool="Write"), self.dir)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(read_state(self.dir), "diag")

    def test_malformed_stdin_fails_open(self):
        """R4: 깨진 입력 → exit 0 (무장 상태여도 세션을 막지 않는다)."""
        self.arm()
        r = run_hook("--check", "{not json", self.dir)
        self.assertEqual(r.returncode, 0)

    def test_missing_session_id_fails_open(self):
        """R4: session_id 부재 → exit 0."""
        r = run_hook("--check", {"tool_name": "Edit", "tool_input": {"file_path": "/x.py"}}, self.dir)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
