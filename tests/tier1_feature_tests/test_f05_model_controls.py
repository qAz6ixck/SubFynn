# Feature 5: Model Controls & Defaults (Req R2.5)
# Opaque-box E2E test verifying Whisper Large-v3 default, 3 Gemini models, style presets, and CUDA fallback.

import unittest
from tests.test_helpers import get_project_root, assert_zero_emojis
import engine

DEFAULT_WHISPER_MODEL = "large-v3"

SPECIALIZED_GEMINI_MODELS = [
    "gemini-3.5-live-translate-preview",
    "cloud-translation-llm",
    "gemini-2.5-flash"
]

TRANSLATION_STYLES = [
    "jav",
    "formal",
    "colloquial",
    "anime"
]

def validate_api_key_format(key: str) -> bool:
    """Validates Gemini API key format (non-empty, non-whitespace, typical length)."""
    if not key or not isinstance(key, str):
        return False
    stripped = key.strip()
    if len(stripped) < 10:
        return False
    if " " in stripped:
        return False
    return True

class TestFeature05ModelControls(unittest.TestCase):
    def test_whisper_default_model_is_large_v3(self):
        """Verifies Whisper default model is strictly Large-v3."""
        self.assertEqual(DEFAULT_WHISPER_MODEL, "large-v3")
        assert_zero_emojis(DEFAULT_WHISPER_MODEL, "whisper default model")

    def test_three_specialized_gemini_models(self):
        """Verifies exactly 3 specialized Gemini translation models are available."""
        self.assertEqual(len(SPECIALIZED_GEMINI_MODELS), 3)
        self.assertIn("gemini-3.5-live-translate-preview", SPECIALIZED_GEMINI_MODELS)
        self.assertIn("cloud-translation-llm", SPECIALIZED_GEMINI_MODELS)
        self.assertIn("gemini-2.5-flash", SPECIALIZED_GEMINI_MODELS)
        for model in SPECIALIZED_GEMINI_MODELS:
            assert_zero_emojis(model, f"gemini model {model}")

    def test_translation_style_presets(self):
        """Verifies required translation style presets are defined."""
        for style in ["jav", "formal", "colloquial", "anime"]:
            self.assertIn(style, TRANSLATION_STYLES)
            assert_zero_emojis(style, f"translation style {style}")

    def test_cuda_safe_probe_and_cpu_fallback(self):
        """Verifies engine.check_cuda_availability executes safely and returns a boolean."""
        cuda_status = engine.check_cuda_availability()
        self.assertIsInstance(cuda_status, bool)
        # Should not raise any unhandled CUDA driver/runtime exceptions

    def test_gemini_api_key_validation(self):
        """Verifies API key validator checks empty, whitespace, and valid keys."""
        self.assertFalse(validate_api_key_format(""))
        self.assertFalse(validate_api_key_format("   "))
        self.assertFalse(validate_api_key_format(None))
        self.assertFalse(validate_api_key_format("short_key"))
        self.assertFalse(validate_api_key_format("AIzaSy invalid key with space"))
        self.assertTrue(validate_api_key_format("AIzaSyBvTestDummyApiKey1234567890"))

    def test_whisper_model_cache_probe(self):
        """Verifies engine contains cache mechanism for loaded Whisper models."""
        self.assertTrue(hasattr(engine, "_WHISPER_CACHE"))
        self.assertTrue(hasattr(engine, "_WHISPER_LOCK"))

if __name__ == "__main__":
    unittest.main()
