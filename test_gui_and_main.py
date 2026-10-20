"""
Unit tests for gui.py and main.py standalone desktop routing.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import gui
from gui import ThaiSubtitleApp


class TestGuiAndMain(unittest.TestCase):
    def test_gui_initialization_no_video(self):
        app = ThaiSubtitleApp()
        self.assertEqual(app.video_path, "")
        self.assertEqual(app.file_entry.get(), "")
        # Model locked to large-v3 default
        self.assertTrue(app.model_var.get().startswith("large-v3"))
        self.assertTrue(app.style_var.get().startswith("jav"))
        self.assertTrue(app.lang_var.get().startswith("ja"))
        self.assertTrue(app.gemini_model_var.get().startswith("gemini"))
        app.update()
        app.destroy()

    def test_gui_initialization_with_initial_video(self):
        readme_path = os.path.abspath("README.md")
        app = ThaiSubtitleApp(initial_video=readme_path)
        self.assertEqual(app.video_path, readme_path)
        self.assertEqual(app.file_entry.get(), readme_path)
        self.assertIn("README.md", app.status_lbl.cget("text"))
        app.update()
        app.destroy()

    def test_gui_load_video(self):
        app = ThaiSubtitleApp()
        readme_path = os.path.abspath("README.md")
        app.load_video(readme_path)
        self.assertEqual(app.video_path, readme_path)
        self.assertEqual(app.file_entry.get(), readme_path)
        app.update()
        app.destroy()

    def test_gui_specialized_translation_models(self):
        app = ThaiSubtitleApp()
        # Verify the 3 specialized translation models are in the options menu
        values = app.gemini_model_menu.cget("values")
        self.assertEqual(len(values), 3)
        self.assertTrue(any("gemini-3.5-live-translate-preview" in v for v in values))
        self.assertTrue(any("cloud-translation-llm" in v for v in values))
        self.assertTrue(any("gemini-2.5-flash" in v for v in values))
        app.destroy()

    def test_gui_shift_time(self):
        app = ThaiSubtitleApp()
        app.last_result = {
            "segments": [
                {"id": 1, "start": 1.0, "end": 3.0, "text": "สวัสดี"}
            ],
            "srt_content": "1\n00:00:01,000 --> 00:00:03,000\nสวัสดี\n",
        }
        app.shift_time(0.5)
        self.assertAlmostEqual(app.last_result["segments"][0]["start"], 1.5)
        self.assertAlmostEqual(app.last_result["segments"][0]["end"], 3.5)
        self.assertIn("00:00:01,500 --> 00:00:03,500", app.srt_textbox.get("1.0", "end"))
        app.destroy()

    def test_main_routing_gui_default(self):
        import main
        with patch.object(sys, "argv", ["main.py"]):
            with patch("gui.ThaiSubtitleApp") as mock_app_class:
                mock_instance = MagicMock()
                mock_app_class.return_value = mock_instance
                main.main()
                mock_app_class.assert_called_once_with(initial_video=None)
                mock_instance.mainloop.assert_called_once()

    def test_main_routing_gui_with_drag_drop_video(self):
        import main
        with patch.object(sys, "argv", ["SubFynn.exe", "my_movie.mp4"]):
            with patch.object(sys, "executable", "C:\\dist\\SubFynn\\SubFynn.exe"):
                with patch("gui.ThaiSubtitleApp") as mock_app_class:
                    mock_instance = MagicMock()
                    mock_app_class.return_value = mock_instance
                    main.main()
                    mock_app_class.assert_called_once_with(initial_video="my_movie.mp4")
                    mock_instance.mainloop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
