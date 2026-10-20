# SubFynn Desktop .exe Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform SubFynn into a dedicated, standalone Windows Desktop `.exe` application with a modern `#23212C` theme, zero emojis, Whisper Large-v3 default, 3 specialized Gemini models, interactive subtitle editor, custom icon, and zero web/CLI/video bloat.

**Architecture:** A single desktop entry point (`main.py`) running a CustomTkinter GUI (`gui.py`) backed by `engine.py` for Whisper STT, Gemini LLM translation, and FFmpeg burning, packaged with PyInstaller into `dist/SubFynn/SubFynn.exe`.

**Tech Stack:** Python 3.10+, CustomTkinter, Tkinter, Pillow (PIL), faster-whisper, google-genai, FFmpeg, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-20-subfynn-desktop-exe-redesign.md`

## Global Constraints
- Pure desktop execution only — no CLI or web server modules.
- Zero emojis anywhere in GUI strings or console output.
- Theme background `#23212C`.
- Whisper Large-v3 default.
- Custom application icon embedded in `.exe`.

## Review Focus
1. Video file with spaces or special characters loaded into GUI.
2. UTF-8 console output handling on Windows CP874 without emoji crashes.
3. Subtitle timing adjustment preserves sub-second millisecond formatting.
4. FFmpeg subtitle burning properly handles escaping and temp directories on Windows.
5. PyInstaller spec bundles FFmpeg, ffprobe, and application icon.

---

### Task 1: Generate High-Resolution Application Icon
- [ ] Create Python script to generate sleek 512x512 glowing waveform & subtitle logo.
- [ ] Save to `assets/app_icon.png` and multi-resolution `assets/app_icon.ico` (256, 128, 64, 48, 32, 16).

### Task 2: Remove Web App, CLI, and Video Intro Bloat
- [ ] Remove `cli.py`, `app.py`, `api/`, `vercel.json`, `start_web.bat`, `start_tunnel.bat`, `tunnel.py`, `public/`.
- [ ] Remove `test_app.py`, `subfynn_intro.mp4`, `assets/subfynn_intro.mp4`, `intro_video/`.
- [ ] Remove `cloudflared.exe`.

### Task 3: Update Engine Translation Models & Fallbacks
- [ ] Update `engine.py` to support `gemini-3.5-live-translate-preview`, `cloud-translation-llm`, and `gemini-2.5-flash`.
- [ ] Ensure safe fallback chain down to `gemini-2.5-flash` / `gemini-2.0-flash`.

### Task 4: Complete Desktop GUI Redesign (`gui.py`)
- [ ] Redesign `gui.py` with CustomTkinter and `#23212C` theme.
- [ ] Set Whisper Large-v3 as default STT model.
- [ ] Add the 3 specialized Gemini translation models.
- [ ] Implement interactive subtitle editor (table view, segment editing, time shifting).
- [ ] Implement video drag-drop, subtitle generation, export, and FFmpeg burn-in.
- [ ] Set `assets/app_icon.ico` as window and taskbar icon.

### Task 5: Application Entry Point & Launchers
- [ ] Simplify `main.py` to launch `gui.ThaiSubtitleApp(initial_video=...)`.
- [ ] Create `start_app.bat` with CRLF line endings and CP65001.

### Task 6: Update Tests & Verification
- [ ] Update `test_gui_and_main.py` to test redesigned GUI without web/cli.
- [ ] Verify `test_engine.py` and `test_gui_and_main.py` pass 100%.

### Task 7: Build Standalone Executable & Package
- [ ] Update `subfynn.spec` and `build_exe.py` with `assets/app_icon.ico` and FFmpeg.
- [ ] Compile `dist/SubFynn/SubFynn.exe`.
- [ ] Verify executable launches and packages into zip.
- [ ] Commit all changes to Git.
