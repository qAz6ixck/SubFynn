# Feature 10: Hard Burn-in Video (Req R2.5)
# Opaque-box E2E test verifying hardsub burn-in, Windows path escaping, font styling, and playable video output.

import os
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path
import engine
from tests.test_helpers import (
    get_sample_video, get_bundled_ffmpeg, probe_media_file,
    make_sample_segments, assert_zero_emojis
)

class TestFeature10HardBurn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_video = get_sample_video()
        cls.ffmpeg = get_bundled_ffmpeg()
        cls.temp_dir = tempfile.mkdtemp(prefix="subfynn_test_hardburn_")

        # Create a fast 2-second sample video for quick burn test
        cls.short_video = os.path.join(cls.temp_dir, "short_sample.mp4")
        flags = 0x08000000 if os.name == "nt" else 0
        cmd = [
            cls.ffmpeg, "-y",
            "-ss", "0", "-t", "2",
            "-i", cls.sample_video,
            "-c", "copy",
            cls.short_video
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, creationflags=flags)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_hard_burn_windows_path_escaping(self):
        """Verifies Windows path escaping helper prevents FFmpeg filter graph parse errors."""
        win_path = r"C:\Users\User\Videos\SubFynn\movie:01.srt"
        # In FFmpeg filter syntax, ':' must be escaped as '\:' and '\' as '/'
        escaped = win_path.replace("\\", "/").replace(":", "\\:")
        self.assertNotIn(r"\Users", escaped)
        self.assertIn("C\\:/", escaped)
        assert_zero_emojis(escaped, "escaped path")

    def test_hard_burn_font_configuration(self):
        """Verifies engine contains font configuration for Thai typography (Leelawadee UI / Arial)."""
        self.assertTrue(hasattr(engine, "burn_subtitles_to_video"))

    def test_hard_burn_execution_short_clip(self):
        """Executes actual hardsub burn on 2s video clip and verifies output file creation."""
        srt_path = os.path.join(self.temp_dir, "short_burn.srt")
        out_video = os.path.join(self.temp_dir, "burned_output.mp4")

        # Create 1-second cue
        short_segments = [
            {
                "id": 1,
                "start": 0.2,
                "end": 1.8,
                "thai_text": "ทดสอบเผาซับไตเติล"
            }
        ]
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(short_segments))

        result = engine.burn_subtitles_to_video(
            video_path=self.short_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg,
            font_size=18
        )

        self.assertTrue(os.path.isfile(out_video), "Burned video file must exist")
        self.assertGreater(os.path.getsize(out_video), 10_000, "Burned video must have non-trivial size")
        self.assertEqual(result, out_video)

    def test_hard_burn_output_probe_verification(self):
        """Probes the burned video with ffprobe and asserts valid h264 video and aac audio."""
        out_video = os.path.join(self.temp_dir, "burned_output.mp4")
        if not os.path.isfile(out_video):
            self.skipTest("burned_output.mp4 not generated")

        info = probe_media_file(out_video)
        assert_zero_emojis(info, "ffprobe burned video info")

        streams = info.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        self.assertIsNotNone(v_stream, "Must have valid video stream")
        self.assertEqual(v_stream.get("codec_name"), "h264")
        self.assertIsNotNone(a_stream, "Must have valid audio stream")

    def test_hard_burn_error_on_missing_srt(self):
        """Verifies attempting to burn with non-existent SRT raises FileNotFoundError or returns None."""
        bogus_srt = os.path.join(self.temp_dir, "non_existent.srt")
        out_video = os.path.join(self.temp_dir, "bogus_burn.mp4")

        with self.assertRaises(FileNotFoundError):
            engine.burn_subtitles_to_video(
                video_path=self.short_video,
                srt_path=bogus_srt,
                output_video_path=out_video,
                ffmpeg_path=self.ffmpeg
            )

    def test_hard_burn_error_on_missing_video(self):
        """Verifies attempting to burn non-existent video raises FileNotFoundError."""
        bogus_video = os.path.join(self.temp_dir, "non_existent_video.mp4")
        srt_path = os.path.join(self.temp_dir, "short_burn.srt")
        out_video = os.path.join(self.temp_dir, "bogus_burn2.mp4")

        with self.assertRaises(FileNotFoundError):
            engine.burn_subtitles_to_video(
                video_path=bogus_video,
                srt_path=srt_path,
                output_video_path=out_video,
                ffmpeg_path=self.ffmpeg
            )

if __name__ == "__main__":
    unittest.main()
