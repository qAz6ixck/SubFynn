# SubFynn E2E Test Suite - Shared Helpers and Utilities
# Strictly ZERO emojis permitted in code, assertions, and test output.

import os
import re
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

# Regular expression matching Unicode emoji ranges
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs
    "\U0001F680-\U0001F6FF"  # Transport and Map
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U0001F1E6-\U0001F1FF"  # Regional Indicator Symbols
    "\U0001F200-\U0001F251"  # Enclosed Ideographic Supplement
    "\u2600-\u26FF"          # Misc Symbols
    "\u2700-\u27BF"          # Dingbats
    "]+",
    flags=re.UNICODE
)

def get_project_root() -> Path:
    """Returns absolute Path to project root."""
    return Path(__file__).resolve().parent.parent

def contains_emoji(text: str) -> bool:
    """Returns True if the text contains any emoji character."""
    if not isinstance(text, str):
        text = str(text)
    return bool(EMOJI_PATTERN.search(text))

def assert_zero_emojis(target, context_msg: str = ""):
    """Asserts that the string or data structure contains strictly zero emojis."""
    if isinstance(target, str):
        matches = EMOJI_PATTERN.findall(target)
        if matches:
            raise AssertionError(f"Emoji detected in {context_msg}: {matches}")
    elif isinstance(target, dict):
        for k, v in target.items():
            assert_zero_emojis(k, f"{context_msg} dict key {k}")
            assert_zero_emojis(v, f"{context_msg} dict value for {k}")
    elif isinstance(target, (list, tuple, set)):
        for idx, item in enumerate(target):
            assert_zero_emojis(item, f"{context_msg} item {idx}")

def get_bundled_ffmpeg() -> str:
    """Returns path to bundled ffmpeg.exe."""
    root = get_project_root()
    bundled = root / "ffmpeg.exe"
    if bundled.is_file():
        return str(bundled)
    # Check PATH fallback
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
    raise FileNotFoundError("ffmpeg.exe not found in project root or system PATH")

def get_bundled_ffprobe() -> str:
    """Returns path to bundled ffprobe.exe."""
    root = get_project_root()
    bundled = root / "ffprobe.exe"
    if bundled.is_file():
        return str(bundled)
    which_ffprobe = shutil.which("ffprobe")
    if which_ffprobe:
        return which_ffprobe
    raise FileNotFoundError("ffprobe.exe not found in project root or system PATH")

def get_sample_video() -> str:
    """Returns path to assets/subfynn_trailer.mp4."""
    root = get_project_root()
    video = root / "assets" / "subfynn_trailer.mp4"
    if not video.is_file():
        raise FileNotFoundError(f"Sample video not found at {video}")
    return str(video)

def probe_media_file(filepath: str) -> dict:
    """Executes ffprobe and returns parsed JSON inspection."""
    ffprobe = get_bundled_ffprobe()
    cmd = [
        ffprobe,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(filepath)
    ]
    flags = 0x08000000 if sys.platform == "win32" else 0
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=flags)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed ({proc.returncode}): {proc.stderr}")
    return json.loads(proc.stdout)

def make_sample_segments():
    """Returns standard mock subtitle segments for testing."""
    return [
        {
            "id": 1,
            "index": 1,
            "start": 1.0,
            "end": 3.5,
            "start_str": "00:00:01,000",
            "end_str": "00:00:03,500",
            "start_ms": 1000,
            "end_ms": 3500,
            "text": "こんにちは、世界！",
            "original_text": "こんにちは、世界！",
            "thai_text": "สวัสดีชาวโลก"
        },
        {
            "id": 2,
            "index": 2,
            "start": 4.2,
            "end": 7.8,
            "start_str": "00:00:04,200",
            "end_str": "00:00:07,800",
            "start_ms": 4200,
            "end_ms": 7800,
            "text": "SubFynnのテストへようこそ。",
            "original_text": "SubFynnのテストへようこそ。",
            "thai_text": "ยินดีต้อนรับสู่การทดสอบ SubFynn"
        },
        {
            "id": 3,
            "index": 3,
            "start": 8.0,
            "end": 10.5,
            "start_str": "00:00:08,000",
            "end_str": "00:00:10,500",
            "start_ms": 8000,
            "end_ms": 10500,
            "text": "高速で正確な翻訳を実現します。",
            "original_text": "高速で正確な翻訳を実現します。",
            "thai_text": "มอบการแปลที่รวดเร็วและแม่นยำ"
        }
    ]
