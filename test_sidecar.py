"""
Automated Unit and Integration Tests for engine_sidecar.py.

Verifies:
- Direct JSON-RPC dispatch (ping, load_model, shift_time, burn, mux, shutdown).
- Spawning engine_sidecar.py as a subprocess via standard pipes.
- NDJSON line-delimited communication.
- Real-time progress event streaming.
- Stdin EOF watchdog immediate exit (exit code 0).
- Clean graceful shutdown command (exit code 0).
- Malformed JSON recovery and error reporting (-32700, -32601, -32603).
"""

import os
import sys
import json
import time
import shutil
import unittest
import subprocess
from unittest.mock import MagicMock, patch

import engine
import engine_sidecar


class TestSidecarDirect(unittest.TestCase):
    """In-process unit tests for sidecar RPC handlers and dispatch logic."""

    def test_ping_direct(self):
        res, err, is_shutdown = engine_sidecar.dispatch_rpc({"id": 1, "method": "engine.ping"})
        self.assertIsNone(err)
        self.assertFalse(is_shutdown)
        self.assertIsNotNone(res)
        self.assertEqual(res["status"], "ready")
        self.assertEqual(res["version"], "1.0.0")
        self.assertIsInstance(res["cuda_available"], bool)
        self.assertIsInstance(res["cached_models"], list)
        self.assertTrue(isinstance(res["ffmpeg_path"], str) and len(res["ffmpeg_path"]) > 0)

    def test_bare_method_names(self):
        # Bare name without 'engine.' prefix should also route seamlessly
        res, err, is_shutdown = engine_sidecar.dispatch_rpc({"id": 2, "method": "ping"})
        self.assertIsNone(err)
        self.assertEqual(res["status"], "ready")

        res_health, err, _ = engine_sidecar.dispatch_rpc({"id": 3, "method": "health"})
        self.assertIsNone(err)
        self.assertEqual(res_health["status"], "ready")

    def test_unknown_method(self):
        res, err, is_shutdown = engine_sidecar.dispatch_rpc({"id": 4, "method": "engine.non_existent_method"})
        self.assertIsNone(res)
        self.assertIsNotNone(err)
        self.assertEqual(err["code"], -32601)
        self.assertIn("Method not found", err["message"])

    def test_invalid_request_format(self):
        res, err, _ = engine_sidecar.dispatch_rpc({"id": 5, "method": 12345})
        self.assertIsNone(res)
        self.assertIsNotNone(err)
        self.assertEqual(err["code"], -32600)

    def test_shift_time_direct(self):
        segments = [
            {"id": 1, "start": 1.0, "end": 3.0, "original_text": "One", "thai_text": "หนึ่ง"},
            {"id": 2, "start": 3.5, "end": 5.0, "original_text": "Two", "thai_text": "สอง"},
        ]
        res, err, _ = engine_sidecar.dispatch_rpc({
            "id": 6,
            "method": "engine.shift_time",
            "params": {"segments": segments, "offset_seconds": 1.5},
        })
        self.assertIsNone(err)
        self.assertIsNotNone(res)
        shifted = res["segments"]
        self.assertEqual(shifted[0]["start"], 2.5)
        self.assertEqual(shifted[0]["end"], 4.5)
        self.assertIn("00:00:02,500 --> 00:00:04,500", res["srt_content"])
        self.assertTrue(res["vtt_content"].startswith("WEBVTT"))

    def test_shift_time_invalid_params(self):
        res, err, _ = engine_sidecar.dispatch_rpc({
            "id": 7,
            "method": "engine.shift_time",
            "params": {"offset_seconds": 1.0},
        })
        self.assertIsNone(res)
        self.assertIsNotNone(err)
        self.assertEqual(err["code"], -32603)

    def test_load_model_direct(self):
        with patch("engine.load_whisper_model_safely") as mock_load:
            mock_load.return_value = MagicMock()
            res, err, _ = engine_sidecar.dispatch_rpc({
                "id": 8,
                "method": "engine.load_model",
                "params": {"model_size": "large-v3"},
            })
            self.assertIsNone(err)
            self.assertTrue(res["loaded"])
            self.assertEqual(res["model_size"], "large-v3")
            mock_load.assert_called_once_with("large-v3")

    def test_classify_stage(self):
        self.assertEqual(engine_sidecar.classify_stage(15.0, "กำลังแยกเสียง"), "extracting_audio")
        self.assertEqual(engine_sidecar.classify_stage(50.0, "กำลังถอดเสียง"), "transcribing")
        self.assertEqual(engine_sidecar.classify_stage(80.0, "กำลังแปลภาษา"), "translating")
        self.assertEqual(engine_sidecar.classify_stage(93.0, "กำลังบันทึกคำบรรยาย"), "generating_subtitles")
        self.assertEqual(engine_sidecar.classify_stage(96.0, "กำลังใส่คลิป"), "embedding_subtitles")
        self.assertEqual(engine_sidecar.classify_stage(100.0, "เสร็จเรียบร้อย"), "completed")

    def test_make_response(self):
        succ = engine_sidecar.make_response(10, {"ok": True}, None)
        self.assertEqual(succ["id"], 10)
        self.assertEqual(succ["result"], {"ok": True})
        self.assertIsNone(succ["error"])

        fail = engine_sidecar.make_response(11, None, {"code": -32603, "message": "fail"})
        self.assertEqual(fail["id"], 11)
        self.assertIsNone(fail["result"])
        self.assertEqual(fail["error"]["code"], -32603)


class TestSidecarSubprocess(unittest.TestCase):
    """Subprocess integration tests spawning engine_sidecar.py over anonymous pipes."""

    @classmethod
    def setUpClass(cls):
        cls.workspace = os.path.abspath("test_sidecar_workspace")
        os.makedirs(cls.workspace, exist_ok=True)
        cls.ffmpeg = engine.find_ffmpeg()

        # Generate a small 1-second synthetic video with audio for testing media operations
        cls.synthetic_video = os.path.join(cls.workspace, "sidecar_synth.mp4")
        cmd = [
            cls.ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264",
            "-c:a", "aac",
            cls.synthetic_video,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert res.returncode == 0, f"Failed to generate synthetic video: {res.stderr.decode()}"

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.workspace):
            shutil.rmtree(cls.workspace, ignore_errors=True)

    def _spawn_sidecar(self) -> subprocess.Popen:
        """Spawns engine_sidecar.py as a clean background subprocess with piped I/O."""
        cmd = [sys.executable, "-u", "engine_sidecar.py"]
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

    def _close_proc(self, proc: subprocess.Popen) -> None:
        """Safely closes all pipes and terminates the subprocess."""
        for pipe in (proc.stdin, proc.stdout, proc.stderr):
            if pipe:
                try:
                    pipe.close()
                except Exception:
                    pass
        if proc.poll() is None:
            try:
                proc.kill()
                proc.wait(timeout=2)
            except Exception:
                pass

    def _send_request(self, proc: subprocess.Popen, req: dict) -> None:
        line = json.dumps(req, ensure_ascii=False) + "\n"
        proc.stdin.write(line)
        proc.stdin.flush()

    def _read_response(self, proc: subprocess.Popen, timeout_sec: float = 15.0) -> dict:
        """Reads a response line, skipping any intermediate progress events."""
        start = time.time()
        while time.time() - start < timeout_sec:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if data.get("type") == "progress":
                continue
            return data
        raise TimeoutError(f"No response received within {timeout_sec}s")

    def test_subprocess_ping(self):
        proc = self._spawn_sidecar()
        try:
            self._send_request(proc, {"id": 101, "method": "engine.ping", "params": {}})
            resp = self._read_response(proc)
            self.assertEqual(resp["id"], 101)
            self.assertIsNone(resp["error"])
            result = resp["result"]
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["version"], "1.0.0")
            self.assertIn("cuda_available", result)
            self.assertIn("cached_models", result)
            self.assertIn("ffmpeg_path", result)
            self.assertTrue(os.path.isfile(result["ffmpeg_path"]))
        finally:
            self._close_proc(proc)

    def test_subprocess_load_model_probe(self):
        proc = self._spawn_sidecar()
        try:
            self._send_request(proc, {"id": 102, "method": "engine.load_model", "params": {"model_size": "tiny"}})
            resp = self._read_response(proc, timeout_sec=20.0)
            self.assertEqual(resp["id"], 102)
            self.assertIsNone(resp["error"])
            result = resp["result"]
            self.assertTrue(result["loaded"])
            self.assertEqual(result["model_size"], "tiny")
            self.assertIn("device", result)
        finally:
            self._close_proc(proc)

    def test_subprocess_shift_time(self):
        proc = self._spawn_sidecar()
        try:
            req = {
                "id": 103,
                "method": "engine.shift_time",
                "params": {
                    "segments": [
                        {
                            "id": 1,
                            "start": 2.0,
                            "end": 4.0,
                            "original_text": "Subtitle Test",
                            "thai_text": "ทดสอบซับ",
                        }
                    ],
                    "offset_seconds": 1.0,
                },
            }
            self._send_request(proc, req)
            resp = self._read_response(proc)
            self.assertEqual(resp["id"], 103)
            self.assertIsNone(resp["error"])
            result = resp["result"]
            self.assertEqual(result["segments"][0]["start"], 3.0)
            self.assertEqual(result["segments"][0]["end"], 5.0)
            self.assertIn("00:00:03,000 --> 00:00:05,000", result["srt_content"])
            self.assertTrue(result["vtt_content"].startswith("WEBVTT"))
        finally:
            self._close_proc(proc)

    def test_subprocess_burn_and_mux_subtitles(self):
        proc = self._spawn_sidecar()
        try:
            burned_out = os.path.join(self.workspace, "burned_sub_test.mp4")
            req_burn = {
                "id": 104,
                "method": "engine.burn_subtitles",
                "params": {
                    "video_path": self.synthetic_video,
                    "output_video_path": burned_out,
                    "srt_content": "1\n00:00:00,000 --> 00:00:01,000\nทดสอบเบิร์นซับไตเติล\n",
                    "font_size": 18,
                },
            }
            self._send_request(proc, req_burn)
            resp_burn = self._read_response(proc, timeout_sec=20.0)
            self.assertEqual(resp_burn["id"], 104)
            self.assertIsNone(resp_burn["error"])
            self.assertTrue(resp_burn["result"]["success"])
            self.assertTrue(os.path.isfile(burned_out))
            self.assertGreater(os.path.getsize(burned_out), 1000)

            mux_out = os.path.join(self.workspace, "mux_sub_test.mp4")
            req_mux = {
                "id": 105,
                "method": "engine.mux_subtitles",
                "params": {
                    "video_path": self.synthetic_video,
                    "output_video_path": mux_out,
                    "srt_content": "1\n00:00:00,000 --> 00:00:01,000\nทดสอบมักซ์ซับ\n",
                },
            }
            self._send_request(proc, req_mux)
            resp_mux = self._read_response(proc, timeout_sec=15.0)
            self.assertEqual(resp_mux["id"], 105)
            self.assertIsNone(resp_mux["error"])
            self.assertTrue(resp_mux["result"]["success"])
            self.assertTrue(os.path.isfile(mux_out))
            self.assertGreater(os.path.getsize(mux_out), 1000)
        finally:
            self._close_proc(proc)

    def test_subprocess_progress_streaming(self):
        proc = self._spawn_sidecar()
        try:
            req = {
                "id": 106,
                "method": "engine.process_video",
                "params": {
                    "video_path": self.synthetic_video,
                    "output_dir": os.path.join(self.workspace, "pipeline_out"),
                    "model_size": "tiny",
                    "embed_mode": "none",
                },
            }
            self._send_request(proc, req)

            progress_events = []
            final_response = None
            start_time = time.time()

            while time.time() - start_time < 30.0:
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("type") == "progress":
                    progress_events.append(data["data"])
                elif "id" in data:
                    final_response = data
                    break

            self.assertIsNotNone(final_response, "Did not receive final RPC response")
            self.assertEqual(final_response["id"], 106)
            self.assertIsNone(final_response["error"])
            self.assertTrue(final_response["result"]["success"])
            self.assertIn("srt_path", final_response["result"])
            self.assertIn("vtt_path", final_response["result"])
            self.assertIn("srt_content", final_response["result"])
            self.assertIn("vtt_content", final_response["result"])

            # Verify progress events streamed properly
            self.assertGreater(len(progress_events), 0, "No progress events streamed")
            stages_seen = {p.get("stage") for p in progress_events}
            self.assertTrue(any(s in stages_seen for s in ["extracting_audio", "transcribing", "completed"]))
            # Verify percent monotonicity or range
            for p in progress_events:
                self.assertGreaterEqual(p["percent"], 0.0)
                self.assertLessEqual(p["percent"], 100.0)
                self.assertEqual(p["task_id"], 106)
        finally:
            self._close_proc(proc)

    def test_subprocess_clean_shutdown(self):
        proc = self._spawn_sidecar()
        try:
            self._send_request(proc, {"id": 107, "method": "engine.shutdown", "params": {}})
            resp = self._read_response(proc)
            self.assertEqual(resp["id"], 107)
            self.assertEqual(resp["result"]["status"], "shutting_down")
            exit_code = proc.wait(timeout=5)
            self.assertEqual(exit_code, 0)
        finally:
            self._close_proc(proc)

    def test_subprocess_stdin_eof_watchdog(self):
        proc = self._spawn_sidecar()
        try:
            # Verify it is alive and answering
            self._send_request(proc, {"id": 108, "method": "engine.ping", "params": {}})
            resp = self._read_response(proc)
            self.assertEqual(resp["result"]["status"], "ready")

            # Close stdin pipe -> sends EOF to sidecar
            proc.stdin.close()

            # Sidecar must exit immediately with code 0 via os._exit(0)
            exit_code = proc.wait(timeout=5)
            self.assertEqual(exit_code, 0)
        finally:
            self._close_proc(proc)

    def test_subprocess_malformed_json_recovery(self):
        proc = self._spawn_sidecar()
        try:
            # Send corrupted non-JSON line
            proc.stdin.write("INVALID NON JSON LINE\n")
            proc.stdin.flush()

            resp = self._read_response(proc)
            self.assertIsNone(resp["id"])
            self.assertIsNotNone(resp["error"])
            self.assertEqual(resp["error"]["code"], -32700)

            # Send valid request right after; process should still be alive and responsive
            self._send_request(proc, {"id": 109, "method": "engine.ping", "params": {}})
            resp2 = self._read_response(proc)
            self.assertEqual(resp2["id"], 109)
            self.assertEqual(resp2["result"]["status"], "ready")
        finally:
            self._close_proc(proc)


if __name__ == "__main__":
    unittest.main()
