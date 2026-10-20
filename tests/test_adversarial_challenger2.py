"""
Adversarial Verification & Empirical Fuzzing Suite
SubFynn Rebuild - Challenger 2 Test Harness

Targets:
1. React Frontend Build (dist/): Zero-emoji probe across all chunks, HTML, and CSS.
2. Portable Release Package (dist/SubFynn-Windows-Portable.zip):
   Extraction, PE32+ validation, icon resources, FFmpeg 9.0 binaries (>80MB), and run check.
3. Python Engine Sidecar (engine_sidecar.py):
   NDJSON fuzzing: invalid methods, negative IDs, float/string/null IDs, malformed JSON,
   boundary timecodes (negative clamped, massive offsets, zero-duration), and stdout purity.
"""

import os
import re
import sys
import json
import time
import shutil
import struct
import tempfile
import unittest
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Comprehensive Emoji Regular Expression (covering Unicode 15.0+ emoji ranges)
COMPREHENSIVE_EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
    "\U0001F680-\U0001F6FF"  # Transport & Map Symbols
    "\U0001F700-\U0001F77F"  # Alchemical Symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Extended-A
    "\U0001F1E6-\U0001F1FF"  # Regional Indicator Symbols (Flags)
    "\U0001F200-\U0001F251"  # Enclosed Ideographic Supplement
    "\u2600-\u26FF"          # Misc Symbols
    "\u2700-\u27BF"          # Dingbats
    "\u2300-\u23FF"          # Misc Technical (e.g. watch, hourglass)
    "\u2B50"                 # Star
    "\u2B55"                 # Circle
    "\u2934-\u2935"          # Arrows
    "]+",
    flags=re.UNICODE
)

# Regex for escaped emoji unicode representations in bundles (e.g. \ud83d\ude00 or \u1f600)
ESCAPED_EMOJI_REGEX = re.compile(
    r"(?:\\u[dD][89a-fA-F][0-9a-fA-F]{2}\\u[dD][c-fC-F][0-9a-fA-F]{2})|"
    r"(?:\\u[0-9a-fA-F]{4})",
    flags=re.IGNORECASE
)


class TestAdversarialChallenger2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = PROJECT_ROOT
        cls.dist_dir = cls.root / "dist"
        cls.portable_zip = cls.dist_dir / "SubFynn-Windows-Portable.zip"

    # =========================================================================
    # AREA 1: React Frontend Build (dist/) Zero Emojis Adversarial Scan
    # =========================================================================

    def test_01_frontend_dist_files_exist(self):
        """Verifies dist/ contains HTML entries and bundled assets."""
        self.assertTrue(self.dist_dir.is_dir(), "dist/ directory must exist")
        index_html = self.dist_dir / "index.html"
        splash_html = self.dist_dir / "splashscreen.html"
        assets_dir = self.dist_dir / "assets"

        self.assertTrue(index_html.is_file(), "dist/index.html must exist")
        self.assertTrue(splash_html.is_file(), "dist/splashscreen.html must exist")
        self.assertTrue(assets_dir.is_dir(), "dist/assets directory must exist")

    def test_02_frontend_dist_zero_emojis_exhaustive_probe(self):
        """Adversarially probes all bundled HTML, JS, CSS, and JSON files in dist/ for any emojis."""
        scanned_files = []
        violations = []
        total_bytes = 0

        target_extensions = {".html", ".js", ".css", ".json", ".svg", ".txt"}

        for p in self.dist_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in target_extensions:
                scanned_files.append(p)
                total_bytes += p.stat().st_size
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    violations.append((str(p), [f"ReadError: {e}"]))
                    continue

                # 1. Direct Unicode character match
                direct_matches = COMPREHENSIVE_EMOJI_REGEX.findall(content)
                if direct_matches:
                    violations.append((str(p.relative_to(self.root)), "direct", direct_matches[:10]))

                # 2. Check for escaped surrogate pairs commonly representing emojis
                # Filter for surrogates in high surrogate range D800-DBFF followed by DC00-DFFF
                surrogates = re.findall(r"\\u[dD][89abAB][0-9a-fA-F]{2}\\u[dD][c-fC-F][0-9a-fA-F]{2}", content)
                if surrogates:
                    violations.append((str(p.relative_to(self.root)), "escaped_surrogates", surrogates[:10]))

        print(f"\n[EMOJI PROBE] Scanned {len(scanned_files)} files ({total_bytes:,} bytes) in dist/.")
        for f in scanned_files:
            print(f"  - {f.relative_to(self.root)} ({f.stat().st_size:,} bytes)")

        self.assertEqual(len(violations), 0, f"Detected emojis in frontend dist: {violations}")

    # =========================================================================
    # AREA 2: Portable Release Zip Extraction & Binary Integrity
    # =========================================================================

    def test_03_portable_zip_existence_and_hash(self):
        """Verifies portable zip package existence, size (>70MB), and valid zip header."""
        self.assertTrue(self.portable_zip.is_file(), f"Portable zip not found at {self.portable_zip}")
        zip_size = self.portable_zip.stat().st_size
        print(f"\n[ZIP PROBE] Portable zip size: {zip_size:,} bytes ({zip_size / (1024*1024):.2f} MB)")
        self.assertGreater(zip_size, 70_000_000, "Portable zip must be > 70MB (includes FFmpeg binaries)")

        # Verify ZIP PK signature
        with open(self.portable_zip, "rb") as f:
            sig = f.read(4)
        self.assertEqual(sig, b"PK\x03\x04", "File must have valid ZIP magic header")

    def test_04_portable_zip_extraction_and_manifest(self):
        """Extracts portable zip to temp directory and verifies all components."""
        import zipfile
        temp_extract = tempfile.mkdtemp(prefix="subfynn_probe_")
        try:
            with zipfile.ZipFile(self.portable_zip, "r") as zf:
                # Adversarial zip slip check: ensure no path contains '..' or absolute paths
                for name in zf.namelist():
                    norm = os.path.normpath(name)
                    self.assertFalse(norm.startswith("..") or os.path.isabs(norm), f"Zip slip path detected: {name}")
                zf.extractall(temp_extract)

            extracted_dir = Path(temp_extract) / "SubFynn"
            self.assertTrue(extracted_dir.is_dir(), "SubFynn/ directory must be extracted")

            subfynn_exe = extracted_dir / "SubFynn.exe"
            ffmpeg_exe = extracted_dir / "ffmpeg.exe"
            ffprobe_exe = extracted_dir / "ffprobe.exe"
            sidecar_py = extracted_dir / "engine_sidecar.py"
            engine_py = extracted_dir / "engine.py"
            icon_ico = extracted_dir / "assets" / "app_icon.ico"

            self.assertTrue(subfynn_exe.is_file(), "SubFynn.exe must exist in portable zip")
            self.assertTrue(ffmpeg_exe.is_file(), "ffmpeg.exe must exist in portable zip")
            self.assertTrue(ffprobe_exe.is_file(), "ffprobe.exe must exist in portable zip")
            self.assertTrue(sidecar_py.is_file(), "engine_sidecar.py must exist in portable zip")
            self.assertTrue(engine_py.is_file(), "engine.py must exist in portable zip")
            self.assertTrue(icon_ico.is_file(), "assets/app_icon.ico must exist in portable zip")

            # Check binary sizes
            self.assertGreater(ffmpeg_exe.stat().st_size, 80_000_000, "ffmpeg.exe in zip must be > 80MB")
            self.assertGreater(ffprobe_exe.stat().st_size, 80_000_000, "ffprobe.exe in zip must be > 80MB")
            self.assertGreater(subfynn_exe.stat().st_size, 5_000_000, "SubFynn.exe in zip must be > 5MB")

            # Verify PE32+ header of SubFynn.exe
            with open(subfynn_exe, "rb") as f:
                dos_hdr = f.read(64)
                self.assertEqual(dos_hdr[:2], b"MZ", "SubFynn.exe must have DOS MZ header")
                pe_offset = struct.unpack("<I", dos_hdr[60:64])[0]
                f.seek(pe_offset)
                pe_sig = f.read(4)
                self.assertEqual(pe_sig, b"PE\x00\x00", "SubFynn.exe must have PE signature")
                machine = struct.unpack("<H", f.read(2))[0]
                self.assertEqual(machine, 0x8664, "SubFynn.exe must be x64/AMD64 binary")

            # Verify FFmpeg & FFprobe executable execution from extracted dir
            flags = 0x08000000 if sys.platform == "win32" else 0
            p_f = subprocess.run([str(ffmpeg_exe), "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
            self.assertEqual(p_f.returncode, 0, f"ffmpeg execution failed: {p_f.stderr}")
            self.assertIn("ffmpeg version", p_f.stdout)

            p_p = subprocess.run([str(ffprobe_exe), "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
            self.assertEqual(p_p.returncode, 0, f"ffprobe execution failed: {p_p.stderr}")
            self.assertIn("ffprobe version", p_p.stdout)

            # Live run test of SubFynn.exe from extracted package
            p_app = subprocess.Popen([str(subfynn_exe)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
            time.sleep(1.5)
            self.assertIsNone(p_app.poll(), "SubFynn.exe terminated prematurely")
            self.assertGreater(p_app.pid, 0, "SubFynn.exe PID must be positive")
            p_app.terminate()
            p_app.wait(timeout=5)
            print(f"[ZIP PROBE] Successfully launched and terminated SubFynn.exe (PID {p_app.pid}) from extracted package.")

        finally:
            shutil.rmtree(temp_extract, ignore_errors=True)

    # =========================================================================
    # AREA 3: Python Engine Sidecar Adversarial Fuzzing & Stdout Purity
    # =========================================================================

    def test_05_sidecar_adversarial_fuzzing_and_stdout_purity(self):
        """
        Adversarially fuzzes engine_sidecar.py with 22 test cases and verifies 100% of stdout lines
        are strictly valid NDJSON without log corruption or unescaped tracebacks.
        """
        flags = 0x08000000 if sys.platform == "win32" else 0
        sidecar_script = self.root / "engine_sidecar.py"

        proc = subprocess.Popen(
            [sys.executable, str(sidecar_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=flags,
        )

        all_stdout_lines = []
        all_stderr_lines = []

        def send_and_recv(payload: str, timeout_sec: float = 3.0) -> dict:
            proc.stdin.write(payload + "\n")
            proc.stdin.flush()
            start = time.time()
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("EOF received from sidecar stdout")
            all_stdout_lines.append(line.rstrip("\r\n"))
            # Must strictly parse as valid JSON
            try:
                data = json.loads(line)
                return data
            except json.JSONDecodeError as e:
                self.fail(f"Stdout corruption detected! Non-JSON line: '{line}' - error: {e}")

        try:
            # Case 1: Standard Ping
            r = send_and_recv(json.dumps({"id": 1, "method": "engine.ping", "params": {}}))
            self.assertEqual(r.get("id"), 1)
            self.assertIsNone(r.get("error"))
            self.assertEqual(r.get("result", {}).get("status"), "ready")

            # Case 2: Method Not Found (Code -32601)
            r = send_and_recv(json.dumps({"id": 2, "method": "engine.nonexistent_method", "params": {}}))
            self.assertEqual(r.get("id"), 2)
            self.assertIsNone(r.get("result"))
            self.assertEqual(r.get("error", {}).get("code"), -32601)

            # Case 3: Negative Integer ID (-1)
            r = send_and_recv(json.dumps({"id": -1, "method": "engine.ping", "params": {}}))
            self.assertEqual(r.get("id"), -1)
            self.assertIsNone(r.get("error"))

            # Case 4: Large Negative ID (-99999999)
            r = send_and_recv(json.dumps({"id": -99999999, "method": "engine.ping", "params": {}}))
            self.assertEqual(r.get("id"), -99999999)

            # Case 5: String ID ("req-test-uuid-42")
            r = send_and_recv(json.dumps({"id": "req-test-uuid-42", "method": "engine.ping", "params": {}}))
            self.assertEqual(r.get("id"), "req-test-uuid-42")

            # Case 6: Float ID (3.14159)
            r = send_and_recv(json.dumps({"id": 3.14159, "method": "engine.ping", "params": {}}))
            self.assertEqual(r.get("id"), 3.14159)

            # Case 7: Null ID (None)
            r = send_and_recv(json.dumps({"id": None, "method": "engine.ping", "params": {}}))
            self.assertIsNone(r.get("id"))

            # Case 8: Malformed JSON syntax (Parse error Code -32700)
            r = send_and_recv('{"id": 8, "method": "engine.ping", invalid syntax')
            self.assertIsNone(r.get("id"))
            self.assertEqual(r.get("error", {}).get("code"), -32700)

            # Case 9: Non-Object JSON (JSON array instead of object - Code -32600)
            r = send_and_recv('[1, 2, 3]')
            self.assertIsNone(r.get("id"))
            self.assertEqual(r.get("error", {}).get("code"), -32600)

            # Case 10: Non-Object JSON (JSON string literal - Code -32600)
            r = send_and_recv('"just_a_string"')
            self.assertEqual(r.get("error", {}).get("code"), -32600)

            # Case 11: Null method (Code -32600)
            r = send_and_recv(json.dumps({"id": 11, "method": None, "params": {}}))
            self.assertEqual(r.get("id"), 11)
            self.assertEqual(r.get("error", {}).get("code"), -32600)

            # Case 12: Non-string method (Code -32600)
            r = send_and_recv(json.dumps({"id": 12, "method": 98765, "params": {}}))
            self.assertEqual(r.get("id"), 12)
            self.assertEqual(r.get("error", {}).get("code"), -32600)

            # Case 13: Missing required params on shift_time (Code -32603)
            r = send_and_recv(json.dumps({"id": 13, "method": "engine.shift_time", "params": {}}))
            self.assertEqual(r.get("id"), 13)
            self.assertEqual(r.get("error", {}).get("code"), -32603)
            self.assertIn("Missing required 'segments'", r.get("error", {}).get("message"))

            # Case 14: Non-list segments on shift_time (Code -32603)
            r = send_and_recv(json.dumps({"id": 14, "method": "engine.shift_time", "params": {"segments": "invalid_not_list"}}))
            self.assertEqual(r.get("id"), 14)
            self.assertEqual(r.get("error", {}).get("code"), -32603)

            # Case 15: Boundary Timecode: Negative offset clamping start/end >= 0.0
            sample_segs = [
                {"id": 1, "start": 1.5, "end": 4.0, "text": "Segment 1", "thai_text": "ข้อความ 1"}
            ]
            r = send_and_recv(json.dumps({
                "id": 15,
                "method": "engine.shift_time",
                "params": {"segments": sample_segs, "offset_seconds": -10.0}
            }))
            self.assertEqual(r.get("id"), 15)
            self.assertIsNone(r.get("error"))
            shifted = r.get("result", {}).get("segments", [])
            self.assertEqual(len(shifted), 1)
            self.assertGreaterEqual(shifted[0]["start"], 0.0, "Start timestamp must be clamped to >= 0.0")
            self.assertGreaterEqual(shifted[0]["end"], 0.0, "End timestamp must be clamped to >= 0.0")
            self.assertTrue(r.get("result", {}).get("srt_content"))
            self.assertTrue(r.get("result", {}).get("vtt_content"))

            # Case 16: Boundary Timecode: Massive offset (+1,000,000s)
            r = send_and_recv(json.dumps({
                "id": 16,
                "method": "engine.shift_time",
                "params": {"segments": sample_segs, "offset_seconds": 1_000_000.0}
            }))
            self.assertEqual(r.get("id"), 16)
            self.assertIsNone(r.get("error"))
            shifted_huge = r.get("result", {}).get("segments", [])
            self.assertGreater(shifted_huge[0]["start"], 1_000_000.0)

            # Case 17: Boundary Timecode: Zero-duration segment (start == end)
            zero_dur_segs = [
                {"id": 1, "start": 5.0, "end": 5.0, "text": "Instant cue", "thai_text": "ทันที"}
            ]
            r = send_and_recv(json.dumps({
                "id": 17,
                "method": "engine.shift_time",
                "params": {"segments": zero_dur_segs, "offset_seconds": 0.0}
            }))
            self.assertEqual(r.get("id"), 17)
            self.assertIsNone(r.get("error"))

            # Case 18: Boundary Timecode: Empty segments list ([])
            r = send_and_recv(json.dumps({
                "id": 18,
                "method": "engine.shift_time",
                "params": {"segments": [], "offset_seconds": 2.5}
            }))
            self.assertEqual(r.get("id"), 18)
            self.assertIsNone(r.get("error"))
            self.assertEqual(r.get("result", {}).get("segments"), [])

            # Case 19: Missing video_path on burn_subtitles (Code -32603)
            r = send_and_recv(json.dumps({"id": 19, "method": "engine.burn_subtitles", "params": {}}))
            self.assertEqual(r.get("id"), 19)
            self.assertEqual(r.get("error", {}).get("code"), -32603)

            # Case 20: Non-existent video_path on burn_subtitles (Code -32603)
            r = send_and_recv(json.dumps({
                "id": 20,
                "method": "engine.burn_subtitles",
                "params": {"video_path": "d:/does_not_exist_xyz.mp4", "srt_content": "1\n00:00:00,000 --> 00:00:01,000\nTest\n"}
            }))
            self.assertEqual(r.get("id"), 20)
            self.assertEqual(r.get("error", {}).get("code"), -32603)

            # Case 21: Missing srt_path and srt_content on mux_subtitles
            r = send_and_recv(json.dumps({
                "id": 21,
                "method": "engine.mux_subtitles",
                "params": {"video_path": str(self.root / "assets" / "subfynn_trailer.mp4")}
            }))
            self.assertEqual(r.get("id"), 21)
            self.assertEqual(r.get("error", {}).get("code"), -32603)

            # Case 22: Rapid-fire burst of 30 requests to verify ordering and no dropped lines
            burst_count = 30
            for i in range(burst_count):
                b_id = 100 + i
                proc.stdin.write(json.dumps({"id": b_id, "method": "engine.ping", "params": {}}) + "\n")
            proc.stdin.flush()

            burst_results = []
            for i in range(burst_count):
                b_line = proc.stdout.readline()
                self.assertTrue(b_line, f"Premature EOF on burst item {i}")
                all_stdout_lines.append(b_line.rstrip("\r\n"))
                b_data = json.loads(b_line)
                burst_results.append(b_data.get("id"))

            expected_ids = [100 + i for i in range(burst_count)]
            self.assertEqual(burst_results, expected_ids, "Burst requests must maintain exact FIFO ordering")

            # Final Case: Clean Shutdown
            proc.stdin.write(json.dumps({"id": 999, "method": "engine.shutdown", "params": {}}) + "\n")
            proc.stdin.flush()
            shutdown_line = proc.stdout.readline()
            self.assertTrue(shutdown_line)
            all_stdout_lines.append(shutdown_line.rstrip("\r\n"))
            shutdown_resp = json.loads(shutdown_line)
            self.assertEqual(shutdown_resp.get("id"), 999)

            # Verify sidecar exited with code 0
            exit_code = proc.wait(timeout=5)
            self.assertEqual(exit_code, 0, f"Sidecar did not exit cleanly (code {exit_code})")

            # Final Stdout Purity Assertion:
            # 1. Every single captured line from stdout MUST be valid JSON
            # 2. NO raw string prints, NO unescaped tracebacks, NO warnings on stdout
            print(f"\n[SIDECAR FUZZING] Verified {len(all_stdout_lines)} responses emitted on stdout.")
            for idx, raw_line in enumerate(all_stdout_lines):
                try:
                    parsed = json.loads(raw_line)
                    self.assertIsInstance(parsed, dict, f"Stdout line {idx} is not a JSON object: {raw_line}")
                except Exception as e:
                    self.fail(f"Corrupted stdout line at index {idx}: '{raw_line}' (error: {e})")

            print("[SIDECAR FUZZING] 100% of stdout lines are valid NDJSON. Zero log pollution.")

        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    unittest.main()
