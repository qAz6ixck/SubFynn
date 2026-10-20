# Feature 7 Boundaries: Time Shifting (+/-0.5s & bulk)
# Verifies extreme negative clamps, hours rollover (>24h), microsecond rounding, and zero-duration corrections.

import copy
import unittest
import engine
from tests.test_helpers import make_sample_segments, assert_zero_emojis

class TestBoundary07TimeShifting(unittest.TestCase):
    def setUp(self):
        self.segments = make_sample_segments()

    def test_extreme_negative_shift_clamped_to_zero(self):
        """Verifies shifting backwards by -999,999s cleanly clamps to 0.0s."""
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), -999999.0)
        for s in shifted:
            self.assertGreaterEqual(s["start"], 0.0)
            self.assertGreater(s["end"], 0.0)
            self.assertEqual(s["start_str"], "00:00:00,000")
            assert_zero_emojis(s, "clamped segment")

    def test_extreme_positive_shift_rollover(self):
        """Verifies huge positive offset (>27 hours) formats hours properly without crashing."""
        offset = 100000.0  # 100,000s = 27h 46m 40s
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), offset)
        # Segment 1 original was 1.0s -> 100001.0s -> 27:46:41,000
        self.assertEqual(shifted[0]["start_str"], "27:46:41,000")
        assert_zero_emojis(shifted[0]["start_str"], "27h timecode")

    def test_float_microsecond_rounding_fidelity(self):
        """Verifies float microsecond offsets round cleanly to nearest millisecond."""
        offset = 1.1238  # Should round to 1.124
        shifted = engine.shift_subtitle_segments(copy.deepcopy(self.segments), offset)
        self.assertAlmostEqual(shifted[0]["start"], 2.124, places=3)
        self.assertEqual(shifted[0]["start_str"], "00:00:02,124")

    def test_shift_empty_segments_list(self):
        """Verifies shifting empty segment list returns empty list."""
        shifted = engine.shift_subtitle_segments([], 5.0)
        self.assertEqual(shifted, [])

    def test_shift_negative_zero_identity(self):
        """Verifies -0.0 and +0.0 offsets behave identically."""
        shifted_pos = engine.shift_subtitle_segments(copy.deepcopy(self.segments), 0.0)
        shifted_neg = engine.shift_subtitle_segments(copy.deepcopy(self.segments), -0.0)
        self.assertEqual(shifted_pos, shifted_neg)

    def test_end_time_greater_than_start_after_clamp(self):
        """Verifies end time is guaranteed to be >= start time + 0.1s after negative clamping."""
        zero_seg = [{"id": 1, "start": 0.05, "end": 0.08, "text": "Quick", "thai_text": "สั้น"}]
        shifted = engine.shift_subtitle_segments(zero_seg, -1.0)
        self.assertEqual(shifted[0]["start"], 0.0)
        self.assertGreaterEqual(shifted[0]["end"], 0.1)
        self.assertGreater(shifted[0]["end"], shifted[0]["start"])

if __name__ == "__main__":
    unittest.main()
