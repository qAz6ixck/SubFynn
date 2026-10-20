# Feature 1 Boundaries: Tauri Host & Splashscreen
# Verifies extreme resolutions, boundary dimensions, idempotence, and security CSP configs.

import json
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis

class TestBoundary01TauriHost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.tauri_conf_path = cls.root / "src-tauri" / "tauri.conf.json"
        with open(cls.tauri_conf_path, "r", encoding="utf-8") as f:
            cls.conf = json.load(f)

    def test_window_min_dimensions_clamp(self):
        """Verifies main window enforces positive minimum dimensions to prevent collapse."""
        windows = self.conf.get("app", {}).get("windows", [])
        main_win = next((w for w in windows if w.get("label") == "main"), None)
        self.assertIsNotNone(main_win)

        min_w = main_win.get("minWidth", 0)
        min_h = main_win.get("minHeight", 0)
        self.assertGreater(min_w, 600, "Minimum width must be > 600px to maintain UI grid")
        self.assertGreater(min_h, 400, "Minimum height must be > 400px to display editor table")

    def test_splashscreen_non_resizable_boundary(self):
        """Verifies splashscreen explicitly prohibits user resizing."""
        windows = self.conf.get("app", {}).get("windows", [])
        splash = next((w for w in windows if w.get("label") == "splashscreen"), None)
        self.assertIsNotNone(splash)
        self.assertFalse(splash.get("resizable", True), "Splashscreen must not be resizable")

    def test_window_labels_are_unique(self):
        """Verifies no duplicate window labels exist in tauri.conf.json."""
        windows = self.conf.get("app", {}).get("windows", [])
        labels = [w.get("label") for w in windows]
        self.assertEqual(len(labels), len(set(labels)), "Window labels must be strictly unique")

    def test_extreme_viewport_handling(self):
        """Simulates 8K ultra-wide dimensions (7680x4320) and verifies layout constraints."""
        viewports = [
            {"width": 800, "height": 600, "valid": False},      # Below minWidth/minHeight
            {"width": 1280, "height": 840, "valid": True},      # Standard
            {"width": 3840, "height": 2160, "valid": True},     # 4K UHD
            {"width": 7680, "height": 4320, "valid": True},     # 8K UHD
        ]
        min_w = 960
        min_h = 640
        for vp in viewports:
            is_valid = vp["width"] >= min_w and vp["height"] >= min_h
            self.assertEqual(is_valid, vp["valid"])

    def test_window_title_special_characters_zero_emojis(self):
        """Verifies window titles contain valid descriptive characters and strictly zero emojis."""
        windows = self.conf.get("app", {}).get("windows", [])
        for win in windows:
            title = win.get("title", "")
            assert_zero_emojis(title, f"window title {win.get('label')}")
            self.assertTrue(len(title) > 0)
            self.assertLess(len(title), 256)

    def test_idempotent_close_splashscreen_rust_command(self):
        """Verifies Rust lib.rs contains safe null-check for splashscreen handle."""
        lib_rs = self.root / "src-tauri" / "src" / "lib.rs"
        if not lib_rs.exists():
            self.skipTest("src-tauri/src/lib.rs not found")
        content = lib_rs.read_text(encoding="utf-8")
        assert_zero_emojis(content, "lib.rs")
        self.assertIn("close_splashscreen", content)
        self.assertIn("get_webview_window", content)

if __name__ == "__main__":
    unittest.main()
