# Test Infrastructure: SubFynn Standalone Desktop

## Overview
SubFynn uses Python's standard `unittest` framework to verify all desktop GUI components, engine pipelines, audio extraction, Whisper transcription, Google Gemini translations, SRT/VTT formatting, and FFmpeg video burning.

## Test Suites

| Suite | File | Tests | Coverage |
|-------|------|-------|----------|
| **Core Engine & Media** | `test_engine.py` | 37 tests | Audio demux, Whisper CPU fallback, Gemini translation fallbacks, Thai text post-processing, repetition filter, SRT/VTT time formatting, FFmpeg subtitle mux & burn-in |
| **Desktop GUI & Launcher** | `test_gui_and_main.py` | 7 tests | GUI initialization, Whisper Large-v3 default, specialized Gemini models, video path loading, time shifting (+0.5s / -0.5s), CLI/main argument routing, drag & drop launch |

## Executing Tests

Run all unit tests:
```bash
python -m unittest discover -v
```

Run specific test suites:
```bash
python -m unittest test_engine.py -v
python -m unittest test_gui_and_main.py -v
```

## Acceptance Criteria
- 100% of test cases pass with exit code 0.
- Zero console encoding errors on Windows (UTF-8 / CP65001 enforced).
- Zero emoji references across test assertions and production code.
