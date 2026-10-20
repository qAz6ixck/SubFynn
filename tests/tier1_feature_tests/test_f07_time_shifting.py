# Feature 7: Time Shifting (+/-0.5s & bulk) (Req R2.4)
# Opaque-box E2E test verifying millisecond time shifting, non-negative clamping, and duration invariance.

import copy
import unittest
import engine
from tests.test_helpers import make_sample_segments, assert_zero_emojis

class TestFeature07TimeShifting(unittest.TestCase):
    def setUp(self):
        self.segments = make_sample_segments()

    def test_shift_subtitles_positive_half_second(self):
        """Verifies +0.5s shift increases start and end timestamps by exactly 500ms."""
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), 0.5)
        assert_zero_emojis(shifted, "shifted segments (+0.5s)")

        self.assertEqual(len(shifted), len(self.segments))
        # Segment 1 original was 1.0 -> 3.5
        self.assertAlmostEqual(shifted[0]["start"], 1.5, places=3)
        self.assertAlmostEqual(shifted[0]["end"], 4.0, places=3)
        self.assertEqual(shifted[0]["start_str"], "00:00:01,500")
        self.assertEqual(shifted[0]["end_str"], "00:00:04,000")

    def test_shift_subtitles_negative_half_second(self):
        """Verifies -0.5s shift decreases start and end timestamps by 500ms."""
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), -0.5)
        assert_zero_emojis(shifted, "shifted segments (-0.5s)")

        # Segment 1 original was 1.0 -> 3.5
        self.assertAlmostEqual(shifted[0]["start"], 0.5, places=3)
        self.assertAlmostEqual(shifted[0]["end"], 3.0, places=3)
        self.assertEqual(shifted[0]["start_str"], "00:00:00,500")
        self.assertEqual(shifted[0]["end_str"], "00:00:03,000")

    def test_shift_subtitles_custom_bulk_offset(self):
        """Verifies arbitrary bulk offset (e.g. +2.345s) shifts timestamps precisely."""
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), 2.345)
        # Original 1.0 + 2.345 = 3.345
        self.assertAlmostEqual(shifted[0]["start"], 3.345, places=3)
        self.assertAlmostEqual(shifted[0]["end"], 5.845, places=3)
        self.assertEqual(shifted[0]["start_str"], "00:00:03,345")
        self.assertEqual(shifted[0]["end_str"], "00:00:05,845")

    def test_shift_subtitles_non_negative_clamp(self):
        """Verifies shifting backwards past zero clamps start time to 0.0 and 00:00:00,000."""
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), -5.0)
        self.assertGreaterEqual(shifted[0]["start"], 0.0)
        self.assertEqual(shifted[0]["start_str"], "00:00:00,000")
        # No negative timestamps permitted
        self.assertFalse(shifted[0]["start_str"].startswith("-"))
        self.assertFalse(shifted[0]["end_str"].startswith("-"))

    def test_shift_subtitles_duration_invariance(self):
        """Verifies duration (end - start) remains unchanged when offset is applied."""
        offset = 1.75
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), offset)

        for orig, shifted_seg in zip(self.segments, shifted):
            orig_duration = orig["end"] - orig["start"]
            shifted_duration = shifted_seg["end"] - shifted_seg["start"]
            self.assertAlmostEqual(orig_duration, shifted_duration, places=3)

    def test_zero_offset_identity(self):
        """Verifies 0.0s offset preserves identical timestamps."""
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), 0.0)
        for orig, shifted_seg in zip(self.segments, shifted):
            self.assertEqual(orig["start"], shifted_seg["start"])
            self.assertEqual(orig["end"], shifted_seg["end"])

if __name__ == "__main__":
    unittest.main()
