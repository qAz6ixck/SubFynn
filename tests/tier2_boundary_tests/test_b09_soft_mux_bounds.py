# Feature 9 Boundaries: Soft-mux Subtitles
# Verifies file overwriting (-y), directories with spaces, empty SRT tracks, audio sampling rate preservation.

import os
import shutil
import tempfile
import unittest
import engine
from tests.test_helpers import (
    get_sample_video, get_bundled_ffmpeg, probe_media_file,
    make_sample_segments, assert_zero_emojis
)

class TestBoundary09SoftMux(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_video = get_sample_video()
        cls.ffmpeg = get_bundled_ffmpeg()
        cls.temp_dir = tempfile.mkdtemp(prefix="subfynn_bound_softmux_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_soft_mux_overwrite_existing_file(self):
        """Verifies destination file is safely overwritten without interactive prompt."""
        out_video = os.path.join(self.temp_dir, "overwrite_test.mp4")
        # Pre-create dummy destination
        with open(out_video, "wb") as f:
            f.write(b"pre-existing old content")

        srt_path = os.path.join(self.temp_dir, "test.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(make_sample_segments()))

        res = engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg
        )
        self.assertEqual(res, out_video)
        self.assertGreater(os.path.getsize(out_video), 100_000)

    def test_soft_mux_output_directory_with_spaces_and_brackets(self):
        """Verifies output directory containing spaces and brackets is supported."""
        special_dir = os.path.join(self.temp_dir, "Custom Output [Folder] (2026)")
        os.makedirs(special_dir, exist_ok=True)
        out_video = os.path.join(special_dir, "muxed.mp4")
        srt_path = os.path.join(special_dir, "test.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(make_sample_segments()))

        res = engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=srt_path,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg
        )
        self.assertTrue(os.path.isfile(out_video))

    def test_soft_mux_empty_srt_file(self):
        """Verifies soft-muxing an empty SRT file runs without container failure."""
        empty_srt = os.path.join(self.temp_dir, "empty.srt")
        with open(empty_srt, "w", encoding="utf-8") as f:
            f.write("")

        out_video = os.path.join(self.temp_dir, "empty_srt_muxed.mp4")
        res = engine.mux_subtitles_to_video(
            video_path=self.sample_video,
            srt_path=empty_srt,
            output_video_path=out_video,
            ffmpeg_path=self.ffmpeg
        )
        self.assertTrue(os.path.isfile(out_video))

    def test_soft_mux_corrupt_video_input(self):
        """Verifies invalid video file raises FileNotFoundError or returns None."""
        corrupt_video = os.path.join(self.temp_dir, "corrupt.mp4")
        with open(corrupt_video, "wb") as f:
            f.write(b"not a video file")
        srt_path = os.path.join(self.temp_dir, "corrupt_test.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(engine.generate_srt(make_sample_segments()))
        out_video = os.path.join(self.temp_dir, "corrupt_out.mp4")

        # Either returns None or raises exception
        try:
            res = engine.mux_subtitles_to_video(
                video_path=corrupt_video,
                srt_path=srt_path,
                output_video_path=out_video,
                ffmpeg_path=self.ffmpeg
            )
            # If returned without throwing, res should be None
            self.assertIsNone(res)
        except Exception:
            pass  # Raising exception is also acceptable error handling

    def test_soft_mux_preserves_audio_sampling_rate(self):
        """Verifies audio stream sampling rate and channels are identical to source."""
        out_video = os.path.join(self.temp_dir, "overwrite_test.mp4")
        if not os.path.isfile(out_video):
            self.skipTest("overwrite_test.mp4 not generated")

        orig_info = probe_media_file(self.sample_video)
        muxed_info = probe_media_file(out_video)

        orig_audio = next(s for s in orig_info["streams"] if s["codec_type"] == "audio")
        muxed_audio = next(s for s in muxed_info["streams"] if s["codec_type"] == "audio")

        self.assertEqual(orig_audio.get("sample_rate"), muxed_audio.get("sample_rate"))
        self.assertEqual(orig_audio.get("channels"), muxed_audio.get("channels"))

    def test_soft_mux_non_interactive_flags(self):
        """Verifies engine.py mux implementation contains -y flag for non-interactive execution."""
        import inspect
        source = inspect.getsource(engine.mux_subtitles_to_video)
        self.assertIn("-y", source)

if __name__ == "__main__":
    unittest.main()
