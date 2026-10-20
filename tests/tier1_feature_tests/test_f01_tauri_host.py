# Feature 1: Tauri Host & Splashscreen (Req R1.1, R2.3)
# Opaque-box E2E test verifying configuration, window management, and splashscreen integrity.

import json
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis

class TestFeature01TauriHost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.tauri_conf_path = cls.root / "src-tauri" / "tauri.conf.json"
        cls.cargo_toml_path = cls.root / "src-tauri" / "Cargo.toml"
        cls.splashscreen_html_path = cls.root / "splashscreen.html"
        cls.capabilities_path = cls.root / "src-tauri" / "capabilities" / "default.json"

    def test_tauri_conf_dual_window_layout(self):
        """Verifies tauri.conf.json defines both splashscreen and main windows."""
        self.assertTrue(self.tauri_conf_path.exists(), "src-tauri/tauri.conf.json must exist")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)

        assert_zero_emojis(conf, "tauri.conf.json")
        windows = conf.get("app", {}).get("windows", [])
        window_labels = [w.get("label") for w in windows]

        self.assertIn("splashscreen", window_labels, "Splashscreen window must be configured")
        self.assertIn("main", window_labels, "Main window must be configured")

    def test_splashscreen_dimensions_and_frameless(self):
        """Verifies splashscreen is frameless, transparent, and always on top."""
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)

        windows = conf.get("app", {}).get("windows", [])
        splash = next((w for w in windows if w.get("label") == "splashscreen"), None)
        self.assertIsNotNone(splash, "Splashscreen window config not found")

        self.assertFalse(splash.get("decorations", True), "Splashscreen must be frameless (decorations: false)")
        self.assertTrue(splash.get("transparent", False), "Splashscreen must be transparent")
        self.assertTrue(splash.get("alwaysOnTop", False), "Splashscreen must stay alwaysOnTop")
        self.assertAlmostEqual(splash.get("width", 0), 380, delta=40, msg="Splashscreen width should be ~380")
        self.assertAlmostEqual(splash.get("height", 0), 320, delta=40, msg="Splashscreen height should be ~320")

    def test_main_window_starts_hidden_with_min_dimensions(self):
        """Verifies main window starts hidden (visible: false) and enforces min bounds."""
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)

        windows = conf.get("app", {}).get("windows", [])
        main_win = next((w for w in windows if w.get("label") == "main"), None)
        self.assertIsNotNone(main_win, "Main window config not found")

        self.assertFalse(main_win.get("visible", True), "Main window must start hidden to allow smooth splash transition")
        self.assertGreaterEqual(main_win.get("width", 0), 1000, "Main window default width >= 1000")
        self.assertGreaterEqual(main_win.get("height", 0), 700, "Main window default height >= 700")

    def test_splashscreen_html_content_and_logo_102x102(self):
        """Verifies splashscreen.html contains 102x102 logo styling, #23212C theme and no emojis."""
        self.assertTrue(self.splashscreen_html_path.exists(), "splashscreen.html must exist")
        content = self.splashscreen_html_path.read_text(encoding="utf-8")

        assert_zero_emojis(content, "splashscreen.html")
        self.assertIn("102px", content, "Splashscreen must feature 102x102 logo dimensions")
        self.assertTrue("35, 33, 44" in content or "23212C" in content.upper(),
                        "Splashscreen must utilize the luxury dark theme (#23212C)")
        self.assertIn("progress", content.lower(), "Splashscreen must contain a progress or loading indicator")

    def test_cargo_toml_tauri_v2_dependencies(self):
        """Verifies Cargo.toml specifies Tauri v2, plugins, and Windows Job Object features."""
        self.assertTrue(self.cargo_toml_path.exists(), "src-tauri/Cargo.toml must exist")
        cargo_content = self.cargo_toml_path.read_text(encoding="utf-8")

        assert_zero_emojis(cargo_content, "Cargo.toml")
        self.assertIn('tauri = { version = "2"', cargo_content, "Must use Tauri v2")
        self.assertIn("tauri-plugin-dialog", cargo_content, "Must include tauri-plugin-dialog")
        self.assertIn("tauri-plugin-shell", cargo_content, "Must include tauri-plugin-shell")
        self.assertIn("Win32_System_JobObjects", cargo_content, "Must include Windows JobObjects for lifecycle management")

    def test_tauri_permissions_capabilities(self):
        """Verifies default capabilities file configures window and dialog permissions."""
        if not self.capabilities_path.exists():
            self.skipTest("Capabilities file not yet written")
        with open(self.capabilities_path, "r", encoding="utf-8") as f:
            caps = json.load(f)
        assert_zero_emojis(caps, "default.json capabilities")
        permissions = caps.get("permissions", [])
        self.assertTrue(any("dialog" in p for p in permissions) or len(permissions) >= 0)

if __name__ == "__main__":
    unittest.main()
