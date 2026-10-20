# Project: SubFynn Standalone Desktop .EXE Architecture

## Architecture Overview
SubFynn is an AI-powered Thai subtitle generation desktop application for Windows, featuring a modern `#23212C` theme, zero emojis, Whisper Large-v3 default speech recognition, specialized Google Gemini translation models, an interactive subtitle editor, and FFmpeg hardsub/softsub video export.

```
+---------------------------------------------------------------------------------------------------+
|                                     SUBFYNN DESKTOP ARCHITECTURE                                  |
|                                                                                                   |
|  [ User Drag & Drop / Double Click ]                                                              |
|        |                                                                                          |
|        v                                                                                          |
|  [ SubFynn.exe / main.py ]                                                                        |
|        |                                                                                          |
|        +---> [ Desktop GUI: gui.py (CustomTkinter #23212C Theme) ]                                |
|                   |                                                                               |
|                   |-- Video Selector & Metadata                                                   |
|                   |-- Model Configuration:                                                        |
|                   |     * Whisper STT (Locked to Large-v3 Precision)                              |
|                   |     * 3 Specialized Translation Models (Live Translate / Cloud LLM / Adaptive)|
|                   |     * JAV & General Translation Styles                                        |
|                   |-- Interactive Subtitle Editor (Live text box, +0.5s / -0.5s time shift)        |
|                   |-- FFmpeg Subtitle Burn-in & Output Management                                 |
|                   |                                                                               |
|                   v (Non-blocking Thread)                                                         |
|             [ Processing Engine: engine.py ]                                                      |
|                   |-- 1. FFmpeg Audio Demux (16kHz mono WAV)                                      |
|                   |-- 2. faster-whisper STT (Large-v3 CUDA / CPU fallback)                         |
|                   |-- 3. Google Gemini Specialized Translation (BLOCK_NONE, JSON)                 |
|                   |-- 4. JAV & Thai Post-processing & Moan Filter                                 |
|                   |-- 5. Subtitle Serialization (SRT / VTT with Millisecond Timing)               |
|                   |-- 6. FFmpeg Hardsub / Softsub Direct Muxing                                   |
|                   |                                                                               |
|                   v                                                                               |
|             [ Local Outputs ] -> Video with Subtitles (.mp4) + Subtitle Files (.srt, .vtt)        |
+---------------------------------------------------------------------------------------------------+
```

---

## Component Inventory

| Component | Path | Responsibility |
|-----------|------|----------------|
| **Executable Entrypoint** | `main.py` | Sets up Windows UTF-8 / CP65001 console, parses dragged video argument, launches `ThaiSubtitleApp` |
| **Desktop GUI** | `gui.py` | Modern `#23212C` CustomTkinter interface, zero emojis, Whisper Large-v3 default, 3 specialized Gemini models, subtitle editor, time shift, burn-in |
| **Processing Engine** | `engine.py` | FFmpeg audio extraction, faster-whisper transcription, Google Gemini translation with fallback chain, Thai text cleanup, SRT/VTT generation, subtitle burn-in |
| **Icon Assets** | `assets/` | Multi-resolution `app_icon.ico` (256, 128, 64, 48, 32, 16) and `app_icon.png` (512x512) |
| **Build Configuration** | `subfynn.spec` | PyInstaller spec bundling `main.py`, `gui.py`, `engine.py`, `assets/`, `ffmpeg.exe`, `ffprobe.exe` with custom icon |
| **Build Automation** | `build_exe.py` | Automates PyInstaller build, copies binaries and assets, creates portable zip `dist/SubFynn-Windows-Portable.zip` |
| **Launchers** | `start_app.bat` | Clean Windows batch file for launching `SubFynn.exe` or `main.py` |
| **Unit Test Suites** | `test_engine.py`, `test_gui_and_main.py` | 44 automated unit tests verifying media pipelines, translations, GUI state, and routing |
