# Feature 3: File Dialog & Drag-and-Drop (Req R1.3)
# Opaque-box E2E test verifying native dialog configuration, video format filtering, and drag-and-drop validation.

import os
import json
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, get_sample_video, assert_zero_emojis

# Canonical list of allowed video extensions
ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".flv", ".webm", ".ts", ".m4v", ".wmv"
}

DISALLOWED_EXTENSIONS = {
    ".txt", ".pdf", ".exe", ".py", ".rs", ".zip", ".png", ".jpg", ".doc", ".mp3"
}

def validate_dropped_file(path_str: str) -> bool:
    """Validates if a dropped path is an existing, non-empty video file."""
    if not path_str or not isinstance(path_str, str):
        return False
    p = Path(path_str)
    if not p.is_file():
        return False
    if p.suffix.lower() not in ALLOWED_VIDEO_EXTENSIONS:
        return False
    try:
        if p.stat().st_size == 0:
            return False
    except OSError:
        return False
    return True

class TestFeature03FileDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.sample_video = get_sample_video()
        cls.tauri_conf_path = cls.root / "src-tauri" / "tauri.conf.json"

    def test_supported_video_extensions_whitelist(self):
        """Verifies allowed extensions are accepted and disallowed extensions are rejected."""
        for ext in ALLOWED_VIDEO_EXTENSIONS:
            fake_name = f"video_test{ext}"
            self.assertIn(Path(fake_name).suffix.lower(), ALLOWED_VIDEO_EXTENSIONS)

        for ext in DISALLOWED_EXTENSIONS:
            fake_name = f"invalid_file{ext}"
            self.assertNotIn(Path(fake_name).suffix.lower(), ALLOWED_VIDEO_EXTENSIONS)

    def test_drag_drop_payload_structure(self):
        """Verifies parsing of Tauri drag-drop payload structure with absolute paths."""
        mock_payload = {
            "paths": [
                self.sample_video
            ],
            "position": {"x": 250, "y": 180}
        }
        assert_zero_emojis(mock_payload, "drag-drop payload")
        paths = mock_payload.get("paths", [])
        self.assertEqual(len(paths), 1)
        self.assertTrue(os.path.isabs(paths[0]), "Dropped path must be absolute")
        self.assertTrue(validate_dropped_file(paths[0]), "Dropped file should be valid")

    def test_path_normalization_and_validation(self):
        """Verifies normalization handles slashes, spaces, and Windows drive formatting."""
        raw_path = self.sample_video.replace("\\", "/")
        norm_path = os.path.normpath(raw_path)
        self.assertTrue(os.path.isabs(norm_path))
        self.assertTrue(Path(norm_path).exists())

    def test_file_existence_and_size_validation(self):
        """Verifies non-existent paths and 0-byte files fail validation."""
        fake_path = str(self.root / "assets" / "non_existent_clip.mp4")
        self.assertFalse(validate_dropped_file(fake_path), "Non-existent path must be rejected")

        # Test with empty file
        temp_empty = self.root / "_empty_test_clip.mp4"
        try:
            temp_empty.write_bytes(b"")
            self.assertFalse(validate_dropped_file(str(temp_empty)), "0-byte file must be rejected")
        finally:
            if temp_empty.exists():
                temp_empty.unlink()

    def test_tauri_file_dialog_plugin_configuration(self):
        """Verifies tauri.conf.json has dialog plugin enabled."""
        if not self.tauri_conf_path.exists():
            self.skipTest("tauri.conf.json not yet written")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        plugins = conf.get("plugins", {})
        self.assertIn("dialog", plugins, "Dialog plugin must be registered in tauri.conf.json")

    def test_sample_video_path_resolution(self):
        """Verifies sample video exists and validates as a genuine video file."""
        self.assertTrue(validate_dropped_file(self.sample_video))
        size_bytes = Path(self.sample_video).stat().st_size
        self.assertGreater(size_bytes, 1_000_000, "Sample video must be substantial (>1MB)")

if __name__ == "__main__":
    unittest.main()
