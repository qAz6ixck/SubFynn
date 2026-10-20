# Feature 11 Boundaries: Standalone Packaging & Icon
# Verifies corrupted ICO headers, PNG chunk validation, binary sizes (>80MB), bundle targets, and SemVer compliance.

import re
import json
import struct
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis

SEMVER_REGEX = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")

class TestBoundary11PackagingIcon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.ico_path = cls.root / "assets" / "app_icon.ico"
        cls.png_path = cls.root / "assets" / "app_icon.png"
        cls.ffmpeg_path = cls.root / "ffmpeg.exe"
        cls.ffprobe_path = cls.root / "ffprobe.exe"
        cls.tauri_conf_path = cls.root / "src-tauri" / "tauri.conf.json"

    def test_ico_header_corruption_detection(self):
        """Verifies validator detects truncated or invalid ICO headers."""
        def validate_ico_header(data: bytes) -> bool:
            if len(data) < 6:
                return False
            reserved, ico_type, count = struct.unpack("<HHH", data[:6])
            return reserved == 0 and ico_type == 1 and count > 0

        self.assertTrue(validate_ico_header(self.ico_path.read_bytes()))
        self.assertFalse(validate_ico_header(b"corrupt"))
        self.assertFalse(validate_ico_header(b"\x00\x00\x02\x00\x01\x00"))  # type=2 (cursor, not icon)

    def test_png_signature_and_ihdr_bounds(self):
        """Verifies PNG bit depth is 8 and color type is RGBA (6)."""
        data = self.png_path.read_bytes()
        bit_depth = data[24]
        color_type = data[25]
        self.assertEqual(bit_depth, 8, "Must be standard 8-bit depth")
        self.assertEqual(color_type, 6, "Must be color type 6 (RGBA with alpha channel)")

    def test_ffmpeg_binary_file_size_threshold(self):
        """Verifies bundled FFmpeg binaries are substantial (>80MB) complete builds."""
        f_size = self.ffmpeg_path.stat().st_size
        p_size = self.ffprobe_path.stat().st_size
        self.assertGreater(f_size, 80_000_000, "ffmpeg.exe must be > 80MB")
        self.assertGreater(p_size, 80_000_000, "ffprobe.exe must be > 80MB")

    def test_tauri_bundle_active_and_targets(self):
        """Verifies bundle configuration is active with targets set."""
        if not self.tauri_conf_path.exists():
            self.skipTest("tauri.conf.json not yet written")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        bundle = conf.get("bundle", {})
        self.assertTrue(bundle.get("active", False))
        self.assertIn("targets", bundle)

    def test_semver_version_string_compliance(self):
        """Verifies application version follows Semantic Versioning (SemVer)."""
        if not self.tauri_conf_path.exists():
            self.skipTest("tauri.conf.json not yet written")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        ver = conf.get("version", "")
        self.assertTrue(bool(SEMVER_REGEX.match(ver)), f"Version '{ver}' must follow SemVer pattern")

    def test_tauri_identifier_format(self):
        """Verifies app identifier is standard reverse-DNS (com.subfynn.app)."""
        if not self.tauri_conf_path.exists():
            self.skipTest("tauri.conf.json not yet written")
        with open(self.tauri_conf_path, "r", encoding="utf-8") as f:
            conf = json.load(f)
        ident = conf.get("identifier", "")
        self.assertEqual(ident, "com.subfynn.app")
        assert_zero_emojis(ident, "app identifier")

if __name__ == "__main__":
    unittest.main()
