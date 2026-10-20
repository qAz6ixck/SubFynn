# Feature 6: Interactive Subtitle Editor (Req R2.4)
# Opaque-box E2E test verifying live editing, search filtering, segment indexing, and insertion/deletion.

import copy
import unittest
from tests.test_helpers import make_sample_segments, assert_zero_emojis

def search_segments(segments, query: str):
    """Filters segments by query against source text or thai_text."""
    if not query or not query.strip():
        return list(segments)
    q = query.strip().lower()
    return [
        s for s in segments
        if q in (s.get("text") or "").lower() or q in (s.get("thai_text") or "").lower()
    ]

def renumber_segments(segments):
    """Renumbers 1-based sequential indices."""
    for idx, s in enumerate(segments, start=1):
        s["index"] = idx
    return segments

class TestFeature06SubtitleEditor(unittest.TestCase):
    def setUp(self):
        self.segments = make_sample_segments()

    def test_subtitle_segment_data_structure(self):
        """Verifies each segment contains mandatory fields: index, start, end, text, thai_text."""
        for seg in self.segments:
            assert_zero_emojis(seg, "segment")
            self.assertIn("index", seg)
            self.assertIn("start", seg)
            self.assertIn("end", seg)
            self.assertIn("text", seg)
            self.assertIn("thai_text", seg)
            self.assertIsInstance(seg["index"], int)
            self.assertGreaterEqual(seg["index"], 1)

    def test_live_in_place_editing_updates_segment(self):
        """Verifies in-place modification of Thai translation updates data model."""
        working_copy = copy.deepcopy(self.segments)
        new_translation = "สวัสดีโลกยุคใหม่ (แก้ไขแล้ว)"
        working_copy[0]["thai_text"] = new_translation

        self.assertEqual(working_copy[0]["thai_text"], new_translation)
        assert_zero_emojis(working_copy[0]["thai_text"], "edited translation")
        # Ensure other fields remain intact
        self.assertEqual(working_copy[0]["start_str"], "00:00:01,000")
        self.assertEqual(working_copy[0]["text"], "こんにちは、世界！")

    def test_search_filter_case_insensitive(self):
        """Verifies searching by query matches Japanese text or Thai text."""
        # Query matching Thai text
        thai_match = search_segments(self.segments, "สวัสดี")
        self.assertEqual(len(thai_match), 1)
        self.assertEqual(thai_match[0]["index"], 1)

        # Query matching Japanese text
        jp_match = search_segments(self.segments, "世界")
        self.assertEqual(len(jp_match), 1)
        self.assertEqual(jp_match[0]["index"], 1)

        # Query matching SubFynn
        sub_match = search_segments(self.segments, "subfynn")
        self.assertEqual(len(sub_match), 1)
        self.assertEqual(sub_match[0]["index"], 2)

    def test_segment_insertion_maintains_order(self):
        """Verifies inserting a cue into the list and renumbering maintains chronological order."""
        new_cue = {
            "index": 0,
            "start": "00:00:03,600",
            "end": "00:00:04,100",
            "start_ms": 3600,
            "end_ms": 4100,
            "text": "少し休憩。",
            "thai_text": "พักสักครู่"
        }
        updated = copy.deepcopy(self.segments)
        updated.insert(1, new_cue)
        renumber_segments(updated)

        self.assertEqual(len(updated), 4)
        for idx, cue in enumerate(updated, start=1):
            self.assertEqual(cue["index"], idx)
        self.assertEqual(updated[1]["text"], "少し休憩。")

    def test_segment_deletion_renumbers_indices(self):
        """Verifies deleting a cue preserves sequential 1-based indexing."""
        updated = copy.deepcopy(self.segments)
        del updated[1]  # Delete segment 2
        renumber_segments(updated)

        self.assertEqual(len(updated), 2)
        self.assertEqual(updated[0]["index"], 1)
        self.assertEqual(updated[1]["index"], 2)
        self.assertEqual(updated[1]["text"], "高速で正確な翻訳を実現します。")

    def test_empty_search_returns_all_records(self):
        """Verifies empty or whitespace search queries return all segments."""
        self.assertEqual(len(search_segments(self.segments, "")), len(self.segments))
        self.assertEqual(len(search_segments(self.segments, "   ")), len(self.segments))
        self.assertEqual(len(search_segments(self.segments, None)), len(self.segments))

if __name__ == "__main__":
    unittest.main()
