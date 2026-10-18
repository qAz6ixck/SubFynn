"""
Unit tests for gui.py and main.py routing logic.
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

    def test_main_routing_web_mode(self):
        import main
        with patch.object(sys, "argv", ["SubFynn.exe", "--web", "--port", "5010"]):
            with patch("app.start_server") as mock_start_server:
                main.main()
                mock_start_server.assert_called_once_with(port=5010, open_browser=True)

    def test_gui_open_web_mode(self):
        app = ThaiSubtitleApp()
        with patch("app.start_server_in_background", return_value=5000) as mock_bg:
            with patch("webbrowser.open") as mock_open:
                app.open_web_mode()
                mock_bg.assert_called_once_with(port=5000)
                mock_open.assert_called_once_with("http://127.0.0.1:5000")
                self.assertIn("5000", app.status_lbl.cget("text"))
        app.destroy()

    def test_cli_style_and_model_args(self):
        import cli
        with patch("argparse.ArgumentParser.parse_args") as mock_parse:
            import argparse
            mock_parse.return_value = argparse.Namespace(
                video=os.path.abspath("README.md"),
                model="large-v3",
                style="jav_dirty",
                gemini_model="gemini-2.5-pro",
                lang="ja",
                gemini_key=None,
                outdir=None,
                shift_seconds=0.0,
                burn=False,
            )
            with patch("cli.process_video_subtitles") as mock_process:
                mock_process.return_value = {
                    "success": True,
                    "detected_language": "ja",
                    "segments": [],
                    "srt_path": "out.srt",
                    "vtt_path": "out.vtt",
                }
                with patch("sys.stdout"):
                    cli.main()
                mock_process.assert_called_once()
                self.assertEqual(mock_process.call_args[1]["model_size"], "large-v3")
                self.assertEqual(mock_process.call_args[1]["translation_style"], "jav_dirty")
                self.assertEqual(mock_process.call_args[1]["gemini_model"], "gemini-2.5-pro")
                self.assertEqual(mock_process.call_args[1]["source_lang"], "ja")


if __name__ == "__main__":
    unittest.main()
