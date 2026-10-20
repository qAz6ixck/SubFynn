# Feature 2 Boundaries: Python Engine Sidecar IPC
# Verifies large payloads, malformed JSON lines, rapid bursts, and ID edge cases.

import sys
import json
import time
import subprocess
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis

class TestBoundary02SidecarIPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.sidecar_path = cls.root / "engine_sidecar.py"
        if not cls.sidecar_path.exists():
            raise unittest.SkipTest("engine_sidecar.py not found")

    def _spawn_sidecar(self) -> subprocess.Popen:
        flags = 0x08000000 if sys.platform == "win32" else 0
        return subprocess.Popen(
            [sys.executable, str(self.sidecar_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=flags
        )

    def test_extreme_large_ndjson_line(self):
        """Verifies sidecar processes large multi-segment payload (~1MB) without buffer truncation."""
        proc = self._spawn_sidecar()
        try:
            # Generate 1500 segments
            large_segments = [
                {
                    "id": i,
                    "start": float(i),
                    "end": float(i + 1),
                    "text": f"Line {i} with long descriptive subtitle payload to simulate extreme buffer size",
                    "thai_text": f"ข้อความทดสอบซับไตเติลที่ {i} เพื่อทดสอบความยาวข้อมูลขนาดใหญ่มาก"
                }
                for i in range(1, 1501)
            ]
            req = {
                "id": 8888,
                "method": "engine.shift_time",
                "params": {"segments": large_segments, "offset_seconds": 1.0}
            }
            line = json.dumps(req, ensure_ascii=False)
            proc.stdin.write(line + "\n")
            proc.stdin.flush()

            resp_line = proc.stdout.readline()
            self.assertTrue(resp_line)
            res = json.loads(resp_line)
            self.assertEqual(res.get("id"), 8888)
            self.assertIsNone(res.get("error"))
            self.assertEqual(len(res["result"]["segments"]), 1500)
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_malformed_json_syntax_error(self):
        """Verifies sending corrupt JSON string yields parse error (-32700) without crashing process."""
        proc = self._spawn_sidecar()
        try:
            # Corrupted truncated JSON
            proc.stdin.write('{"id": 123, "method": "engine.ping", "params": { BROKEN JSON\n')
            proc.stdin.flush()

            resp_line = proc.stdout.readline()
            self.assertTrue(resp_line)
            res = json.loads(resp_line)
            self.assertIsNotNone(res.get("error"))
            self.assertIn(res["error"].get("code"), [-32700, -32600])

            # Confirm process remains alive
            proc.stdin.write(json.dumps({"id": 124, "method": "engine.ping", "params": {}}) + "\n")
            proc.stdin.flush()
            alive_line = proc.stdout.readline()
            alive_res = json.loads(alive_line)
            self.assertEqual(alive_res.get("id"), 124)
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_empty_line_and_whitespace_graceful(self):
        """Verifies sending empty lines or whitespace-only lines is ignored safely."""
        proc = self._spawn_sidecar()
        try:
            proc.stdin.write("\n")
            proc.stdin.write("   \n")
            proc.stdin.write("\t\n")
            proc.stdin.flush()

            # Now send valid ping
            proc.stdin.write(json.dumps({"id": 55, "method": "engine.ping", "params": {}}) + "\n")
            proc.stdin.flush()

            resp_line = proc.stdout.readline()
            res = json.loads(resp_line)
            self.assertEqual(res.get("id"), 55)
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_rapid_burst_consecutive_requests(self):
        """Sends 25 rapid requests in immediate succession and verifies all responses received."""
        proc = self._spawn_sidecar()
        try:
            count = 25
            for i in range(count):
                proc.stdin.write(json.dumps({"id": i, "method": "engine.ping", "params": {}}) + "\n")
            proc.stdin.flush()

            received_ids = []
            for _ in range(count):
                line = proc.stdout.readline()
                res = json.loads(line)
                received_ids.append(res.get("id"))

            self.assertEqual(sorted(received_ids), list(range(count)))
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_various_request_id_types(self):
        """Verifies handling of string IDs, negative IDs, and zero ID."""
        proc = self._spawn_sidecar()
        try:
            test_ids = ["req-uuid-12345", -42, 0, "simple_id"]
            for test_id in test_ids:
                proc.stdin.write(json.dumps({"id": test_id, "method": "engine.ping", "params": {}}) + "\n")
                proc.stdin.flush()
                resp = json.loads(proc.stdout.readline())
                self.assertEqual(resp.get("id"), test_id)
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_missing_params_handled_safely(self):
        """Verifies requests with omitted or null params field execute without exception."""
        proc = self._spawn_sidecar()
        try:
            req1 = {"id": 1, "method": "engine.ping"}
            req2 = {"id": 2, "method": "engine.ping", "params": None}
            proc.stdin.write(json.dumps(req1) + "\n" + json.dumps(req2) + "\n")
            proc.stdin.flush()

            res1 = json.loads(proc.stdout.readline())
            res2 = json.loads(proc.stdout.readline())
            self.assertEqual(res1.get("result", {}).get("status"), "ready")
            self.assertEqual(res2.get("result", {}).get("status"), "ready")
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

if __name__ == "__main__":
    unittest.main()
