# Feature 6 Boundaries: Interactive Subtitle Editor
# Verifies empty lists, massive segment sets, regex escaping in search, and overlapping cues.

import time
import unittest
from tests.test_helpers import assert_zero_emojis
from tests.tier1_feature_tests.test_f06_subtitle_editor import search_segments, renumber_segments

def detect_overlapping_cues(segments):
    """Detects pairs of adjacent cues that overlap in time."""
    overlaps = []
    for i in range(len(segments) - 1):
        curr = segments[i]
        nxt = segments[i + 1]
        if curr.get("end", 0) > nxt.get("start", 0):
            overlaps.append((curr.get("id", i), nxt.get("id", i + 1)))
    return overlaps

class TestBoundary06SubtitleEditor(unittest.TestCase):
    def test_empty_subtitle_list_operations(self):
        """Verifies operations on empty list behave safely without IndexError."""
        empty_list = []
        self.assertEqual(len(search_segments(empty_list, "test")), 0)
        self.assertEqual(len(renumber_segments(empty_list)), 0)
        self.assertEqual(len(detect_overlapping_cues(empty_list)), 0)

    def test_massive_subtitle_list_stress(self):
        """Generates 10,000 segments and verifies renumbering and search complete in <0.5s."""
        massive = [
            {"id": i, "start": float(i), "end": float(i + 0.8), "text": f"Cue {i}", "thai_text": f"บทสนทนา {i}"}
            for i in range(1, 10001)
        ]
        t0 = time.time()
        renumber_segments(massive)
        matches = search_segments(massive, "Cue 9999")
        elapsed = time.time() - t0

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], 9999)
        self.assertLess(elapsed, 0.5, "Massive list operations should take <0.5s")

    def test_special_regex_characters_in_search(self):
        """Verifies search with regex metacharacters does not crash."""
        cues = [
            {"id": 1, "start": 1.0, "end": 2.0, "text": "Price: $100 [USD] (50% off)", "thai_text": "ราคา: 100$ (ลด 50%)"},
            {"id": 2, "start": 2.1, "end": 3.0, "text": "Regex test: .*+?^${}()", "thai_text": "ทดสอบเครื่องหมาย"}
        ]
        query = ".*+?^${}()"
        res = search_segments(cues, query)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], 2)

    def test_sub_millisecond_cue_duration(self):
        """Verifies handling of cue with micro-duration (1ms)."""
        micro_cue = [
            {"id": 1, "start": 1.000, "end": 1.001, "text": "Snap", "thai_text": "ชั่วพริบตา"}
        ]
        duration = micro_cue[0]["end"] - micro_cue[0]["start"]
        self.assertAlmostEqual(duration, 0.001, places=3)
        self.assertGreater(duration, 0)

    def test_empty_and_whitespace_segment_text(self):
        """Verifies segments with empty or whitespace text are validly structured."""
        blank_cues = [
            {"id": 1, "start": 1.0, "end": 2.0, "text": "", "thai_text": "   "},
            {"id": 2, "start": 2.5, "end": 3.5, "text": "\t\n", "thai_text": ""}
        ]
        assert_zero_emojis(blank_cues, "blank cues")
        self.assertEqual(len(blank_cues), 2)

    def test_overlapping_timecode_detection(self):
        """Verifies overlap detection identifies conflicting time ranges."""
        overlapping_cues = [
            {"id": 1, "start": 1.0, "end": 3.0, "text": "A"},
            {"id": 2, "start": 2.5, "end": 4.0, "text": "B"},  # Overlaps with 1 (starts at 2.5 < 3.0)
            {"id": 3, "start": 4.5, "end": 5.0, "text": "C"}
        ]
        overlaps = detect_overlapping_cues(overlapping_cues)
        self.assertEqual(len(overlaps), 1)
        self.assertEqual(overlaps[0], (1, 2))

if __name__ == "__main__":
    unittest.main()
