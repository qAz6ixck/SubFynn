# Feature 11: Standalone Packaging & Icon (Req R3.1, R3.2)
# Opaque-box E2E test verifying icon resolutions, bundled FFmpeg binaries, and bundle configurations.

import sys
import json
import struct
import unittest
import subprocess
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis

class TestFeature11PackagingIcon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.ico_path = cls.root / "assets" / "app_icon.ico"
        cls.png_path = cls.root / "assets" / "app_icon.png"
        cls.ffmpeg_path = cls.root / "ffmpeg.exe"
        cls.ffprobe_path = cls.root / "ffprobe.exe"
        cls.tauri_conf_path = cls.root / "src-tauri" / "tauri.conf.json"

    def test_app_icon_ico_contains_required_resolutions(self):
        """Verifies assets/app_icon.ico contains multi-resolution icons."""
        self.assertTrue(self.ico_path.is_file(), "assets/app_icon.ico must exist")
        data = self.ico_path.read_bytes()

        # ICO header: 2 bytes reserved (0), 2 bytes type (1=icon), 2 bytes count
        reserved, ico_type, count = struct.unpack("<HHH", data[:6])
        self.assertEqual(reserved, 0)
        self.assertEqual(ico_type, 1)
        self.assertGreaterEqual(count, 4, "Must contain at least 4 embedded resolutions")

        sizes = []
        for i in range(count):
            entry_offset = 6 + i * 16
            width = data[entry_offset]
            height = data[entry_offset + 1]
            # In ICO format, 0 means 256px
            w = 256 if width == 0 else width
            h = 256 if height == 0 else height
            sizes.append((w, h))

        # Check required standard Windows resolutions
        expected_resolutions = [(16, 16), (32, 32), (48, 48), (256, 256)]
        for exp in expected_resolutions:
            self.assertIn(exp, sizes, f"Resolution {exp} must be present in .ico")

    def test_app_icon_png_master_dimensions(self):
        """Verifies assets/app_icon.png exists and has 512x512 master resolution."""
        self.assertTrue(self.png_path.is_file(), "assets/app_icon.png must exist")
        data = self.png_path.read_bytes()
        # PNG signature
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        # IHDR width and height at offset 16-24
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual(width, 512)
        self.assertEqual(height, 512)

    def test_bundled_ffmpeg_and_ffprobe_exist_and_executable(self):
        """Verifies bundled FFmpeg 9.0 binaries exist in project root and are executable."""
        self.assertTrue(self.ffmpeg_path.is_file(), "ffmpeg.exe must exist in project root")
        self.assertTrue(self.ffprobe_path.is_file(), "ffprobe.exe must exist in project root")

        flags = 0x08000000 if sys.platform == "win32" else 0
        proc_f = subprocess.run([str(self.ffmpeg_path), "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
        self.assertEqual(proc_f.returncode, 0)
        self.assertIn("ffmpeg version", proc_f.stdout)

        proc_p = subprocess.run([str(self.ffprobe_path), "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
        self.assertEqual(proc_p.returncode, 0)
        self.assertIn("ffprobe version", proc_p.stdout)

    def test_tauri_conf_bundle_resources_include_ffmpeg(self):
        """Verifies tauri.conf.json bundle.resources includes ffmpeg and ffprobe."""
        if not self.tauri_conf_path.exists():
            self.skipTest("tauri.conf.json not yet generated")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        resources = conf.get("bundle", {}).get("resources", [])
        self.assertTrue(any("ffmpeg" in r for r in resources), "bundle.resources must include ffmpeg")
        self.assertTrue(any("ffprobe" in r for r in resources), "bundle.resources must include ffprobe")

    def test_tauri_conf_bundle_icon_list(self):
        """Verifies tauri.conf.json configures application icons."""
        if not self.tauri_conf_path.exists():
            self.skipTest("tauri.conf.json not yet generated")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        icons = conf.get("bundle", {}).get("icon", [])
        self.assertGreater(len(icons), 0, "bundle.icon must specify icon paths")

    def test_product_name_and_identifier(self):
        """Verifies product metadata in tauri.conf.json."""
        if not self.tauri_conf_path.exists():
            self.skipTest("tauri.conf.json not yet generated")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        self.assertEqual(conf.get("productName"), "SubFynn")
        self.assertEqual(conf.get("identifier"), "com.subfynn.app")

if __name__ == "__main__":
    unittest.main()
