# Project: SubFynn Tauri v2 Rebuild

## Architecture Overview
SubFynn is rebuilt as a modern, blazing-fast standalone Windows desktop application utilizing **Tauri v2 (Rust)**, a **React 18/19 + Vite + Tailwind CSS** frontend, and a high-performance **Python Engine Sidecar** communicating via Line-Delimited JSON (NDJSON) over standard I/O.

```
+----------------------------------------------------------------------------------------------------+
|                                    SUBFYNN TAURI V2 ARCHITECTURE                                   |
|                                                                                                    |
|  [ User Drag & Drop Video / File Dialog ]                                                          |
|        |                                                                                           |
|        v                                                                                           |
|  [ React 18/19 + Vite + Tailwind CSS + Lucide Icons Frontend (#23212C, Zero Emojis) ]             |
|        |                                                                                           |
|        |-- Frameless Animated SplashScreen (102x102 SubFynn Logo, Ambient Pulsing Glow)           |
|        |-- Model Selectors: Whisper Large-v3 default, 3 Specialized Gemini Models                  |
|        |-- Interactive Live Subtitle Editor Table (+/-0.5s shift, search, instant SRT/VTT download)|
|        |-- Action Triggers: Transcribe & Translate, Soft-mux Subtitle, Hard Burn-in Video          |
|        |-- Real-time Streaming Progress Bar & Status Readout                                       |
|        |                                                                                           |
|        v (Tauri IPC invoke & event listener)                                                       |
|  [ Tauri v2 Desktop Host (Rust) ]                                                                  |
|        |                                                                                           |
|        |-- Window Management (splashscreen -> main window smooth transition via close_splashscreen)|
|        |-- Native File Dialog & Drag-and-Drop Video Resolver (Absolute Paths)                     |
|        |-- Windows Job Object Triple-Lock Process Lifecycle (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)   |
|        |-- Asynchronous NDJSON Reader/Writer & Tauri Event Emitter (pipeline-progress)             |
|        |                                                                                           |
|        v (stdin / stdout NDJSON pipes)                                                             |
|  [ Python Engine Sidecar (engine_sidecar.py / engine.py) ]                                         |
|        |                                                                                           |
|        |-- 1. FFmpeg Audio Demux (16kHz mono WAV, CREATE_NO_WINDOW)                                |
|        |-- 2. faster-whisper STT (Large-v3 default, CUDA safe probe, CPU int8 fallback)            |
|        |-- 3. Google Gemini Specialized Translation (BLOCK_NONE, JSON structured output, fallbacks)|
|        |-- 4. JAV & Thai Post-processing, Negation Protection, Moan Repetition Filter               |
|        |-- 5. Subtitle Serialization (SRT / VTT Millisecond Timing, in-place time-shifting)        |
|        |-- 6. Bundled FFmpeg Hardsub Burn-in (Leelawadee UI) & Softsub Fast-Mux                    |
|        |                                                                                           |
|        v                                                                                           |
|  [ Bundled Outputs & Windows Packaging ]                                                           |
|        |-- Bundled FFmpeg 9.0 (ffmpeg.exe, ffprobe.exe) via Tauri resources                        |
|        |-- Embedded Multi-resolution Windows App Icon (assets/app_icon.ico, icons/32..256)         |
|        |-- Standalone Executable (SubFynn.exe) & Portable Zip Package                              |
+----------------------------------------------------------------------------------------------------+
```

---

## Feature Inventory
Every feature identified during the Survey phase is mapped to an assigned milestone:

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Rust Toolchain & Tauri v2 Init | Install Rust toolchain on Windows, initialize `src-tauri`, configure `tauri.conf.json` dual-window & capabilities | M1 | Survey |
| 2 | Frameless SplashScreen Window | 102x102 SubFynn logo, centered frameless window, loading indicator, `#23212C` theme, smooth transition | M1 | Survey / Req R2.3 |
| 3 | Python Engine Sidecar Daemon | `engine_sidecar.py` NDJSON reader/writer loop wrapping `engine.py` pipeline with methods (ping, load_model, process_video, shift_time, burn, mux, shutdown) | M2 | Survey / Req R1.2 |
| 4 | Whisper Large-v3 & Gemini Pipeline | Safe CUDA probe, CPU int8 fallback, Whisper Large-v3 default, 3 Gemini models, adult/JAV negation protection | M2 | Survey / Req R1.2 |
| 5 | Rust Tauri IPC & Job Object Bridge | Tauri Rust commands for sidecar spawn, health ping, ndjson stream forwarding to events, native dialog, drag-drop handling, and Windows Job Object clean termination | M3 | Survey / Req R1.3 |
| 6 | React Frontend & Theme System | React 18/19 + Vite 6 + Tailwind CSS, `#23212C` canvas, frosted glass cards, Lucide icons, strictly ZERO emojis | M4 | Survey / Req R2.1-2 |
| 7 | Model Controls & Media Actions | Whisper Large-v3 default dropdown, 3 Gemini models selector, style dropdown, Transcribe/Soft-mux/Hard-burn action triggers, real-time progress bar | M4 | Survey / Req R2.5 |
| 8 | Interactive Subtitle Editor Table | Live editable table for timecodes, source text, Thai text, search filter, bulk `±0.5s` & custom offset time-shift, instant SRT/VTT download | M5 | Survey / Req R2.4 |
| 9 | Standalone Packaging & Icon Embedding | Embed `assets/app_icon.ico` & multi-size PNGs, bundle `ffmpeg.exe`/`ffprobe.exe`, build `SubFynn.exe` & portable zip | M6 | Survey / Req R3.1-2 |
| 10| E2E Testing Suite & Adversarial Hardening | Comprehensive opaque-box test suite (Tiers 1-4) published in `TEST_READY.md`, 100% pass, followed by Tier 5 adversarial hardening | M7 / Test Track | Survey / Req AC |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Host Environment & Tauri v2 Core | Install Rustup/Cargo, initialize `src-tauri`, configure `tauri.conf.json`, setup splashscreen window, implement `close_splashscreen` command | none | DONE |
| M2 | Python Engine Sidecar Daemon | Create `engine_sidecar.py` NDJSON daemon, stdin/stdout IPC, streaming progress output, stdin EOF watchdog, sidecar unit tests | none | DONE |
| M3 | Rust Host IPC & Process Lifecycle Bridge | Rust sidecar manager with Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`), event emission (`pipeline-progress`), file picker & drag-drop | M1, M2 | DONE |
| M4 | React Frontend & Luxury Glassmorphic UI | React + Vite + Tailwind setup, `#23212C` theme, Lucide icons, zero emojis, model controls, progress bar, action triggers | M1 | DONE |
| M5 | Interactive Live Subtitle Editor | Live editable table, timecode parser/validator, search filter, bulk time-shift, SRT/VTT download, clipboard copy | M4 | DONE |
| M6 | Standalone Packaging & Icon Embedding | Bundling `ffmpeg.exe`/`ffprobe.exe`, icon generation from `assets/app_icon.png`, `cargo tauri build`, portable zip packaging | M1, M2, M3, M4, M5 | DONE |
| M7 | Final E2E 100% Pass & Adversarial Hardening | Phase 1: Pass 100% of E2E tests (Tiers 1-4) from E2E Testing Track; Phase 2: Tier 5 adversarial testing with Challenger loop | M6, TEST_READY | IN_PROGRESS |

---

## Interface Contracts

### 1. Tauri Host (Rust) ↔ Python Engine Sidecar (`engine_sidecar.py`)
- **Transport**: Standard I/O anonymous pipes with Line-Delimited JSON (NDJSON), UTF-8 encoded.
- **Request Format (Rust -> Python stdin)**:
  ```json
  {"id": 1, "method": "<method_name>", "params": {...}}\n
  ```
- **Response Format (Python stdout -> Rust)**:
  ```json
  {"id": 1, "result": {...}, "error": null}\n
  ```
- **Streaming Event Format (Python stdout -> Rust)**:
  ```json
  {"type": "progress", "data": {"task_id": 1, "percent": 45.2, "stage": "transcribing", "message": "..."}}\n
  ```
- **Supported Methods**:
  - `engine.ping`: Returns `{"status": "ready", "version": "1.0.0", "cuda_available": bool, "ffmpeg_path": string}`
  - `engine.load_model`: `{"model_size": "large-v3"}` -> `{"loaded": true}`
  - `engine.process_video`: `{"video_path": string, "output_dir": string, "model_size": string, "gemini_api_key": string, "gemini_model": string, "translation_style": string}` -> returns segments list, srt_path, vtt_path, srt_content, vtt_content.
  - `engine.shift_time`: `{"segments": [...], "offset_seconds": float}` -> returns shifted segments and srt/vtt strings.
  - `engine.burn_subtitles`: `{"video_path": string, "srt_content": string, "output_video_path": string}` -> returns output path.
  - `engine.mux_subtitles`: `{"video_path": string, "srt_content": string, "output_video_path": string}` -> returns output path.
  - `engine.shutdown`: Gracefully terminates sidecar.
- **Error Handling**: On failure, response contains `{"id": <id>, "error": {"code": -32603, "message": "<error_str>"}}`.
- **Lifecycle Triple-Lock**:
  1. Rust assigns sidecar child process to Windows Job Object (`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`).
  2. Python daemon exits immediately upon `sys.stdin.readline() == ""`.
  3. Tauri `WindowEvent::Destroyed` explicitly kills child process.

### 2. React Frontend ↔ Tauri Host (Rust)
- **Commands (`invoke`)**:
  - `invoke('open_video_dialog') -> Promise<string | null>`: Opens native file picker filtered to video formats.
  - `invoke('close_splashscreen') -> Promise<void>`: Closes splashscreen window and shows main window.
  - `invoke('start_pipeline', { options }) -> Promise<ProcessResult>`: Invokes sidecar `engine.process_video`.
  - `invoke('shift_subtitles', { segments, offsetSeconds }) -> Promise<ShiftResult>`: Invokes sidecar `engine.shift_time`.
  - `invoke('burn_subtitles', { videoPath, srtContent, outputPath }) -> Promise<string>`: Invokes sidecar `engine.burn_subtitles`.
  - `invoke('mux_subtitles', { videoPath, srtContent, outputPath }) -> Promise<string>`: Invokes sidecar `engine.mux_subtitles`.
  - `invoke('open_path', { path }) -> Promise<void>`: Opens file/directory in Windows Explorer.
- **Events (`listen`)**:
  - `listen('pipeline-progress', callback)`: Receives real-time `{ percent: number, stage: string, message: string }`.
  - `listen('tauri://drag-drop', callback)`: Receives dragged video file paths.

---

## Code Layout
```
d:\MyProject\subdev\
├── package.json                   # Root package: React, Vite, Tailwind, Lucide, Framer Motion, @tauri-apps/api
├── vite.config.ts                 # Vite bundler configuration (port 1420)
├── tailwind.config.js             # #23212C theme, frosted glass cards, custom colors
├── postcss.config.js              # PostCSS configuration
├── tsconfig.json                  # TypeScript configuration
├── index.html                     # Main application entry
├── splashscreen.html              # Frameless splashscreen entry
├── src/                           # Frontend Source
│   ├── main.tsx                   # React root entry
│   ├── App.tsx                    # Main layout with model controls, video area, editor, actions
│   ├── index.css                  # Global styles, ambient glows, glassmorphic cards
│   ├── components/
│   │   ├── SplashScreen.tsx       # Animated 102x102 logo splashscreen
│   │   ├── VideoDropzone.tsx      # Drag & drop area with Lucide icons
│   │   ├── ModelControls.tsx      # Whisper Large-v3 default & 3 Gemini models selector
│   │   ├── SubtitleEditor.tsx     # Live editable table with timecodes & Thai translation
│   │   ├── SubtitleRow.tsx        # Editable table row component
│   │   ├── TimeShiftControls.tsx  # Bulk +/-0.5s & custom offset controls
│   │   ├── ActionButtons.tsx      # Transcribe, Soft-mux, Hard-burn action buttons
│   │   └── ProgressBar.tsx        # Dual-layer glowing progress bar
│   ├── hooks/
│   │   ├── useTauriIpc.ts         # Wrapper for Tauri invoke & events
│   │   └── useSubtitleEditor.ts   # State management for subtitles, history, search
│   ├── types/
│   │   └── subtitle.ts            # Type definitions for SubtitleSegment, etc.
│   └── utils/
│       └── timecode.ts            # Timecode parser, formatter, SRT/VTT serializer
├── src-tauri/                     # Tauri v2 Desktop Host (Rust)
│   ├── Cargo.toml                 # Tauri v2, tauri-plugin-dialog, tauri-plugin-shell, windows sys
│   ├── tauri.conf.json            # Dual windows, bundle config, icons, resources
│   ├── capabilities/
│   │   └── default.json           # Window and dialog permissions
│   ├── icons/                     # Generated multi-resolution icons (32, 128, 256, ico)
│   └── src/
│       ├── main.rs                # Windows subsystem declaration
│       ├── lib.rs                 # Command handlers & setup hook
│       └── sidecar.rs             # Sidecar spawner, Job Object, NDJSON streaming
├── engine.py                      # Core Python processing logic (Whisper, Gemini, JAV filters, FFmpeg)
├── engine_sidecar.py              # NDJSON daemon entrypoint for Tauri sidecar
├── ffmpeg.exe                     # Bundled FFmpeg binary (version 9.0 essentials)
├── ffprobe.exe                    # Bundled FFprobe binary (version 9.0 essentials)
├── assets/                        # Design assets
│   ├── app_icon.png               # Master 512x512 icon
│   └── app_icon.ico               # Windows multi-size icon
└── tests/                         # E2E Test Suite (Opaque-box)
    ├── runner.js / runner.py      # E2E Test Runner
    ├── tier1_feature_tests/       # Feature coverage (>=5 per feature)
    ├── tier2_boundary_tests/      # Boundary & corner cases (>=5 per feature)
    ├── tier3_combination_tests/   # Cross-feature combinations
    └── tier4_workload_tests/      # Real-world application scenarios
```
