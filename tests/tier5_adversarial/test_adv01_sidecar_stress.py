# SubFynn Tier 5 Adversarial Stress Test: Python Sidecar Daemon
# Strictly ZERO emojis permitted in code, assertions, and test output.

import sys
import json
import time
import queue
import threading
import subprocess
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.test_helpers import get_project_root, assert_zero_emojis


class TestAdversarial01SidecarStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.sidecar_path = cls.root / "engine_sidecar.py"
        if not cls.sidecar_path.is_file():
            raise unittest.SkipTest("engine_sidecar.py not found in project root")

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

    def _cleanup_proc(self, proc: subprocess.Popen):
        try:
            if proc.stdin and not proc.stdin.closed:
                proc.stdin.close()
        except Exception:
            pass
        try:
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
        except Exception:
            pass
        try:
            if proc.stderr and not proc.stderr.closed:
                proc.stderr.close()
        except Exception:
            pass
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass

    def test_adv01_rapid_requests_burst_200(self):
        """Adversarial rapid burst: 200 consecutive requests sent back-to-back."""
        proc = self._spawn_sidecar()
        try:
            req_count = 200
            start_time = time.perf_counter()

            # Dispatch 200 requests without waiting between sends
            for i in range(1, req_count + 1):
                payload = json.dumps({"id": i, "method": "engine.ping", "params": {}})
                proc.stdin.write(payload + "\n")
            proc.stdin.flush()

            # Read all 200 responses
            received_ids = []
            for _ in range(req_count):
                line = proc.stdout.readline()
                self.assertTrue(line, "Daemon stdout closed prematurely during rapid burst")
                data = json.loads(line)
                assert_zero_emojis(data, "rapid burst response")
                self.assertEqual(data.get("result", {}).get("status"), "ready")
                received_ids.append(data.get("id"))

            elapsed = time.perf_counter() - start_time
            self.assertEqual(len(received_ids), req_count)
            self.assertEqual(sorted(received_ids), list(range(1, req_count + 1)))

            # Throughput assertion: 200 requests should complete in reasonable time (< 15 seconds)
            self.assertLess(elapsed, 15.0, f"200 rapid requests took {elapsed:.2f}s, expected < 15s")
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_adv02_huge_input_payload_10000_segments(self):
        """Adversarial huge payload: 10,000 subtitle segments (>4MB) processed in single NDJSON line."""
        proc = self._spawn_sidecar()
        try:
            seg_count = 10000
            huge_segments = [
                {
                    "id": i,
                    "start": round(i * 1.5, 3),
                    "end": round(i * 1.5 + 1.2, 3),
                    "text": f"Adversarial segment {i} Japanese speech content testing high-volume memory buffer",
                    "thai_text": f"ข้อความจำลองซับไตเติลสำหรับการทดสอบหน่วยความจำขนาดใหญ่ ลำดับที่ {i}"
                }
                for i in range(1, seg_count + 1)
            ]

            req = {
                "id": 99999,
                "method": "engine.shift_time",
                "params": {
                    "segments": huge_segments,
                    "offset_seconds": 2.5
                }
            }

            line = json.dumps(req, ensure_ascii=False)
            payload_size_mb = len(line.encode("utf-8")) / (1024 * 1024)
            self.assertGreater(payload_size_mb, 1.5, "Payload size should exceed 1.5 MB")

            t0 = time.perf_counter()
            proc.stdin.write(line + "\n")
            proc.stdin.flush()

            resp_line = proc.stdout.readline()
            self.assertTrue(resp_line, "Daemon failed to return response for huge input")
            resp = json.loads(resp_line)
            duration = time.perf_counter() - t0

            assert_zero_emojis(resp, "huge input response")
            self.assertEqual(resp.get("id"), 99999)
            self.assertIsNone(resp.get("error"))

            shifted_segs = resp.get("result", {}).get("segments", [])
            self.assertEqual(len(shifted_segs), seg_count)
            self.assertEqual(shifted_segs[0]["start"], round(1 * 1.5 + 2.5, 3))
            self.assertEqual(shifted_segs[-1]["start"], round(seg_count * 1.5 + 2.5, 3))
            self.assertLess(duration, 15.0, f"10k segments shift took {duration:.2f}s, expected < 15s")
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_adv03_empty_and_whitespace_requests(self):
        """Adversarial empty lines, tab characters, and degenerate JSON structures."""
        proc = self._spawn_sidecar()
        try:
            # 1. Send series of whitespace and newlines
            proc.stdin.write("\n\n\n")
            proc.stdin.write("     \n")
            proc.stdin.write("\t\t  \r\n")
            proc.stdin.flush()

            # 2. Send empty JSON object: {}
            proc.stdin.write("{}\n")
            proc.stdin.flush()
            err_line = proc.stdout.readline()
            err_resp = json.loads(err_line)
            self.assertIsNotNone(err_resp.get("error"))
            self.assertEqual(err_resp["error"].get("code"), -32600)

            # 3. Send non-dict JSON values (array, primitive number, string)
            proc.stdin.write("[1, 2, 3]\n")
            proc.stdin.flush()
            arr_resp = json.loads(proc.stdout.readline())
            self.assertEqual(arr_resp["error"].get("code"), -32600)

            proc.stdin.write("12345\n")
            proc.stdin.flush()
            num_resp = json.loads(proc.stdout.readline())
            self.assertEqual(num_resp["error"].get("code"), -32600)

            # 4. Verify daemon is still functional
            proc.stdin.write(json.dumps({"id": 777, "method": "engine.ping", "params": {}}) + "\n")
            proc.stdin.flush()
            ping_resp = json.loads(proc.stdout.readline())
            self.assertEqual(ping_resp.get("id"), 777)
            self.assertEqual(ping_resp["result"]["status"], "ready")
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_adv04_concurrent_writes_stress(self):
        """Adversarial concurrency: 10 client threads writing requests concurrently to sidecar."""
        proc = self._spawn_sidecar()
        try:
            num_threads = 10
            requests_per_thread = 15
            total_requests = num_threads * requests_per_thread

            write_lock = threading.Lock()
            response_queue = queue.Queue()

            # Background thread reading responses continuously
            stop_reader = threading.Event()

            def reader_loop():
                while not stop_reader.is_set():
                    line = proc.stdout.readline()
                    if not line:
                        break
                    try:
                        parsed = json.loads(line)
                        response_queue.put(parsed)
                    except Exception:
                        pass

            reader_thread = threading.Thread(target=reader_loop, daemon=True)
            reader_thread.start()

            # Worker threads sending requests
            def worker(thread_idx: int):
                for req_i in range(requests_per_thread):
                    req_id = thread_idx * 1000 + req_i
                    msg = json.dumps({"id": req_id, "method": "engine.ping", "params": {}})
                    with write_lock:
                        proc.stdin.write(msg + "\n")
                        proc.stdin.flush()
                    time.sleep(0.002)

            threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Collect all responses
            collected_ids = set()
            deadline = time.time() + 10.0
            while len(collected_ids) < total_requests and time.time() < deadline:
                try:
                    resp = response_queue.get(timeout=0.5)
                    collected_ids.add(resp.get("id"))
                except queue.Empty:
                    pass

            self.assertEqual(len(collected_ids), total_requests,
                             f"Received {len(collected_ids)} of {total_requests} concurrent requests")
            stop_reader.set()
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)

    def test_adv05_malformed_json_and_robust_recovery(self):
        """Adversarial resilience: alternating corrupt JSON lines and valid requests."""
        proc = self._spawn_sidecar()
        try:
            malformed_payloads = [
                '{"id": 1, "method": ',  # Truncated
                '{"id": 2, "method": "engine.ping", "params": {unquoted_key: 1}}',  # Invalid syntax
                '<<<BAD_DATA_PROTOCOL_CORRUPT>>>',  # Non-JSON random string
                '{"id": 4, "method": 12345}',  # Invalid method type (integer)
                '{"id": 5, "method": "engine.non_existent_method_test"}',  # Unknown method
                '{"id": 6, "method": "engine.shift_time", "params": {"segments": "NOT_A_LIST"}}',  # Type error
            ]

            for idx, malformed in enumerate(malformed_payloads):
                # 1. Send malformed request
                proc.stdin.write(malformed + "\n")
                proc.stdin.flush()

                err_line = proc.stdout.readline()
                self.assertTrue(err_line, f"Daemon died on malformed input {idx}: {malformed}")
                err_data = json.loads(err_line)
                self.assertIsNotNone(err_data.get("error"), f"Expected error response for {malformed}")

                # 2. Immediately send valid request to prove daemon recovered
                valid_id = 1000 + idx
                proc.stdin.write(json.dumps({"id": valid_id, "method": "engine.ping", "params": {}}) + "\n")
                proc.stdin.flush()

                valid_line = proc.stdout.readline()
                self.assertTrue(valid_line, f"Daemon failed to recover after input {idx}")
                valid_data = json.loads(valid_line)
                self.assertEqual(valid_data.get("id"), valid_id)
                self.assertEqual(valid_data.get("result", {}).get("status"), "ready")
        finally:
            proc.stdin.close()
            proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
