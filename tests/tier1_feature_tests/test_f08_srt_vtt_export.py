# Feature 8: SRT & VTT Export (Req R2.4)
# Opaque-box E2E test verifying SRT and VTT formatting, millisecond delimiters, and UTF-8 encoding.

import re
import unittest
import engine
from tests.test_helpers import make_sample_segments, assert_zero_emojis

class TestFeature08SrtVttExport(unittest.TestCase):
    def setUp(self):
        self.segments = make_sample_segments()

    def test_srt_serialization_format_and_millisecond_comma(self):
        """Verifies SubRip format: sequential numbers, HH:MM:SS,mmm --> HH:MM:SS,mmm, and text."""
        srt_content = engine.generate_srt(self.segments)
        assert_zero_emojis(srt_content, "generated SRT")

        self.assertIn("1\n00:00:01,000 --> 00:00:03,500\n", srt_content)
        self.assertIn("2\n00:00:04,200 --> 00:00:07,800\n", srt_content)
        self.assertIn("3\n00:00:08,000 --> 00:00:10,500\n", srt_content)
        # Verify comma is used as decimal separator for SRT
        timecode_matches = re.findall(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}", srt_content)
        self.assertEqual(len(timecode_matches), 3)

    def test_vtt_serialization_format_and_millisecond_period(self):
        """Verifies WebVTT format: WEBVTT header, HH:MM:SS.mmm --> HH:MM:SS.mmm, and text."""
        vtt_content = engine.generate_vtt(self.segments)
        assert_zero_emojis(vtt_content, "generated VTT")

        self.assertTrue(vtt_content.startswith("WEBVTT\n"), "VTT must begin with WEBVTT header")
        self.assertIn("00:00:01.000 --> 00:00:03.500\n", vtt_content)
        self.assertIn("00:00:04.200 --> 00:00:07.800\n", vtt_content)
        # Verify period is used as decimal separator for VTT
        timecode_matches = re.findall(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", vtt_content)
        self.assertEqual(len(timecode_matches), 3)

    def test_thai_unicode_fidelity(self):
        """Verifies Thai script is exported without corruption or replacement characters."""
        srt_content = engine.generate_srt(self.segments)
        vtt_content = engine.generate_vtt(self.segments)

        self.assertIn("สวัสดีชาวโลก", srt_content)
        self.assertIn("สวัสดีชาวโลก", vtt_content)
        # Check no unicode replacement character U+FFFD exists
        self.assertNotIn("\ufffd", srt_content)
        self.assertNotIn("\ufffd", vtt_content)

    def test_multiline_subtitle_handling(self):
        """Verifies multiline cues preserve internal linebreaks properly."""
        multiline_seg = [
            {
                "id": 1,
                "start": 1.0,
                "end": 3.0,
                "thai_text": "บรรทัดแรก\nบรรทัดที่สอง"
            }
        ]
        srt = engine.generate_srt(multiline_seg)
        self.assertIn("บรรทัดแรก\nบรรทัดที่สอง", srt)

    def test_special_character_preservation(self):
        """Verifies quotes, punctuation, and brackets are preserved."""
        special_seg = [
            {
                "id": 1,
                "start": 0.5,
                "end": 2.0,
                "thai_text": "«คำพูดสำคัญ!» [เสียงดนตรี] (วงเล็บ)"
            }
        ]
        srt = engine.generate_srt(special_seg)
        assert_zero_emojis(srt, "special characters SRT")
        self.assertIn("«คำพูดสำคัญ!» [เสียงดนตรี] (วงเล็บ)", srt)

    def test_empty_segments_export(self):
        """Verifies empty list of segments produces clean empty SRT and standard VTT header."""
        srt = engine.generate_srt([])
        vtt = engine.generate_vtt([])
        self.assertEqual(srt.strip(), "")
        self.assertEqual(vtt.strip(), "WEBVTT")

if __name__ == "__main__":
    unittest.main()
