# SubFynn Standalone Desktop .exe Redesign Spec

**Date:** 2026-10-20
**Status:** Approved by User

## 1. Goal
Transition SubFynn from a bloated multi-interface repository (web app, CLI, intro motion graphics) into a single, dedicated, ultra-modern Windows Desktop application (`SubFynn.exe`).

## 2. Requirements & Architecture

### 2.1 Interface & Aesthetic
- **Single Mode**: Desktop GUI application only. No CLI commands or web servers.
- **Theme**: Deep modern dark theme with `#23212C` primary background.
- **Emoji Free**: 100% removal of all Unicode emojis across the entire UI and terminal output to prevent Windows console CP874 encoding crashes and maintain a sleek, professional aesthetic.
- **Branding & Icon**: Custom multi-resolution Windows icon (`assets/app_icon.ico` with 256, 128, 64, 48, 32, 16 sizes and `assets/app_icon.png` 512x512) embedded in the executable and window title bar.
- **Typography**: Clean Kanit / Segoe UI typography with crisp contrast.

### 2.2 Speech-to-Text (STT) Engine
- **Whisper Model**: Locked to **Large-v3** as default (no confusing options dropdown; displays clean badge "Whisper Large-v3 (Precision AI)").
- Device selection (CUDA GPU if available, else CPU) and language detection intact.

### 2.3 Translation Models
Offer the 3 latest specialized Gemini models with concise descriptions and automatic fallback:
1. **Gemini Live Translate** (`gemini-3.5-live-translate-preview`): Ultra-low latency specialized translation model for dialogues.
2. **Cloud Translation LLM** (`cloud-translation-llm` / `gemini-2.5-pro`): High-context conversational nuance and slang understanding.
3. **Gemini Adaptive Translation** (`gemini-2.5-flash`): Adaptive tone and natural Thai subtitle flow.
Fallback chain: Requested -> gemini-2.5-flash -> gemini-2.0-flash -> Free Lexicon translation.

### 2.4 Interactive Subtitle Editor & Video Operations
- **Editable Subtitle Table**: Display segments (Start, End, Original Text, Thai Translation).
- **Inline Text Editor**: Quick editing of selected segment with instant save/update.
- **Time Shifting**: Global offset adjustments (`+0.5s`, `-0.5s`, or custom offset).
- **Video Actions**:
  - Drag-and-drop or Browse video file.
  - Generate Subtitles (runs in non-blocking background thread with progress bar and status).
  - Export SRT and VTT.
  - Burn-in Subtitles into MP4 via FFmpeg with progress indicator.
  - Open Output Folder button.

### 2.5 Clean Build & Packaging
- Clean `subfynn.spec` and `build_exe.py` targeting `main.py` -> `gui.py`.
- Bundle `ffmpeg.exe`, `ffprobe.exe`, `assets/app_icon.ico`, and `data/`.
- Compile to `dist/SubFynn/SubFynn.exe` and package `dist/SubFynn-Windows-Portable.zip`.
