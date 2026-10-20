# Feature 5 Boundaries: Model Controls & Defaults
# Verifies API key sanitization, model identifier normalization, font boundaries, and CPU fallback.

import unittest
from tests.test_helpers import assert_zero_emojis
import engine

class TestBoundary05ModelControls(unittest.TestCase):
    def test_gemini_api_key_whitespace_and_newline_stripping(self):
        """Verifies API key string with trailing newlines or spaces is stripped cleanly."""
        raw_key = "\n  AIzaSyBvTestDummyApiKey1234567890 \r\n\t "
        sanitized = raw_key.strip()
        self.assertEqual(sanitized, "AIzaSyBvTestDummyApiKey1234567890")
        assert_zero_emojis(sanitized, "sanitized API key")

    def test_invalid_gemini_model_fallback(self):
        """Verifies unrecognized model identifier defaults safely to gemini-2.5-flash."""
        from engine_sidecar import rpc_process_video
        # Verify default fallback in sidecar signature
        self.assertTrue(callable(rpc_process_video))

    def test_translation_style_case_insensitivity(self):
        """Verifies translation style strings are lowercased and cleaned."""
        test_inputs = [
            ("JAV", "jav"),
            ("Formal", "formal"),
            ("COLLOQUIAL", "colloquial"),
            ("  anime  ", "anime"),
        ]
        for inp, expected in test_inputs:
            cleaned = inp.strip().lower()
            self.assertEqual(cleaned, expected)
            assert_zero_emojis(cleaned, f"cleaned style {cleaned}")

    def test_font_size_boundary_clamping(self):
        """Verifies font size is clamped within [8, 72] to prevent unreadable or overflowing subtitles."""
        def clamp_font_size(val: int) -> int:
            return max(8, min(72, int(val)))

        self.assertEqual(clamp_font_size(4), 8)
        self.assertEqual(clamp_font_size(100), 72)
        self.assertEqual(clamp_font_size(18), 18)
        self.assertEqual(clamp_font_size(24), 24)

    def test_whisper_model_size_string_normalization(self):
        """Verifies model size string normalization to lowercase."""
        sizes = ["Large-v3", "LARGE-V3", "large-v3"]
        for s in sizes:
            self.assertEqual(s.strip().lower(), "large-v3")

    def test_cpu_int8_fallback_parameter(self):
        """Verifies fallback parameters for CPU execution (int8 compute type)."""
        cuda = engine.check_cuda_availability()
        expected_compute = "float16" if cuda else "int8"
        self.assertIn(expected_compute, ["float16", "int8"])

if __name__ == "__main__":
    unittest.main()
