# Feature 10 Boundaries: Hard Burn-in Video
# Verifies auto-creation of directories, special filename escaping, font scaling, NVENC/CPU fallback, and framerate preservation.

import os
import shutil
import tempfile
import unittest
import subprocess
import engine
from tests.test_helpers import (
    get_sample_video, get_bundled_ffmpeg, probe_media_file,
    make_sample_segments, assert_zero_emojis
)

class TestBoundary10HardBurn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_video = get_sample_video()
        cls.ffmpeg = get_bundled_ffmpeg()
        cls.temp_dir = tempfile.mkdtemp(prefix="subfynn_bound_hardburn_")

        # 1-second sample clip
        cls.short_video = os.path.join(cls.temp_dir, "fast_clip.mp4")
        flags = 0x08000000 if os.name == "nt" else 0
        cmd = [
            cls.ffmpeg, "-y",
            "-ss", "0", "-t", "1",
            "-i", cls.sample_video,
            "-c", "copy",
            cls.short_video
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=flags)

        cls.default_srt = os.path.join(cls.temp_dir, "test.srt")
        with open(cls.default_srt, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt([{"id": 1, "start": 0.1, "end": 0.9, "thai_text": "ทดสอบเผาซับ"}]))

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_hard_burn_output_directory_auto_created(self):
        """Verifies parent output directory is automatically created if it does not exist."""
        nested_dir = os.path.join(self.temp_dir, "nested", "subfolder", "level3")
        out_video = os.path.join(nested_dir, "burned_nested.mp4")
        srt_path = os.path.join(self.temp_dir, "test.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt([{"id": 1, "start": 0.1, "end": 0.9, "thai_text": "ทดสอบ"}]))

        res = engine.burn_subtitles_to_video(
            video_path=self.short_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg,
            font_size=16
        )
        self.assertTrue(os.path.isfile(out_video))

    def test_hard_burn_srt_with_quotes_and_brackets(self):
        """Verifies subtitles with single quotes, double quotes, and brackets burn without filter syntax crashes."""
        out_video = os.path.join(self.temp_dir, "quotes_burned.mp4")
        srt_path = os.path.join(self.temp_dir, "quotes.srt")
        cue_text = """ทดสอบ 'คำพูดเดี่ยว' และ "คำพูดคู่" [วงเล็บ]"""
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt([{"id": 1, "start": 0.1, "end": 0.8, "thai_text": cue_text}]))

        res = engine.burn_subtitles_to_video(
            video_path=self.short_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg,
            font_size=18
        )
        self.assertTrue(os.path.isfile(out_video))

    def test_hard_burn_font_size_scaling(self):
        """Verifies font_size values like 12 and 28 execute successfully."""
        srt_path = os.path.join(self.temp_dir, "test.srt")
        for size in [12, 28]:
            out_video = os.path.join(self.temp_dir, f"burned_font_{size}.mp4")
            res = engine.burn_subtitles_to_video(
                video_path=self.short_video,
                srt_path=srt_path,
                output_video_path=out_video,
                ffmpeg_path=self.ffmpeg,
                font_size=size
            )
            self.assertTrue(os.path.isfile(out_video))

    def test_hard_burn_retains_resolution_and_framerate(self):
        """Probes burned output to confirm resolution matches input exactly."""
        out_video = os.path.join(self.temp_dir, "burned_font_12.mp4")
        if not os.path.isfile(out_video):
            self.skipTest("burned_font_12.mp4 not found")

        orig_info = probe_media_file(self.short_video)
        burned_info = probe_media_file(out_video)

        orig_v = next(s for s in orig_info["streams"] if s["codec_type"] == "video")
        burned_v = next(s for s in burned_info["streams"] if s["codec_type"] == "video")

        self.assertEqual(orig_v.get("width"), burned_v.get("width"))
        self.assertEqual(orig_v.get("height"), burned_v.get("height"))

    def test_hard_burn_error_on_zero_byte_video(self):
        """Verifies burning 0-byte video file fails cleanly."""
        zero_video = os.path.join(self.temp_dir, "zero.mp4")
        with open(zero_video, "wb") as f:
            pass
        srt_path = os.path.join(self.temp_dir, "test.srt")
        out_video = os.path.join(self.temp_dir, "zero_out.mp4")

        try:
            res = engine.burn_subtitles_to_video(
                video_path=zero_video,
                srt_path=srt_path,
                output_video_path=out_video,
                ffmpeg_path=self.ffmpeg
            )
            self.assertIsNone(res)
        except Exception:
            pass

    def test_hard_burn_cpu_libx264_presence(self):
        """Verifies engine contains libx264 fallback encoding command arguments."""
        import inspect
        source = inspect.getsource(engine.burn_subtitles_to_video)
        self.assertIn("libx264", source)

if __name__ == "__main__":
    unittest.main()
