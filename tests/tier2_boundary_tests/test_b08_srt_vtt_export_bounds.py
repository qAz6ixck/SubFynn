# Feature 8 Boundaries: SRT & VTT Export
# Verifies HTML tags, literal timecode delimiters, huge cue strings, mixed newlines, and Thai tone mark byte fidelity.

import unittest
import engine
from tests.test_helpers import assert_zero_emojis

class TestBoundary08SrtVttExport(unittest.TestCase):
    def test_cue_text_with_html_tags(self):
        """Verifies styling tags (<i>, <b>, <font>) are preserved in export."""
        styled_seg = [
            {"id": 1, "start": 1.0, "end": 2.5, "thai_text": "<i>ข้อความตัวเอียง</i> และ <b>ตัวหนา</b>"}
        ]
        srt = engine.generate_srt(styled_seg)
        vtt = engine.generate_vtt(styled_seg)

        self.assertIn("<i>ข้อความตัวเอียง</i> และ <b>ตัวหนา</b>", srt)
        self.assertIn("<i>ข้อความตัวเอียง</i> และ <b>ตัวหนา</b>", vtt)

    def test_cue_text_containing_literal_timecode_arrow(self):
        """Verifies text containing literal '-->' does not corrupt cue headers."""
        arrow_seg = [
            {"id": 1, "start": 1.0, "end": 2.0, "thai_text": "เดินทางจาก A --> B สำเร็จ"}
        ]
        srt = engine.generate_srt(arrow_seg)
        lines = srt.strip().split("\n")
        self.assertEqual(lines[0], "1")
        self.assertTrue("-->" in lines[1])
        self.assertEqual(lines[2], "เดินทางจาก A --> B สำเร็จ")

    def test_extremely_long_cue_text(self):
        """Verifies 4,000-character single subtitle cue is serialized without truncation."""
        long_text = "คำบรรยายยาวมาก " * 250
        seg = [{"id": 1, "start": 0.0, "end": 10.0, "thai_text": long_text}]
        srt = engine.generate_srt(seg)
        self.assertIn(long_text.strip(), srt)

    def test_mixed_newlines_normalization(self):
        """Verifies mixed \\r\\n and \\n in cue text are handled cleanly."""
        mixed_seg = [
            {"id": 1, "start": 1.0, "end": 3.0, "thai_text": "บรรทัดแรก\r\nบรรทัดสอง\nบรรทัดสาม"}
        ]
        srt = engine.generate_srt(mixed_seg)
        self.assertIn("บรรทัดแรก\r\nบรรทัดสอง\nบรรทัดสาม", srt)

    def test_zero_length_segments_produces_valid_headers(self):
        """Verifies empty segment export produces empty string for SRT and valid header for VTT."""
        self.assertEqual(engine.generate_srt([]), "")
        self.assertEqual(engine.generate_vtt([]).strip(), "WEBVTT")

    def test_thai_diacritics_tone_marks_utf8_byte_count(self):
        """Verifies Thai stacked tone marks (ไม้เอก, ไม้โท, สระบน) encode cleanly to valid UTF-8."""
        complex_thai = "ผู้เฒ่าดื่มน้ำผึ้งในถ้ำลึก"
        seg = [{"id": 1, "start": 1.0, "end": 4.0, "thai_text": complex_thai}]
        srt = engine.generate_srt(seg)
        utf8_bytes = srt.encode("utf-8")
        # Each Thai char is 3 bytes in UTF-8
        self.assertTrue(len(utf8_bytes) > len(complex_thai))
        decoded = utf8_bytes.decode("utf-8")
        self.assertIn(complex_thai, decoded)
        assert_zero_emojis(decoded, "complex Thai text")

if __name__ == "__main__":
    unittest.main()
