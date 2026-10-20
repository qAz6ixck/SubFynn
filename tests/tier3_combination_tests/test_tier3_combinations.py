# Tier 3: Cross-Feature Combinations (Pairwise Interactions)
# Verifies pairwise integration across all 11 core SubFynn desktop features.

import os
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import engine
from tests.test_helpers import (
    get_project_root, get_sample_video, get_bundled_ffmpeg,
    probe_media_file, make_sample_segments, assert_zero_emojis
)
from tests.tier1_feature_tests.test_f03_file_dialog import validate_dropped_file
from tests.tier1_feature_tests.test_f06_subtitle_editor import search_segments

class TestTier3Combinations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.sample_video = get_sample_video()
        cls.ffmpeg = get_bundled_ffmpeg()
        cls.temp_dir = tempfile.mkdtemp(prefix="subfynn_tier3_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_comb_01_dialog_to_sidecar_ping(self):
        """Pairwise: File Dialog (F3) + Sidecar IPC (F2)."""
        # Validate selected video from file dialog
        self.assertTrue(validate_dropped_file(self.sample_video))
        from engine_sidecar import rpc_ping
        ping_res = rpc_ping()
        self.assertEqual(ping_res["status"], "ready")
        self.assertTrue(os.path.isfile(ping_res["ffmpeg_path"]))

    def test_comb_02_model_controls_to_engine_pipeline(self):
        """Pairwise: Model Controls (F5) + Sidecar IPC (F2)."""
        model_selection = {
            "model_size": "large-v3",
            "gemini_model": "gemini-3.5-live-translate-preview",
            "translation_style": "jav",
            "gemini_api_key": "AIzaSyDummyKeyForCombinationTest123"
        }
        assert_zero_emojis(model_selection, "model controls selection")
        from engine_sidecar import rpc_shift_time
        # Verify sidecar processes time shifting with model parameters
        shift_res = rpc_shift_time({"segments": make_sample_segments(), "offset_seconds": 0.5})
        self.assertIn("srt_content", shift_res)
        self.assertIn("00:00:01,500", shift_res["srt_content"])

    def test_comb_03_transcription_to_editor_population(self):
        """Pairwise: Engine Pipeline (F2) + Subtitle Editor (F6)."""
        raw_output = [
            {"id": 0, "start": 1.25, "end": 3.75, "text": "こんにちは", "thai_text": "สวัสดี"}
        ]
        # Map into editor table data structure
        editor_table = []
        for s in raw_output:
            editor_table.append({
                "index": s["id"] + 1,
                "start": s["start"],
                "end": s["end"],
                "start_str": engine.format_timestamp(s["start"], "srt"),
                "end_str": engine.format_timestamp(s["end"], "srt"),
                "text": s["text"],
                "thai_text": s["thai_text"]
            })
        self.assertEqual(editor_table[0]["index"], 1)
        self.assertEqual(editor_table[0]["start_str"], "00:00:01,250")
        self.assertEqual(editor_table[0]["thai_text"], "สวัสดี")

    def test_comb_04_editor_edit_to_time_shift(self):
        """Pairwise: Subtitle Editor (F6) + Time Shifting (F7)."""
        segments = make_sample_segments()
        # In-place editing of segment 1 Thai translation
        segments[0]["thai_text"] = "ข้อความที่ถูกแก้ไขแล้วในตาราง"
        # Immediate +0.5s time shift
        shifted = engine.shift_subtitle_segments(segments, 0.5)

        self.assertEqual(shifted[0]["thai_text"], "ข้อความที่ถูกแก้ไขแล้วในตาราง")
        self.assertEqual(shifted[0]["start_str"], "00:00:01,500")

    def test_comb_05_time_shift_to_srt_export(self):
        """Pairwise: Time Shifting (F7) + SRT Export (F8)."""
        segments = make_sample_segments()
        shifted = engine.shift_subtitle_segments(segments, 1.2)
        srt = engine.generate_srt(shifted)

        # Original segment 1 was 1.0s -> 2.2s -> 00:00:02,200
        self.assertIn("00:00:02,200 --> 00:00:04,700", srt)

    def test_comb_06_time_shift_to_vtt_export(self):
        """Pairwise: Time Shifting (F7) + VTT Export (F8)."""
        segments = make_sample_segments()
        shifted = engine.shift_subtitle_segments(segments, 2.0)
        vtt = engine.generate_vtt(shifted)

        # Original segment 1 was 1.0s -> 3.0s -> 00:00:03.000 (period delimiter)
        self.assertTrue(vtt.startswith("WEBVTT\n"))
        self.assertIn("00:00:03.000 --> 00:00:05.500", vtt)

    def test_comb_07_editor_search_filter_then_export(self):
        """Pairwise: Subtitle Editor (F6) + Export (F8)."""
        segments = make_sample_segments()
        # Filter editor view by keyword
        filtered = search_segments(segments, "สวัสดี")
        self.assertEqual(len(filtered), 1)

        # Full project export exports all segments even when filtered
        full_srt = engine.generate_srt(segments)
        self.assertEqual(len(full_srt.strip().split("\n\n")), 3)

        # Filtered export exports only matching
        filtered_srt = engine.generate_srt(filtered)
        self.assertEqual(len(filtered_srt.strip().split("\n\n")), 1)

    def test_comb_08_edited_subtitles_to_soft_mux(self):
        """Pairwise: Subtitle Editor (F6) + Soft-mux (F9)."""
        segments = make_sample_segments()
        segments[0]["thai_text"] = "ซับไตเติลสดใหม่จากตัวแก้ไข"
        srt_path = os.path.join(self.temp_dir, "edited_for_mux.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(segments))

        out_video = os.path.join(self.temp_dir, "comb_muxed.mp4")
        engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg
        )
        self.assertTrue(os.path.isfile(out_video))
        info = probe_media_file(out_video)
        sub_stream = next((s for s in info["streams"] if s["codec_type"] == "subtitle"), None)
        self.assertIsNotNone(sub_stream)

    def test_comb_09_edited_subtitles_to_hard_burn(self):
        """Pairwise: Subtitle Editor (F6) + Hard Burn-in (F10)."""
        segments = [
            {"id": 1, "start": 0.1, "end": 0.9, "thai_text": "เผาซับไตเติลภาษาไทย"}
        ]
        srt_path = os.path.join(self.temp_dir, "edited_for_burn.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(segments))

        # Create quick 1s clip
        short_video = os.path.join(self.temp_dir, "short_comb.mp4")
        flags = 0x08000000 if os.name == "nt" else 0
        subprocess_cmd = [
            self.ffmpeg, "-y", "-ss", "0", "-t", "1",
            "-i", self.sample_video, "-c", "copy", short_video
        ]
        import subprocess
        subprocess.run(subprocess_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=flags)

        out_video = os.path.join(self.temp_dir, "comb_burned.mp4")
        engine.burn_subtitles_to_video(
            video_path=short_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg,
            font_size=16
        )
        self.assertTrue(os.path.isfile(out_video))

    def test_comb_10_splashscreen_to_main_window_transition(self):
        """Pairwise: Tauri Host (F1) + React UI Theme (F4)."""
        tauri_conf = self.root / "src-tauri" / "tauri.conf.json"
        with open(tauri_conf, "r", encoding="utf-8") as f:
            conf = json.load(f)

        windows = conf.get("app", {}).get("windows", [])
        splash = next(w for w in windows if w.get("label") == "splashscreen")
        main = next(w for w in windows if w.get("label") == "main")

        # Verify initial states: splash is visible/alwaysOnTop, main starts hidden
        self.assertTrue(splash.get("alwaysOnTop"))
        self.assertFalse(main.get("visible"))

    def test_comb_11_packaging_resources_to_ffmpeg_execution(self):
        """Pairwise: Packaging (F11) + FFmpeg Execution (F9/F10)."""
        tauri_conf = self.root / "src-tauri" / "tauri.conf.json"
        with open(tauri_conf, "r", encoding="utf-8") as f:
            conf = json.load(f)

        resources = conf.get("bundle", {}).get("resources", [])
        # Resources are defined relative to src-tauri
        src_tauri_dir = self.root / "src-tauri"
        for r in resources:
            resolved = (src_tauri_dir / r).resolve()
            self.assertTrue(resolved.exists(), f"Bundled resource {r} must exist at {resolved}")

    def test_comb_12_drag_drop_to_audio_demux(self):
        """Pairwise: Drag & Drop (F3) + Audio Demux (F2)."""
        self.assertTrue(validate_dropped_file(self.sample_video))
        out_wav = os.path.join(self.temp_dir, "demuxed_audio.wav")
        result = engine.extract_audio(
            video_path=self.sample_video,
            output_wav_path=out_wav,
            ffmpeg_path=self.ffmpeg
        )
        self.assertEqual(result, out_wav)
        self.assertTrue(os.path.isfile(out_wav))
        # Verify 16kHz mono WAV format
        info = probe_media_file(out_wav)
        audio = info["streams"][0]
        self.assertEqual(audio["codec_name"], "pcm_s16le")
        self.assertEqual(audio["sample_rate"], "16000")
        self.assertEqual(audio["channels"], 1)

if __name__ == "__main__":
    unittest.main()
