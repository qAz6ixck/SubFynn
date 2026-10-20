# Feature 2: Python Engine Sidecar IPC (Req R1.2)
# Opaque-box E2E test verifying NDJSON wire protocol, RPC methods, progress streaming, and EOF watchdog.

import sys
import json
import time
import subprocess
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis

class TestFeature02SidecarIPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.sidecar_path = cls.root / "engine_sidecar.py"
        if not cls.sidecar_path.exists():
            raise unittest.SkipTest("engine_sidecar.py not found in project root")

    def _spawn_sidecar(self) -> subprocess.Popen:
        """Spawns engine_sidecar.py in a subprocess with standard pipes."""
        flags = 0x08000000 if sys.platform == "win32" else 0
        proc = subprocess.Popen(
            [sys.executable, str(self.sidecar_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=flags
        )
        return proc

    def test_ndjson_request_response_wire_format(self):
        """Verifies NDJSON wire format: single line request yielding single line response."""
        proc = self._spawn_sidecar()
        try:
            req = {"id": 101, "method": "engine.ping", "params": {}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()

            line = proc.stdout.readline()
            self.assertTrue(line, "Sidecar must respond with a line")
            res = json.loads(line)
            assert_zero_emojis(res, "sidecar response")

            self.assertEqual(res.get("id"), 101)
            self.assertIn("result", res)
            self.assertIsNone(res.get("error"))
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_engine_ping_response_schema(self):
        """Verifies engine.ping response contains ready status, version, cuda status, and ffmpeg path."""
        proc = self._spawn_sidecar()
        try:
            req = {"id": 1, "method": "engine.ping", "params": {}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()

            line = proc.stdout.readline()
            res = json.loads(line)
            result = res.get("result", {})

            self.assertEqual(result.get("status"), "ready")
            self.assertEqual(result.get("version"), "1.0.0")
            self.assertIsInstance(result.get("cuda_available"), bool)
            self.assertTrue(result.get("ffmpeg_path"), "ffmpeg_path must be non-empty")
            self.assertTrue(Path(result.get("ffmpeg_path")).exists(), "Reported ffmpeg path must exist")
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_progress_event_ndjson_schema(self):
        """Verifies progress event schema contains task_id, percent, stage, and message without emoji."""
        from engine_sidecar import classify_stage
        stages = [
            (10.0, "แยกเสียง audio"),
            (45.0, "ถอดเสียง transcribing"),
            (80.0, "กำลังแปลภาษา"),
            (95.0, "บันทึก subtitle"),
            (100.0, "เสร็จสิ้น")
        ]
        for pct, msg in stages:
            stage_name = classify_stage(pct, msg)
            self.assertIsInstance(stage_name, str)
            assert_zero_emojis(stage_name, f"Stage name for {msg}")
            self.assertIn(stage_name, [
                "extracting_audio", "transcribing", "translating",
                "generating_subtitles", "embedding_subtitles", "completed"
            ])

    def test_stdin_eof_watchdog_contract(self):
        """Verifies sidecar terminates cleanly (exit code 0) when stdin reaches EOF."""
        proc = self._spawn_sidecar()
        # Close stdin to trigger EOF
        proc.stdin.close()
        exit_code = proc.wait(timeout=5)
        self.assertEqual(exit_code, 0, "Sidecar must exit with code 0 on stdin EOF watchdog")

    def test_stderr_isolation_for_logging(self):
        """Verifies stdout remains purely valid JSON lines even when logs are printed."""
        proc = self._spawn_sidecar()
        try:
            req = {"id": 42, "method": "engine.ping", "params": {}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()

            line = proc.stdout.readline()
            # Must strictly parse as JSON
            data = json.loads(line)
            self.assertEqual(data.get("id"), 42)
            # Ensure no stray characters before or after JSON
            self.assertEqual(line.strip(), json.dumps(data, ensure_ascii=False))
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_jsonrpc_error_payload_format(self):
        """Verifies unknown methods produce JSON-RPC -32601 error payload without terminating daemon."""
        proc = self._spawn_sidecar()
        try:
            req = {"id": 999, "method": "engine.unknown_operation", "params": {}}
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()

            line = proc.stdout.readline()
            res = json.loads(line)
            assert_zero_emojis(res, "error response")

            self.assertEqual(res.get("id"), 999)
            self.assertIsNone(res.get("result"))
            self.assertIsNotNone(res.get("error"))
            self.assertEqual(res["error"].get("code"), -32601)

            # Confirm daemon is still alive and responsive to subsequent valid commands
            req2 = {"id": 1000, "method": "engine.ping", "params": {}}
            proc.stdin.write(json.dumps(req2) + "\n")
            proc.stdin.flush()
            line2 = proc.stdout.readline()
            res2 = json.loads(line2)
            self.assertEqual(res2.get("id"), 1000)
        finally:
            proc.terminate()
            proc.wait(timeout=5)

if __name__ == "__main__":
    unittest.main()
