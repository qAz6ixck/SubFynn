"""
Automated integration test for app.py Web server endpoints.
"""

import os
import time
import json
import urllib.request
import threading
import unittest

from app import start_server, AppRequestHandler, HTTPServer
import engine


class TestWebAppServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 5098
        cls.server = HTTPServer(("127.0.0.1", cls.port), AppRequestHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

        # Generate a small self-contained synthetic video for testing
        cls.test_video = os.path.abspath("test_app_video.mp4")
        ffmpeg = engine.find_ffmpeg()
        cmd = [
            ffmpeg,
            "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264",
            "-c:a", "aac",
            cls.test_video,
        ]
        import subprocess
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        if os.path.exists(cls.test_video):
            os.remove(cls.test_video)

    def test_get_index_html(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode("utf-8")
            self.assertIn("โปรแกรมสร้างซับไทยอัตโนมัติ", content)
            self.assertIn("videoPlayer", content)
            self.assertIn("onVideoTimeUpdate", content)
            self.assertIn("shiftSubtitles", content)
            self.assertIn("styleSelect", content)
            self.assertIn("geminiModelSelect", content)
            self.assertIn("gemini-2.5-pro", content)
            self.assertIn("หนังผู้ใหญ่ / JAV 18+", content)
            self.assertIn("large-v3", content)
            self.assertIn("medium", content)
            self.assertIn("kanit-thin", content)
            self.assertIn("kanit-bold", content)
            self.assertIn("kanit-regular", content)
            self.assertIn("playIntroVideo", content)

    def test_get_intro_video(self):
        url = f"http://127.0.0.1:{self.port}/assets/subfynn_intro.mp4"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "video/mp4")
            data = resp.read()
            self.assertGreater(len(data), 100000)

    def test_upload_and_process_flow(self):
        # 1. Upload a small synthetic video
        with open(self.test_video, "rb") as f:
            video_bytes = f.read()

        upload_url = f"http://127.0.0.1:{self.port}/api/upload?filename=test_web_flow.mp4"
        req = urllib.request.Request(
            upload_url,
            data=video_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            upload_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(upload_data["success"])
            task_id = upload_data["task_id"]

        # 2. Trigger processing with JAV translation style and gemini model
        proc_url = f"http://127.0.0.1:{self.port}/api/process"
        proc_req = urllib.request.Request(
            proc_url,
            data=json.dumps({
                "task_id": task_id,
                "model_size": "tiny",
                "source_lang": "auto",
                "translation_style": "jav_dirty",
                "gemini_model": "gemini-2.5-flash",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(proc_req) as resp:
            self.assertEqual(resp.status, 200)

        # 3. Poll progress until complete
        completed = False
        for _ in range(30):
            time.sleep(0.5)
            poll_url = f"http://127.0.0.1:{self.port}/api/progress?task_id={task_id}"
            with urllib.request.urlopen(poll_url) as resp:
                poll_data = json.loads(resp.read().decode("utf-8"))
                if poll_data.get("state") == "completed":
                    completed = True
                    break

        self.assertTrue(completed, "Web task did not complete in time")

        # 4. Save custom/edited subtitles via /api/save_subtitles
        save_url = f"http://127.0.0.1:{self.port}/api/save_subtitles"
        save_req = urllib.request.Request(
            save_url,
            data=json.dumps({
                "task_id": task_id,
                "segments": [
                    {
                        "id": 1,
                        "start": 0.0,
                        "end": 1.0,
                        "start_str": "00:00:00,000",
                        "end_str": "00:00:01,000",
                        "original_text": "Hello world",
                        "thai_text": "สวัสดีชาวโลก",
                        "text": "สวัสดีชาวโลก",
                    }
                ],
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(save_req) as resp:
            self.assertEqual(resp.status, 200)

        # 5. Test subtitle shifting endpoint
        shift_url = f"http://127.0.0.1:{self.port}/api/shift_subtitles"
        shift_req = urllib.request.Request(
            shift_url,
            data=json.dumps({
                "task_id": task_id,
                "offset_seconds": 0.5,
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(shift_req) as resp:
            self.assertEqual(resp.status, 200)
            shift_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(shift_data["success"])
            self.assertEqual(shift_data["segments"][0]["start"], 0.5)

        # 6. Check SRT download endpoint
        srt_url = f"http://127.0.0.1:{self.port}/api/download_srt?task_id={task_id}"
        with urllib.request.urlopen(srt_url) as resp:
            self.assertEqual(resp.status, 200)
            srt_content = resp.read().decode("utf-8")
            self.assertIn("สวัสดีชาวโลก", srt_content)
            self.assertIn("00:00:00,500", srt_content)

        # 7. Check VTT download endpoint
        vtt_url = f"http://127.0.0.1:{self.port}/api/download_vtt?task_id={task_id}"
        with urllib.request.urlopen(vtt_url) as resp:
            self.assertEqual(resp.status, 200)
            vtt_content = resp.read().decode("utf-8")
            self.assertTrue(vtt_content.startswith("WEBVTT"))
            self.assertIn("สวัสดีชาวโลก", vtt_content)

        # 8. Check media streaming endpoint with standard Range header
        media_url = f"http://127.0.0.1:{self.port}/media/{task_id}"
        req_range = urllib.request.Request(media_url, headers={"Range": "bytes=0-100"})
        with urllib.request.urlopen(req_range) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(len(resp.read()), 101)

        # 9. Check media streaming endpoint with suffix Range header (e.g. bytes=-50)
        req_suffix = urllib.request.Request(media_url, headers={"Range": "bytes=-50"})
        with urllib.request.urlopen(req_suffix) as resp:
            self.assertEqual(resp.status, 206)
            self.assertEqual(len(resp.read()), 50)

        # 10. Check media streaming out-of-bounds Range header (416)
        req_oob = urllib.request.Request(media_url, headers={"Range": "bytes=9999999-"})
        try:
            with urllib.request.urlopen(req_oob) as resp:
                self.assertEqual(resp.status, 416)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 416)
            e.close()

    def test_chunked_upload_flow(self):
        # Test multi-part chunked upload endpoint (/api/upload_chunk)
        with open(self.test_video, "rb") as f:
            video_bytes = f.read()

        total_size = len(video_bytes)
        chunk_size = 5000  # Split into multiple chunks
        total_chunks = (total_size + chunk_size - 1) // chunk_size

        upload_task_id = ""
        for i in range(total_chunks):
            start = i * chunk_size
            end = min(total_size, start + chunk_size)
            chunk_data = video_bytes[start:end]

            chunk_url = (
                f"http://127.0.0.1:{self.port}/api/upload_chunk?"
                f"filename=chunked_test.mp4&chunk_index={i}&total_chunks={total_chunks}"
                f"&total_size={total_size}"
            )
            if upload_task_id:
                chunk_url += f"&task_id={upload_task_id}"

            req = urllib.request.Request(
                chunk_url,
                data=chunk_data,
                headers={"Content-Type": "application/octet-stream"},
            )
            with urllib.request.urlopen(req) as resp:
                self.assertEqual(resp.status, 200)
                res_data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(res_data["success"])
                if not upload_task_id:
                    upload_task_id = res_data["task_id"]

                if i == total_chunks - 1:
                    self.assertTrue(res_data.get("completed"))
                    self.assertEqual(res_data["task_id"], upload_task_id)
                else:
                    self.assertFalse(res_data.get("completed", False))

    def test_find_available_port_fallback(self):
        from app import find_available_port
        # self.port is currently occupied by our test HTTP server
        free_port = find_available_port(self.port, max_attempts=10)
        self.assertNotEqual(free_port, self.port)
        self.assertGreater(free_port, self.port)

    def test_get_api_status(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "online")
            self.assertEqual(data.get("font"), "Kanit")
            self.assertIn("SubFynn", data.get("app"))
            self.assertIn("intro_video", data)

    def test_get_api_health(self):
        url = f"http://127.0.0.1:{self.port}/api/health"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "online")

    def test_vercel_matched_path_header(self):
        # Simulates Vercel rewrite where request to /api/status was rewritten to /api/index.py
        url = f"http://127.0.0.1:{self.port}/api/index.py"
        req = urllib.request.Request(url, headers={"x-vercel-matched-path": "/api/status"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "online")
            self.assertEqual(data.get("font"), "Kanit")

    def test_api_index_handler_import(self):
        import api.index
        self.assertTrue(hasattr(api.index, "handler"))
        self.assertTrue(issubclass(api.index.handler, AppRequestHandler))
        self.assertTrue(hasattr(api.index, "app"))
        self.assertTrue(hasattr(api.index, "application"))
        self.assertTrue(callable(api.index.app))

    def test_app_and_main_entrypoint_exports(self):
        import app
        import main
        self.assertTrue(hasattr(app, "handler"))
        self.assertTrue(hasattr(app, "app"))
        self.assertTrue(hasattr(app, "application"))
        self.assertTrue(callable(app.app))

        self.assertTrue(hasattr(main, "handler"))
        self.assertTrue(hasattr(main, "app"))
        self.assertTrue(hasattr(main, "application"))
        self.assertTrue(callable(main.app))

    def test_wsgi_app_request_handling(self):
        from io import BytesIO
        from app import wsgi_application

        captured = {}
        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        # Test GET /api/status via WSGI
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/status",
            "QUERY_STRING": "",
            "wsgi.input": BytesIO(b""),
        }
        res = wsgi_application(environ, start_response)
        self.assertEqual(captured["status"], "200 OK")
        body = json.loads(b"".join(res).decode("utf-8"))
        self.assertEqual(body.get("status"), "online")
        self.assertEqual(body.get("font"), "Kanit")

        # Test GET /api/health via WSGI
        res = wsgi_application({"REQUEST_METHOD": "GET", "PATH_INFO": "/api/health"}, start_response)
        self.assertEqual(captured["status"], "200 OK")
        body = json.loads(b"".join(res).decode("utf-8"))
        self.assertEqual(body.get("status"), "online")


if __name__ == "__main__":
    unittest.main()

