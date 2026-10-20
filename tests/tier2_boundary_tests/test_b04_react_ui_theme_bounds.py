# Feature 4 Boundaries: React Glassmorphic UI & Theme
# Verifies zero emoji enforcement across UI source files, hex boundary parsing, and contrast bounds.

import os
import re
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, contains_emoji, assert_zero_emojis
from tests.tier1_feature_tests.test_f04_react_ui_theme import contrast_ratio, THEME_BG

HEX_COLOR_REGEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

class TestBoundary04ReactUITheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()

    def test_strict_zero_emoji_scan_of_frontend_source(self):
        """Recursively scans all frontend sources and html files for strictly zero emojis."""
        scan_extensions = {".tsx", ".ts", ".jsx", ".js", ".html", ".css", ".json"}
        candidate_dirs = [self.root / "src", self.root / "assets"]
        scanned_files = 0

        # Also check root html/configs
        root_files = [self.root / "splashscreen.html", self.root / "package.json"]
        for rf in root_files:
            if rf.exists():
                text = rf.read_text(encoding="utf-8", errors="ignore")
                self.assertFalse(contains_emoji(text), f"Emoji found in {rf.name}")
                scanned_files += 1

        for cdir in candidate_dirs:
            if not cdir.exists():
                continue
            for p in cdir.rglob("*"):
                if p.is_file() and p.suffix.lower() in scan_extensions:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    self.assertFalse(contains_emoji(text), f"Emoji found in {p.relative_to(self.root)}")
                    scanned_files += 1

        self.assertGreater(scanned_files, 0, "Must have scanned at least 1 frontend/asset file")

    def test_hex_color_validation_boundaries(self):
        """Verifies hex color validation across 3-digit, 6-digit, and 8-digit formats."""
        valid_hex = ["#fff", "#FFF", "#23212C", "#1C1924", "#3D374D", "#23212CFA", "#6366F1"]
        for h in valid_hex:
            self.assertTrue(bool(HEX_COLOR_REGEX.match(h)), f"Valid hex rejected: {h}")

        invalid_hex = ["23212C", "#23212", "#23212CGG", "red", "#", ""]
        for h in invalid_hex:
            self.assertFalse(bool(HEX_COLOR_REGEX.match(h)), f"Invalid hex accepted: {h}")

    def test_contrast_ratio_boundary_values(self):
        """Verifies contrast ratio edge cases (min 1.0, max 21.0)."""
        same_color = contrast_ratio("#23212C", "#23212C")
        self.assertAlmostEqual(same_color, 1.0, places=1)

        black_white = contrast_ratio("#000000", "#FFFFFF")
        self.assertAlmostEqual(black_white, 21.0, delta=0.5)

    def test_dim_text_contrast_boundary(self):
        """Verifies dim text (#7B758D) has acceptable contrast ratio against dark canvas."""
        dim_contrast = contrast_ratio("#7B758D", THEME_BG)
        # Dim text should have ratio >= 3.0 for secondary captions
        self.assertGreaterEqual(dim_contrast, 3.0)

    def test_backdrop_filter_css_syntax(self):
        """Verifies splashscreen.html contains standard backdrop-filter blur declaration."""
        splash = self.root / "splashscreen.html"
        if splash.exists():
            content = splash.read_text(encoding="utf-8")
            self.assertIn("backdrop-filter: blur(", content)
            self.assertIn("-webkit-backdrop-filter: blur(", content)

    def test_ambient_glow_animation_keyframes(self):
        """Verifies ambient glow pulse animation exists for smooth splashscreen loading."""
        splash = self.root / "splashscreen.html"
        if splash.exists():
            content = splash.read_text(encoding="utf-8")
            self.assertIn("@keyframes pulse-glow", content)

if __name__ == "__main__":
    unittest.main()
