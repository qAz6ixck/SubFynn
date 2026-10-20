# Tier 4: Real-World Workload Scenarios
# Realistic end-to-end user workflows for the SubFynn desktop rebuild.

import os
import copy
import json
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path
import engine
from tests.test_helpers import (
    get_project_root, get_sample_video, get_bundled_ffmpeg,
    probe_media_file, make_sample_segments, assert_zero_emojis
)
from tests.tier1_feature_tests.test_f06_subtitle_editor import search_segments

class TestTier4Workloads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.sample_video = get_sample_video()
        cls.ffmpeg = get_bundled_ffmpeg()
        cls.temp_dir = tempfile.mkdtemp(prefix="subfynn_tier4_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_workload_01_full_demux_transcription_simulation(self):
        """Workflow 1: Video import, 16kHz audio demuxing, text cleaning, and Thai post-processing."""
        wav_path = os.path.join(self.temp_dir, "workload_audio.wav")
        # 1. Demux audio
        demux_res = engine.extract_audio(self.sample_video, wav_path, self.ffmpeg)
        self.assertEqual(demux_res, wav_path)
        self.assertTrue(os.path.isfile(wav_path))

        # 2. Simulate raw Whisper output segments
        raw_cues = [
            {"id": 0, "start": 0.5, "end": 2.2, "original_text": "こんにちは！", "thai_text": "こんにちは！"},
            {"id": 1, "start": 2.5, "end": 4.8, "original_text": "テスト動画です。", "thai_text": "テスト動画です。"},
        ]

        # 3. Apply JAV/Thai post-processing
        processed_cues = []
        for cue in raw_cues:
            th = engine.post_process_jav_thai("สวัสดีครับ วิดีโอนี้เป็นการทดสอบ", cue["original_text"], style="jav")
            processed_cues.append({
                "id": cue["id"],
                "start": cue["start"],
                "end": cue["end"],
                "start_str": engine.format_timestamp(cue["start"], "srt"),
                "end_str": engine.format_timestamp(cue["end"], "srt"),
                "text": cue["original_text"],
                "thai_text": th
            })

        self.assertEqual(len(processed_cues), 2)
        assert_zero_emojis(processed_cues, "processed workload cues")
        # Timing monotonicity check
        self.assertLess(processed_cues[0]["start"], processed_cues[0]["end"])
        self.assertLess(processed_cues[0]["end"], processed_cues[1]["start"])

    def test_workload_02_interactive_edit_bulk_shift_and_dual_export(self):
        """Workflow 2: 50-cue project loaded, user edits lines, shifts by +1.5s, exports SRT and VTT."""
        # 1. Generate 50 realistic cues
        project_cues = [
            {
                "id": i,
                "start": float(i * 2),
                "end": float(i * 2 + 1.8),
                "text": f"Original subtitle dialogue line {i}",
                "thai_text": f"บทสนทนาคำบรรยายภาษาไทยลำดับที่ {i}"
            }
            for i in range(1, 51)
        ]

        # 2. User edits line 5 and line 10 in-place
        project_cues[4]["thai_text"] = "ข้อความแก้ไขบรรทัดที่ 5 โดยผู้ใช้"
        project_cues[9]["thai_text"] = "ข้อความแก้ไขบรรทัดที่ 10 โดยผู้ใช้"

        # 3. User applies +1.5s bulk time-shift
        shifted_cues = engine.shift_subtitle_segments(project_cues, 1.5)

        # 4. Verify edited lines retain user content after shifting
        self.assertEqual(shifted_cues[4]["thai_text"], "ข้อความแก้ไขบรรทัดที่ 5 โดยผู้ใช้")
        self.assertEqual(shifted_cues[9]["thai_text"], "ข้อความแก้ไขบรรทัดที่ 10 โดยผู้ใช้")
        self.assertEqual(shifted_cues[0]["start_str"], "00:00:03,500")

        # 5. Dual export: download SRT and VTT
        srt_path = os.path.join(self.temp_dir, "project_export.srt")
        vtt_path = os.path.join(self.temp_dir, "project_export.vtt")

        srt_content = engine.generate_srt(shifted_cues)
        vtt_content = engine.generate_vtt(shifted_cues)

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write(vtt_content)

        self.assertTrue(os.path.isfile(srt_path))
        self.assertTrue(os.path.isfile(vtt_path))

        # Check export cue counts match 50
        self.assertIn("50\n", srt_content)
        self.assertTrue(vtt_content.startswith("WEBVTT\n"))

    def test_workload_03_zero_delay_soft_mux_pipeline(self):
        """Workflow 3: Stream-copy soft-muxing subtitle track into MP4 container."""
        srt_path = os.path.join(self.temp_dir, "softmux_workflow.srt")
        out_video = os.path.join(self.temp_dir, "softmux_final.mp4")

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(make_sample_segments()))

        res = engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg
        )
        self.assertEqual(res, out_video)

        # Verify output with ffprobe
        info = probe_media_file(out_video)
        streams = info.get("streams", [])
        types = [s["codec_type"] for s in streams]
        self.assertIn("video", types)
        self.assertIn("audio", types)
        self.assertIn("subtitle", types)

    def test_workload_04_hard_burn_subtitles_full_workflow(self):
        """Workflow 4: Hardsub burn-in video rendering with Thai typography."""
        # Create 1.5s sample clip for fast rendering
        short_video = os.path.join(self.temp_dir, "clip_15s.mp4")
        flags = 0x08000000 if os.name == "nt" else 0
        cmd = [
            self.ffmpeg, "-y", "-ss", "0", "-t", "1.5",
            "-i", self.sample_video, "-c", "copy", short_video
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=flags)

        srt_path = os.path.join(self.temp_dir, "hardburn_workflow.srt")
        burned_video = os.path.join(self.temp_dir, "burned_final.mp4")

        burn_cues = [
            {"id": 1, "start": 0.2, "end": 1.2, "thai_text": "ทดสอบเผาซับไตเติลภาษาไทยแท้"}
        ]
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(burn_cues))

        res = engine.burn_subtitles_to_video(
            video_path=short_video,
            srt_path=srt_path,
            output_video_path=burned_video,
            ffmpeg_path=self.ffmpeg,
            font_size=18
        )
        self.assertEqual(res, burned_video)
        self.assertTrue(os.path.isfile(burned_video))

        # Check video stream in burned output
        info = probe_media_file(burned_video)
        v = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual(v["codec_name"], "h264")

    def test_workload_05_error_resilience_and_graceful_recovery(self):
        """Workflow 5: User errors, missing media streams, and graceful recovery."""
        from engine_sidecar import rpc_ping

        # 1. Ping engine - should always be ready
        status = rpc_ping()
        self.assertEqual(status["status"], "ready")

        # 2. User attempts to shift empty segment list
        empty_shifted = engine.shift_subtitle_segments([], -5.0)
        self.assertEqual(empty_shifted, [])

        # 3. User generates SRT/VTT from empty cues
        empty_srt = engine.generate_srt([])
        empty_vtt = engine.generate_vtt([])
        self.assertEqual(empty_srt, "")
        self.assertEqual(empty_vtt.strip(), "WEBVTT")

        # 4. User attempts muxing with non-existent source
        with self.assertRaises(FileNotFoundError):
            engine.mux_subtitles_to_video(
                video_path=os.path.join(self.temp_dir, "non_existent.mp4"),
                srt_path=os.path.join(self.temp_dir, "test.srt"),
                output_video_path=os.path.join(self.temp_dir, "out.mp4"),
                ffmpeg_path=self.ffmpeg
            )

    def test_workload_06_rapid_multibatch_lifecycle_stress(self):
        """Workflow 6: Full multi-action pipeline stress executed in sequence."""
        # Step A: Load segments
        cues = make_sample_segments()

        # Step B: User edits
        cues[0]["thai_text"] = "ขั้นตอนที่ 1 แก้ไข"

        # Step C: Rapid time shifting +0.5s then -0.5s
        shifted_fwd = engine.shift_subtitle_segments(cues, 0.5)
        shifted_back = engine.shift_subtitle_segments(shifted_fwd, -0.5)
        self.assertEqual(shifted_back[0]["start"], 1.0)

        # Step D: Search filtering
        match = search_segments(shifted_back, "ขั้นตอนที่ 1")
        self.assertEqual(len(match), 1)

        # Step E: Export SRT & VTT
        srt_str = engine.generate_srt(shifted_back)
        vtt_str = engine.generate_vtt(shifted_back)
        self.assertTrue(len(srt_str) > 0)
        self.assertTrue(len(vtt_str) > 0)
        assert_zero_emojis(srt_str, "stress SRT")
        assert_zero_emojis(vtt_str, "stress VTT")

        # Step F: Soft-mux
        srt_file = os.path.join(self.temp_dir, "stress.srt")
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write(srt_str)
        muxed_file = os.path.join(self.temp_dir, "stress_muxed.mp4")
        engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_file,
            output_video_path=muxed_file,
            ffmpeg_path=self.ffmpeg
        )
        self.assertTrue(os.path.isfile(muxed_file))

if __name__ == "__main__":
    unittest.main()
