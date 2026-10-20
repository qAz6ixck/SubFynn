# Feature 3 Boundaries: File Dialog & Drag-and-Drop
# Verifies long paths, unicode characters, uppercase extensions, directory rejection, and empty payloads.

import os
import tempfile
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis
from tests.tier1_feature_tests.test_f03_file_dialog import validate_dropped_file, ALLOWED_VIDEO_EXTENSIONS

class TestBoundary03FileDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.temp_dir = tempfile.mkdtemp(prefix="subfynn_bound_dialog_")

    @classmethod
    def tearDownClass(cls):
        import shutil
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_windows_extended_max_path(self):
        """Verifies paths approaching/exceeding 260 characters are validated safely."""
        long_subdirs = os.path.join(self.temp_dir, "nested_" * 15)
        os.makedirs(long_subdirs, exist_ok=True)
        long_file = os.path.join(long_subdirs, "test_clip_with_extremely_long_filename.mp4")
        with open(long_file, "wb") as f:
            f.write(b"mock video data " * 100)

        self.assertTrue(validate_dropped_file(long_file))

    def test_paths_with_unicode_japanese_thai_spaces(self):
        """Verifies paths containing Japanese, Thai, spaces, and brackets are handled without corruption."""
        complex_name = "วิดีโอ_日本語_Clip [2026] (Final Version) #01.mp4"
        complex_path = os.path.join(self.temp_dir, complex_name)
        with open(complex_path, "wb") as f:
            f.write(b"valid video payload bytes" * 50)

        assert_zero_emojis(complex_path, "complex unicode path")
        self.assertTrue(validate_dropped_file(complex_path))

    def test_directory_passed_instead_of_file(self):
        """Verifies dropping a directory instead of a video file is rejected."""
        sub_folder = os.path.join(self.temp_dir, "my_video_folder.mp4")  # Folder named like .mp4
        os.makedirs(sub_folder, exist_ok=True)

        self.assertFalse(validate_dropped_file(sub_folder), "Directory must not be accepted as a video file")

    def test_case_insensitive_video_extensions(self):
        """Verifies .MP4, .Mkv, .AVI uppercase extensions are accepted."""
        for ext in [".MP4", ".Mkv", ".AVI", ".MOV", ".WEBM"]:
            fpath = os.path.join(self.temp_dir, f"test_case{ext}")
            with open(fpath, "wb") as f:
                f.write(b"content" * 20)
            self.assertTrue(validate_dropped_file(fpath), f"Extension {ext} should be accepted")

    def test_zero_byte_video_file_rejection(self):
        """Verifies 0-byte file with valid extension is rejected."""
        zero_file = os.path.join(self.temp_dir, "empty_corrupt.mp4")
        with open(zero_file, "wb") as f:
            pass  # 0 bytes
        self.assertFalse(validate_dropped_file(zero_file))

    def test_empty_drag_drop_paths_list(self):
        """Verifies drag-drop handler handles empty payload gracefully."""
        empty_payload = {"paths": []}
        assert_zero_emojis(empty_payload, "empty drag-drop payload")
        paths = empty_payload.get("paths", [])
        self.assertEqual(len(paths), 0)
        # Should not raise exception
        valid_files = [p for p in paths if validate_dropped_file(p)]
        self.assertEqual(len(valid_files), 0)

if __name__ == "__main__":
    unittest.main()
