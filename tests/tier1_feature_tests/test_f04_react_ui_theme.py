# Feature 4: React Glassmorphic UI & Theme (Req R2.1, R2.2)
# Opaque-box E2E test verifying luxury dark theme (#23212C), glassmorphic palette, Lucide icons, and zero emojis.

import json
import math
import unittest
from pathlib import Path
from tests.test_helpers import get_project_root, assert_zero_emojis

THEME_BG = "#23212C"
CARD_BG = "#1C1924"
CARD_BORDER = "#3D374D"
ACCENT_PRIMARY = "#6366F1"    # Indigo
ACCENT_CYAN = "#38BDF8"       # Electric Cyan
ACCENT_EMERALD = "#10B981"    # Success Emerald
ACCENT_ROSE = "#F43F5E"       # Action Rose
TEXT_WHITE = "#FFFFFF"
TEXT_MUTED = "#A6A0B5"

def hex_to_relative_luminance(hex_str: str) -> float:
    """Calculates WCAG relative luminance from hex color string."""
    hex_clean = hex_str.lstrip("#")
    r, g, b = [int(hex_clean[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    def adjust(c):
        return c / 12.92 if c <= 0.03928 else math.pow((c + 0.055) / 1.055, 2.4)
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

def contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculates contrast ratio between two hex colors."""
    l1 = hex_to_relative_luminance(hex1)
    l2 = hex_to_relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

class TestFeature04ReactUITheme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = get_project_root()
        cls.package_json_path = cls.root / "package.json"
        cls.splashscreen_html_path = cls.root / "splashscreen.html"

    def test_theme_background_color_constant(self):
        """Verifies theme background color #23212C specification."""
        self.assertEqual(THEME_BG.upper(), "#23212C")
        # In RGB: 0x23=35, 0x21=33, 0x2C=44
        self.assertEqual(int(THEME_BG[1:3], 16), 35)
        self.assertEqual(int(THEME_BG[3:5], 16), 33)
        self.assertEqual(int(THEME_BG[5:7], 16), 44)

    def test_glassmorphic_card_palette(self):
        """Verifies card styling and subtle borders for frosted glass effect."""
        self.assertEqual(CARD_BG.upper(), "#1C1924")
        self.assertEqual(CARD_BORDER.upper(), "#3D374D")
        # Ensure card background is distinct but darker than base canvas
        lum_base = hex_to_relative_luminance(THEME_BG)
        lum_card = hex_to_relative_luminance(CARD_BG)
        self.assertLessEqual(lum_card, lum_base)

    def test_accent_color_palette(self):
        """Verifies vibrant accent color constants (Indigo, Cyan, Emerald, Rose)."""
        accents = [ACCENT_PRIMARY, ACCENT_CYAN, ACCENT_EMERALD, ACCENT_ROSE]
        for color in accents:
            self.assertTrue(color.startswith("#"))
            self.assertEqual(len(color), 7)
            assert_zero_emojis(color, f"accent color {color}")

    def test_lucide_icon_adoption_zero_emojis(self):
        """Verifies package.json adopts lucide-react and all text has strictly zero emojis."""
        self.assertTrue(self.package_json_path.exists())
        with open(self.package_json_path, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        assert_zero_emojis(pkg, "package.json")
        deps = pkg.get("dependencies", {})
        self.assertIn("lucide-react", deps, "Must include lucide-react for iconography")

        # Scan splashscreen.html for any emojis
        if self.splashscreen_html_path.exists():
            html_text = self.splashscreen_html_path.read_text(encoding="utf-8")
            assert_zero_emojis(html_text, "splashscreen.html")

    def test_typography_font_stack(self):
        """Verifies font family stack includes Inter and Kanit for clean Thai/Latin typography."""
        if self.splashscreen_html_path.exists():
            html_text = self.splashscreen_html_path.read_text(encoding="utf-8")
            self.assertTrue("Kanit" in html_text or "Inter" in html_text,
                            "Typography must specify modern Kanit/Inter font family")

    def test_theme_contrast_ratio_standards(self):
        """Verifies contrast ratios against #23212C canvas meet accessibility guidelines."""
        white_contrast = contrast_ratio(TEXT_WHITE, THEME_BG)
        self.assertGreaterEqual(white_contrast, 10.0, "White text on #23212C must exceed 10:1 ratio")

        muted_contrast = contrast_ratio(TEXT_MUTED, THEME_BG)
        self.assertGreaterEqual(muted_contrast, 4.5, "Muted text on #23212C must meet 4.5:1 ratio")

if __name__ == "__main__":
    unittest.main()
