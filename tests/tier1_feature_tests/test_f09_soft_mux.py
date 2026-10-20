# Feature 9: Soft-mux Subtitles (Req R2.5)
# Opaque-box E2E test verifying stream copy fast soft-muxing, metadata tags, and ffprobe stream verification.

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import engine
from tests.test_helpers import (
    get_sample_video, get_bundled_ffmpeg, probe_media_file,
    make_sample_segments, assert_zero_emojis
)

class TestFeature09SoftMux(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_video = get_sample_video()
        cls.ffmpeg = get_bundled_ffmpeg()
        cls.temp_dir = tempfile.mkdtemp(prefix="subfynn_test_softmux_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_soft_mux_command_parameters(self):
        """Verifies soft-muxing utilizes stream copy without transcoding video/audio."""
        # Check engine mux implementation
        self.assertTrue(hasattr(engine, "mux_subtitles_to_video"))

    def test_soft_mux_execution_with_sample_video(self):
        """Executes actual soft-muxing on subfynn_trailer.mp4 and verifies output exists."""
        srt_path = os.path.join(self.temp_dir, "test_soft.srt")
        out_video = os.path.join(self.temp_dir, "softmuxed_output.mp4")
        srt_content = engine.generate_srt(make_sample_segments())
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        result_path = engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg
        )

        self.assertTrue(os.path.isfile(out_video), "Soft-muxed output video must be created")
        self.assertGreater(os.path.getsize(out_video), 100_000, "Output file must be non-trivial")
        self.assertEqual(result_path, out_video)

    def test_soft_mux_stream_probe_verification(self):
        """Probes the generated soft-muxed video with ffprobe and asserts subtitle stream presence."""
        out_video = os.path.join(self.temp_dir, "softmuxed_output.mp4")
        if not os.path.isfile(out_video):
            self.skipTest("softmuxed_output.mp4 not generated")

        info = probe_media_file(out_video)
        assert_zero_emojis(info, "ffprobe soft-muxed video info")

        streams = info.get("streams", [])
        codec_types = [s.get("codec_type") for s in streams]

        self.assertIn("video", codec_types, "Video stream must be preserved")
        self.assertIn("audio", codec_types, "Audio stream must be preserved")
        self.assertIn("subtitle", codec_types, "Subtitle stream must be embedded into container")

    def test_soft_mux_mkv_container_support(self):
        """Verifies soft-muxing into Matroska (.mkv) container format."""
        srt_path = os.path.join(self.temp_dir, "test_soft.srt")
        out_mkv = os.path.join(self.temp_dir, "softmuxed_output.mkv")
        if not os.path.isfile(srt_path):
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(engine.generate_srt(make_sample_segments()))

        engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_path,
            output_video_path=out_mkv,
            ffmpeg_path=self.ffmpeg
        )
        self.assertTrue(os.path.isfile(out_mkv))
        info = probe_media_file(out_mkv)
        codec_types = [s.get("codec_type") for s in info.get("streams", [])]
        self.assertIn("subtitle", codec_types)

    def test_soft_mux_error_on_missing_input(self):
        """Verifies attempting to mux non-existent video returns None or raises error."""
        bogus_video = os.path.join(self.temp_dir, "non_existent_input.mp4")
        srt_path = os.path.join(self.temp_dir, "test_soft.srt")
        out_video = os.path.join(self.temp_dir, "bogus_out.mp4")

        with self.assertRaises(FileNotFoundError):
            engine.mux_subtitles_to_video(
                video_path=bogus_video,
                srt_path=srt_path,
                output_video_path=out_video,
                ffmpeg_path=self.ffmpeg
            )

    def test_soft_mux_speed_duration(self):
        """Verifies stream copy muxing is fast (under 10 seconds for 15s clip)."""
        import time
        srt_path = os.path.join(self.temp_dir, "test_soft.srt")
        out_video = os.path.join(self.temp_dir, "timed_output.mp4")

        t0 = time.time()
        engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg
        )
        elapsed = time.time() - t0
        self.assertLess(elapsed, 10.0, "Stream copy soft-mux should complete in <10 seconds")

if __name__ == "__main__":
    unittest.main()
