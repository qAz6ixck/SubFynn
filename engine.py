"""
Core Subtitle Engine: Video Audio Extraction, Speech-to-Text (Whisper),
Thai Translation, Subtitle Generation (SRT/VTT), and Video Hardsub Burn-in.
"""

import os
import sys
import re
import json
import shutil
import subprocess
import time
import urllib.request
import urllib.parse
import threading
import concurrent.futures
import numpy as np
from typing import List, Dict, Any, Optional, Callable

# Disable Hugging Face symlink warnings on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def patch_faster_whisper_audio():
    """
    Patch faster_whisper.audio.decode_audio for compatibility with newer PyAV versions
    where metadata_errors keyword argument was removed.
    """
    try:
        import wave
        import numpy as np
        import faster_whisper.audio as fwa

        def safe_decode_audio(input_file, sampling_rate=16000, split_stereo=False):
            if isinstance(input_file, str) and os.path.isfile(input_file):
                try:
                    with wave.open(input_file, "rb") as wf:
                        if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == sampling_rate:
                            raw = wf.readframes(wf.getnframes())
                            return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                except Exception:
                    pass

            import av, io
            resampler = av.audio.resampler.AudioResampler(
                format="s16",
                layout="mono" if not split_stereo else "stereo",
                rate=sampling_rate,
            )
            raw_buffer = io.BytesIO()
            dtype = None
            try:
                container = av.open(input_file, mode="r", metadata_errors="ignore")
            except TypeError:
                container = av.open(input_file, mode="r")

            with container:
                frames = container.decode(audio=0)
                frames = fwa._ignore_invalid_frames(frames)
                frames = fwa._group_frames(frames, 500000)
                frames = fwa._resample_frames(frames, resampler)
                for frame in frames:
                    array = frame.to_ndarray()
                    dtype = array.dtype
                    raw_buffer.write(array)

            audio = np.frombuffer(raw_buffer.getbuffer(), dtype=dtype).astype(np.float32) / 32768.0
            if split_stereo:
                return audio[0::2], audio[1::2]
            return audio

        fwa.decode_audio = safe_decode_audio
    except Exception:
        pass


patch_faster_whisper_audio()


def find_ffmpeg() -> str:
    """
    Locate ffmpeg executable on Windows, inside PyInstaller bundle, or on PATH.
    """
    # 1. Check inside PyInstaller bundle temp directory (_MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        bundled = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.isfile(bundled):
            return bundled

    # 2. Check alongside the running executable or script, or in _internal
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    alongside = os.path.join(exe_dir, "ffmpeg.exe")
    if os.path.isfile(alongside):
        return alongside
    internal_ffmpeg = os.path.join(exe_dir, "_internal", "ffmpeg.exe")
    if os.path.isfile(internal_ffmpeg):
        return internal_ffmpeg

    # 3. System PATH
    which_path = shutil.which("ffmpeg")
    if which_path:
        return which_path

    # 4. Known fallback locations on Windows
    user_prof = os.environ.get("USERPROFILE", "")
    local_app = os.environ.get("LOCALAPPDATA", "")
    prog_files = os.environ.get("ProgramFiles", "")
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", "")
    known_paths = [
        os.path.join(user_prof, ".spotiflac", "ffmpeg.exe"),
        os.path.join(local_app, "Programs", "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(prog_files, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(prog_files_x86, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(os.environ.get("ProgramData", ""), "chocolatey", "bin", "ffmpeg.exe"),
        os.path.join(local_app, "Microsoft", "WinGet", "Links", "ffmpeg.exe"),
        os.path.join(user_prof, "scoop", "shims", "ffmpeg.exe"),
    ]
    for path in known_paths:
        if path and os.path.isfile(path):
            return path

    raise FileNotFoundError(
        "ไม่พบโปรแกรม FFmpeg กรุณาติดตั้ง FFmpeg หรือเพิ่มลงใน System PATH"
    )


def format_timestamp(seconds: float, format_type: str = "srt") -> str:
    """
    Format seconds into HH:MM:SS,mmm (SRT) or HH:MM:SS.mmm (VTT).
    """
    if seconds < 0:
        seconds = 0.0
    total_seconds = int(seconds)
    millis = int(round((seconds - total_seconds) * 1000))
    if millis >= 1000:
        total_seconds += millis // 1000
        millis = millis % 1000

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    sep = "," if format_type.lower() == "srt" else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def has_audio_stream(file_path: str, ffmpeg_path: Optional[str] = None) -> bool:
    """
    Check if a media file has an audio track.
    """
    if not os.path.isfile(file_path):
        return False
    ffmpeg = ffmpeg_path or find_ffmpeg()
    cmd = [ffmpeg, "-i", os.path.abspath(file_path)]
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    # FFmpeg prints stream information to stderr
    err_text = p.stderr or ""
    return "Audio:" in err_text


def extract_audio(video_path: str, output_wav_path: str, ffmpeg_path: Optional[str] = None) -> Optional[str]:
    """
    Extract 16kHz mono 16-bit PCM WAV audio from video file.
    Returns output_wav_path if successful, or None if the video has no audio track.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"ไม่พบไฟล์วิดีโอ: {video_path}")

    ffmpeg = ffmpeg_path or find_ffmpeg()

    if not has_audio_stream(video_path, ffmpeg):
        return None

    os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-i", os.path.abspath(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        os.path.abspath(output_wav_path),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        err_msg = (result.stderr or "")[-500:]
        if "Output file does not contain any stream" in err_msg or "matches no streams" in err_msg:
            return None
        raise RuntimeError(f"FFmpeg error while extracting audio: {err_msg}")

    if not os.path.isfile(output_wav_path) or os.path.getsize(output_wav_path) == 0:
        raise RuntimeError("การแยกเสียงล้มเหลว ไฟล์เสียงมีขนาด 0 ไบต์")

    return output_wav_path


def is_thai_text(text: str) -> bool:
    """
    Check if text is predominantly Thai.
    Thai Unicode range: U+0E00 to U+0E7F
    """
    thai_chars = sum(1 for char in text if '\u0e00' <= char <= '\u0e7f')
    total_chars = sum(1 for char in text if not char.isspace())
    if total_chars == 0:
        return False
    return (thai_chars / total_chars) > 0.4


def translate_chunk_google(
    texts: List[str],
    target_lang: str = "th",
    retries: int = 3,
    source_lang: Optional[str] = None,
) -> List[str]:
    """
    Translate a chunk of texts using Google Translate web API with multi-endpoint fallback.
    Uses POST (and GET fallback) with mobile Android client headers to avoid HTTP 429 rate-limiting.
    Rotates through multiple Google hosts (clients1-5, translate.googleapis.com) and client parameters ('at', 'it').
    Strictly verifies line count alignment to prevent subtitle shift/desync.
    """
    if not texts:
        return []

    # Flatten internal newlines within each segment so 1 segment = strictly 1 line
    flattened = [t.replace("\r", " ").replace("\n", " ").strip() for t in texts]

    # Map non-empty lines with indices to preserve empty lines
    non_empty_indices = [i for i, t in enumerate(flattened) if t]
    if not non_empty_indices:
        return list(texts)

    to_translate = "\n".join(flattened[i] for i in non_empty_indices)

    # Intelligent source language determination:
    # If the text contains CJK characters, it CANNOT be Thai even if source_lang was erroneously passed as 'th'
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", to_translate):
        sl = "ja"
    elif source_lang and source_lang.lower() not in ("auto", "none", "", target_lang):
        sl = source_lang.lower()
    elif re.search(r"[\uac00-\ud7af]", to_translate):
        sl = "ko"
    elif re.search(r"[a-zA-Z]", to_translate) and target_lang != "en":
        sl = "en"
    else:
        sl = "auto"

    hosts = [
        "clients1.google.com",
        "clients2.google.com",
        "translate.googleapis.com",
        "clients3.google.com",
        "clients4.google.com",
        "clients5.google.com",
    ]
    client_params = ["at", "it"]
    user_agents = [
        "AndroidTranslate/5.3.0.RC02.130475354-53000263 5.1 phone TRANSLATE_600_RC02",
        "GoogleTranslate/6.28.0.05.421483610 (Linux; U; Android 11; Pixel 5)",
        "GoogleTranslate/6.6.1.RC09.302039986 (Linux; U; Android 9; Redmi 7)",
    ]

    translated_full = None
    last_err = None

    for attempt in range(max(1, retries)):
        for h_idx, host in enumerate(hosts):
            for c_idx, client_name in enumerate(client_params):
                ua = user_agents[(attempt + h_idx + c_idx) % len(user_agents)]
                url = f"https://{host}/translate_a/single?client={client_name}&sl={sl}&tl={urllib.parse.quote(target_lang)}&dt=t"
                headers = {
                    "User-Agent": ua,
                    "Accept": "*/*",
                }

                # 1. Attempt POST with form-encoded data (robust against long payload URLs)
                try:
                    post_data = urllib.parse.urlencode({"q": to_translate}).encode("utf-8")
                    req = urllib.request.Request(url, data=post_data, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data and isinstance(data, list) and data[0]:
                            translated_full = "".join(part[0] for part in data[0] if part and part[0])
                            if translated_full:
                                break
                except Exception as e:
                    last_err = e

                # 2. Attempt GET fallback if POST was not successful
                if not translated_full:
                    try:
                        get_url = url + "&q=" + urllib.parse.quote(to_translate)
                        req = urllib.request.Request(get_url, headers=headers)
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            if data and isinstance(data, list) and data[0]:
                                translated_full = "".join(part[0] for part in data[0] if part and part[0])
                                if translated_full:
                                    break
                    except Exception as e:
                        last_err = e

            if translated_full:
                break
        if translated_full:
            break
        time.sleep(0.3 * (attempt + 1))

    # Secondary fallback to MyMemory if all Google client endpoints failed
    if not translated_full:
        try:
            mm_source = sl if (sl and sl != "auto") else "ja"
            mm_lines = []
            for idx in non_empty_indices:
                line_text = flattened[idx]
                mm_url = (
                    "https://api.mymemory.translated.net/get?q="
                    + urllib.parse.quote(line_text)
                    + f"&langpair={mm_source}|{target_lang}"
                )
                mm_req = urllib.request.Request(
                    mm_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                with urllib.request.urlopen(mm_req, timeout=10) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    if res_json.get("responseStatus") == 200:
                        th_val = res_json.get("responseData", {}).get("translatedText", "")
                        if th_val and not any(warn in th_val for warn in ["MYMEMORY WARNING", "INVALID SOURCE LANGUAGE"]):
                            if any('\u0e00' <= c <= '\u0e7f' for c in th_val):
                                mm_lines.append(th_val)
                                continue
                mm_lines.append(line_text)

            if any(any('\u0e00' <= c <= '\u0e7f' for c in line) for line in mm_lines):
                result = list(texts)
                for idx, orig_idx in enumerate(non_empty_indices):
                    result[orig_idx] = mm_lines[idx]
                return result
        except Exception as e:
            last_err = e

    if not translated_full:
        raise last_err or RuntimeError("All translation endpoints failed")

    translated_lines = [line.strip() for line in translated_full.split("\n")]

    # If count doesn't match non_empty_indices count, Google Translate merged/split lines.
    # Raise ValueError to trigger fallback to single-segment translation, preserving 100% alignment.
    if len(translated_lines) != len(non_empty_indices):
        raise ValueError(
            f"Google Translate line count mismatch: expected {len(non_empty_indices)}, got {len(translated_lines)}"
        )

    # Result array matching original length
    result = list(texts)
    for idx, orig_idx in enumerate(non_empty_indices):
        result[orig_idx] = translated_lines[idx]

    return result


JAV_THAI_REPLACEMENTS = [
    # Insertion / Extraction (入れて / 抜いて / 入った)
    # MUST BE BEFORE climax and short phrase replacements so that "ฉันเข้าไปแล้ว" doesn't get partially matched by "ไปแล้ว"
    (re.compile(r"ใส่มันเข้าไปอย่างรวดเร็ว", re.IGNORECASE), "รีบใส่เข้ามาสิ"),
    (re.compile(r"(?:ฉัน|มัน)?เข้าไปแล้ว", re.IGNORECASE), "ใส่เข้ามาแล้ว"),
    (re.compile(r"ดึงมันออกมา|ถอนมันออก", re.IGNORECASE), "เอาออกไปก่อน"),
    (re.compile(r"ย้าย(?=[!?.~ ]|$)", re.IGNORECASE), "ขยับสิ"),

    # Erotic completion / climax expressions (いく / いっちゃう)
    (re.compile(r"(?<![ก-๙])(?:ฉัน)?(?:กำลัง)?จะไป(?:แล้ว)?(?:นะ|อ่ะ|จ้ะ|ละนะ|เดี๋ยวนี้)?(?=[!?.~ ]|$)", re.IGNORECASE), "จะเสร็จแล้ว"),
    (re.compile(r"(?<![ก-๙])ฉันจะไป(?=[!?.~ ]|$)", re.IGNORECASE), "จะเสร็จแล้ว"),
    (re.compile(r"(?<![ก-๙])(?:ฉัน)?ไปแล้ว[!~]?", re.IGNORECASE), "เสร็จแล้ว!"),
    (re.compile(r"(?<![ก-๙])อย่าไป(?=[!?.~ ]|$)", re.IGNORECASE), "อย่าเพิ่งเสร็จนะ"),
    (re.compile(r"(?<![ก-๙])อย่าเพิ่งไป(?:นะ)?(?=[!?.~ ]|$)", re.IGNORECASE), "อย่าเพิ่งเสร็จนะ"),
    (re.compile(r"(?<![ก-๙])ฉันกำลังจะไป", re.IGNORECASE), "ฉันจะเสร็จแล้ว"),
    (re.compile(r"(?<![ก-๙])จะไปแล้ว", re.IGNORECASE), "จะเสร็จแล้ว"),
    (re.compile(r"(?<![ก-๙])ไปกันเถอะ(?:ไปกันเถอะ)?", re.IGNORECASE), "จะเสร็จแล้ว"),
    (re.compile(r"อิคุอิคุอิกุ|อิคุ(?=[!?.~ ]|$)", re.IGNORECASE), "จะเสร็จแล้ว! จะแตกแล้ว!"),

    # Pleasure expressions (気持ちいい)
    (re.compile(r"มันรู้สึกดี(?:มาก)?", re.IGNORECASE), "มันเสียวมาก"),
    (re.compile(r"รู้สึกดีมากๆ", re.IGNORECASE), "เสียวสุดๆ"),
    (re.compile(r"รู้สึกดี(?:จัง|มาก|จริงๆ|เหลือเกิน)?", re.IGNORECASE), "เสียวจัง"),
    (re.compile(r"รู้สึกสบาย(?:ดี)?", re.IGNORECASE), "เสียวจัง"),
    (re.compile(r"ฉันรู้สึกได้", re.IGNORECASE), "เสียวไปหมดแล้ว"),

    # Refusal / teasing / overwhelmed (ダメ / やめて)
    (re.compile(r"ไม่อนุญาต", re.IGNORECASE), "อย่านะ"),
    (re.compile(r"ไม่ได้นะ(?=[!?.~ ]|$)", re.IGNORECASE), "อย่านะ"),
    (re.compile(r"ไม่ได้แล้ว(?=[!?.~ ]|$)", re.IGNORECASE), "ไม่ไหวแล้ว"),
    (re.compile(r"ไม่ ไม่(?=[!?.~ ]|$)", re.IGNORECASE), "อย่านะ ไม่เอานะ"),
    (re.compile(r"หยุดมัน(?=[!?.~ ]|$)", re.IGNORECASE), "อย่าทำนะ"),
    (re.compile(r"อย่ามอง(?=[!?.~ ]|$)", re.IGNORECASE), "อย่ามองสิ เขินนะ"),

    # Admiration / intense pleasure (すごい)
    (re.compile(r"(?:มัน)?ยอดเยี่ยม(?:มาก|จริงๆ|เหลือเกิน)?", re.IGNORECASE), "สุดยอดเลย"),

    # Deep penetration (奥まで / 突いて)
    (re.compile(r"จนถึงด้านใน", re.IGNORECASE), "ลึกจัง"),
    (re.compile(r"ลึกเข้าไปข้างใน", re.IGNORECASE), "มิดด้ามเลย"),
    (re.compile(r"ข้างในลึก", re.IGNORECASE), "ข้างในลึกๆ"),
    (re.compile(r"ทำให้มันเข้มข้นยิ่งขึ้น|เข้มข้นยิ่งขึ้น", re.IGNORECASE), "เอาให้แรงกว่านี้อีกสิ"),
    (re.compile(r"กระตุ้นเพิ่มเติม", re.IGNORECASE), "กระแทกอีกสิ"),

    # Endurance limits (我慢できない / 壊れちゃう)
    (re.compile(r"(?:ฉัน)?ไม่สามารถอดทน(?:ได้)?", re.IGNORECASE), "ทนไม่ไหวแล้ว"),
    (re.compile(r"(?:ฉัน)?ทนไม่ได้แล้ว", re.IGNORECASE), "ทนไม่ไหวแล้ว"),
    (re.compile(r"ทนไม่ได้", re.IGNORECASE), "กลั้นไม่อยู่แล้ว"),
    (re.compile(r"มันจะแตก", re.IGNORECASE), "จะพังแล้ว"),

    # Wetness (濡れてる)
    (re.compile(r"เปียกโชก", re.IGNORECASE), "แฉะไปหมดแล้ว"),
    (re.compile(r"มันเปียกมาก", re.IGNORECASE), "เยิ้มไปหมดแล้ว"),

    # Insemination / Creampie (中に出して / いっぱい出して)
    (re.compile(r"ใส่มันไว้ข้างใน", re.IGNORECASE), "แตกในเลย"),
    (re.compile(r"ใส่ไว้ข้างใน", re.IGNORECASE), "แตกในเลย"),
    (re.compile(r"เอามันเข้าไปข้างใน", re.IGNORECASE), "แตกในเลยนะ"),
    (re.compile(r"ปล่อยออกมาให้หมด", re.IGNORECASE), "ปล่อยออกมาให้หมดเลย"),
    (re.compile(r"ให้ฉันมาก|ให้ออกมาเยอะๆ", re.IGNORECASE), "ปล่อยออกมาเยอะๆ เลยนะ"),

    # Body parts & Erotic terms (おっぱい / ちんぽ / まんこ / 硬い)
    (re.compile(r"ถูหน้าอก(?:ของฉัน)?|นวดหน้าอก(?:ของฉัน)?", re.IGNORECASE), "ขยำนมฉันสิ"),
    (re.compile(r"ยากมาก(?=[!?.~ ]|$)", re.IGNORECASE), "แข็งเป๊กเลย"),
    (re.compile(r"ดิ๊ก|ดิก", re.IGNORECASE), "ควย"),
    (re.compile(r"การช่วยตัวเอง", re.IGNORECASE), "ช่วยตัวเอง"),
    (re.compile(r"น้ำพุ่ง", re.IGNORECASE), "น้ำแตกกระจาย"),
    (re.compile(r"น้ำอสุจิ", re.IGNORECASE), "น้ำรัก"),
    (re.compile(r"ช่องคลอด", re.IGNORECASE), "รูเสียว"),
    (re.compile(r"อวัยวะเพศชาย", re.IGNORECASE), "ท่อนเอ็น"),
    (re.compile(r"อวัยวะเพศหญิง", re.IGNORECASE), "กลีบกุหลาบ"),
    (re.compile(r"ความสุขสุดยอด", re.IGNORECASE), "จุดสุดยอด"),
    (re.compile(r"มีเพศสัมพันธ์", re.IGNORECASE), "เย็ดกัน"),
    (re.compile(r"ร่วมเพศ", re.IGNORECASE), "เย็ด"),
    (re.compile(r"ความใคร่|อารมณ์ทางเพศ", re.IGNORECASE), "เงี่ยน"),
    (re.compile(r"กระตุ้นอารมณ์", re.IGNORECASE), "ปลุกเงี่ยน"),
    (re.compile(r"เจาะเข้าไป|ทิ่มแทง", re.IGNORECASE), "กระเด้าเข้ามา"),

    # Begging / Pleads / Forgive (お願い / 許して)
    (re.compile(r"ขอทาน(?:เถอะ|นะ)?", re.IGNORECASE), "ขอร้องล่ะ"),
    (re.compile(r"โปรดยกโทษให้ฉัน(?:ด้วย)?|ยกโทษให้ฉัน", re.IGNORECASE), "ยอมแล้ว พอเถอะนะ"),

    # Pain / sensations (痛い)
    (re.compile(r"มันเจ็บปวด", re.IGNORECASE), "เจ็บจัง"),
    (re.compile(r"มันเจ็บ(?=[!?.~ ]|$)", re.IGNORECASE), "เจ็บจัง"),

    # Pervert (変態)
    (re.compile(r"ความวิปริต|การแปรสภาพ", re.IGNORECASE), "คนลามก"),

    # Machine Translation Glitches & Awkward JAV Literalisms
    (re.compile(r"ปลาวาฬพ่นน้ำ", re.IGNORECASE), "น้ำแตกกระจาย"),
    (re.compile(r"ความผิดปกติทางเพศ|ความวิปริต|การแปรสภาพ", re.IGNORECASE), "คนลามก"),
    (re.compile(r"มันจะแปลกๆ\s*ไป|กลายเป็นคนแปลก", re.IGNORECASE), "จะบ้าตายอยู่แล้ว"),
    (re.compile(r"ใส่สิ่งต่าง\s*ๆ\s*มากมายเข้าไปข้างใน|ใส่สิ่งต่าง\s*ๆ\s*มากมาย|สิ่งต่าง\s*ๆ\s*มากมาย", re.IGNORECASE), "แตกในใส่เข้ามาเยอะๆ"),
    (re.compile(r"สิ่งของจะแตก|มันจะแตก", re.IGNORECASE), "จะทนไม่ไหวแล้ว"),
    (re.compile(r"แทรกเข้าไปอย่างรวดเร็ว|แทรกมันเข้าไป|แทรกเข้าไป|การสอดแทรก", re.IGNORECASE), "ใส่เข้ามาสิ รีบยัดเข้ามาเร็ว"),
    (re.compile(r"มันกำลังเต้นอยู่ข้างใน", re.IGNORECASE), "มันกระตุกฉีดน้ำอยู่ข้างในเลย"),
    (re.compile(r"ทำมันแบบดิบ|แบบดิบ|ทำมันดิบๆ", re.IGNORECASE), "เอาสดๆ เลย ไม่ใส่ถุง"),
    (re.compile(r"ติดยางสิ|ติดยาง", re.IGNORECASE), "ใส่ถุงยางสิ"),
    (re.compile(r"วางไว้บนใบหน้า", re.IGNORECASE), "แตกใส่หน้าเลยนะ"),
    (re.compile(r"ใส่มันในปากของคุณ|ใส่ในปากของคุณ", re.IGNORECASE), "แตกใส่ปากหนูเลยนะ"),
    (re.compile(r"ดื่มมัน", re.IGNORECASE), "กลืนน้ำรักเข้าไปสิ"),
    (re.compile(r"ฉันกำลังจะไปแล้ว|ฉันไปแล้ว|กำลังจะไปแล้ว", re.IGNORECASE), "จะเสร็จแล้ว! จะแตกแล้ว!"),
    (re.compile(r"(?<![ก-๙])แอน(?=[ ,.!?~]|$)", re.IGNORECASE), "อ๊าา..."),
    (re.compile(r"มันดีเกินไป", re.IGNORECASE), "เสียวเกินไปแล้ว"),
    (re.compile(r"อวัยวะสืบพันธุ์ชาย", re.IGNORECASE), "ท่อนเอ็น"),
    (re.compile(r"อวัยวะสืบพันธุ์หญิง", re.IGNORECASE), "รูเสียว"),
    (re.compile(r"ทวารหนัก", re.IGNORECASE), "รูก้น"),
    (re.compile(r"การร่วมเพศทางปาก", re.IGNORECASE), "อมควย"),
    (re.compile(r"ดันมันอย่างรวดเร็วและรุนแรง|ดันมันแรง", re.IGNORECASE), "กระแทกแรงๆ"),
    (re.compile(r"คุณลุง(?=[!?.~ ,]|$)", re.IGNORECASE), "ลุงขา"),
    (re.compile(r"ฉันไม่สามารถทนได้อีกต่อไป|ฉันไม่สามารถทนได้", re.IGNORECASE), "ทนไม่ไหวแล้ว"),
    (re.compile(r"ถึงขีดจำกัดแล้ว", re.IGNORECASE), "ทนไม่ไหวแล้ว จะเสร็จแล้ว"),
    (re.compile(r"ชนด้านใน|ชนกับด้านใน", re.IGNORECASE), "ชนมดลูกเลย"),
    (re.compile(r"มีอะไรกับฉัน", re.IGNORECASE), "เย็ดกับฉัน"),
    (re.compile(r"ช่วยตัวเองของฉัน", re.IGNORECASE), "ช่วยตัวเอง"),
    (re.compile(r"อย่าเพิ่งไปเลย", re.IGNORECASE), "อย่าเพิ่งเสร็จนะ"),
    (re.compile(r"ฉันเสร็จสิ้นแล้ว", re.IGNORECASE), "เสร็จแล้ว!"),
    (re.compile(r"ทำมันอย่างรุนแรง", re.IGNORECASE), "ทำแรงๆ เลย"),
    (re.compile(r"มองดูสิ่งนี้", re.IGNORECASE), "ดูตรงนี้สิ"),
]

JAV_JAPANESE_CUES = [
    # (keywords, default_thai, dirty_thai, sweet_thai, targets_to_replace)
    (["気持ちいい", "きもちいい", "キモチイイ", "気持ちい", "きもちい", "きもちいいよ"], "เสียวจัง", "เสียวควยมาก", "เสียวจังเลยค่ะ", ["รู้สึกดี", "สบาย", "สุขภาพ"]),
    (["いく", "いっちゃう", "イッちゃう", "イク", "いっちゃいそう", "いきます", "いっちゃうよ", "いっちゃった", "イクイク", "イクッ", "いかないで", "イカないで", "いっちゃだめ", "いっちゃダメ", "いかない"], "จะเสร็จแล้ว", "น้ำจะแตกแล้ว", "หนูจะเสร็จแล้วค่ะ", ["ไป", "กำลัง", "เดินทาง", "อิคุ", "อิกุ", "อย่าเพิ่งไป", "อย่าไป"]),
    (["だめ", "ダメ", "駄目", "ダメダメ"], "อย่านะ", "อย่านะ เดี๋ยวแตก", "อย่าแกล้งหนูสิคะ", ["ไม่ได้", "ไม่อนุญาต", "ห้าม", "ไม่ ไม่"]),
    (["やめて", "ヤメテ", "やめろ", "やめてください"], "อย่าทำนะ", "หยุดก่อนสิ เดี๋ยวแตก", "อย่าแกล้งหนูสิคะ", ["หยุดมัน", "กรุณาหยุด", "หยุดนะ"]),
    (["奥まで", "おくまで", "奥に", "奥が"], "ลึกจัง", "มิดด้ามเลย", "ลึกจังเลยค่ะ", ["ด้านใน", "ลึกเข้าไป", "ข้างในลึก"]),
    (["もっと", "もっと奥", "もっと激しく", "激しく"], "เอาอีก", "กระแทกแรงๆ อีกสิ", "แรงอีกนิดสิคะ", ["ทำให้มันเข้มข้นยิ่งขึ้น", "เข้มข้นยิ่งขึ้น", "เอาอีก"]),
    (["中に出して", "なかに出して", "中出し", "なかだし", "中に出さないで", "なかに出さないで", "中に出すな", "中に出しちゃダメ", "中に出しちゃだめ", "中に出さない"], "แตกในเลย", "แตกในเลยนะมิดด้าม", "ปล่อยข้างในเลยนะคะ", ["ข้างใน", "ใส่", "เอามันเข้าไป", "หยุดแตกใน", "ใส่ข้างใน", "อย่าใส่ข้างใน"]),
    (["いっぱい出して", "いっぱいだして"], "ปล่อยออกมาเยอะๆ นะ", "แตกใส่เยอะๆ เลย", "ปล่อยออกมาให้หมดเลยนะคะ", ["ให้ฉันมาก", "ให้ออกมาเยอะๆ", "ปล่อยออกมา"]),
    (["すごい", "スゴイ", "すごっ"], "สุดยอดเลย", "โคตรดี โคตรเสียว", "สุดยอดเลยค่ะ", ["ยอดเยี่ยม", "เยี่ยม"]),
    (["痛い", "いたい", "痛いよ"], "เจ็บจัง", "เจ็บจัง แต่เสียว", "เจ็บจังเลยค่ะ", ["เจ็บปวด", "มันเจ็บ"]),
    (["お願い", "たのむ", "おねがい"], "ขอร้องล่ะ", "ขอร้องล่ะ เอาอีก", "ขอร้องล่ะค่ะ ช่วยหนูที", ["ขอทาน", "โปรด"]),
    (["許して", "ゆるして", "勘弁して"], "ยอมแล้ว พอเถอะนะ", "ยอมแล้ว ยกโทษให้ด้วย", "หนูยอมแล้วค่ะ พอเถอะนะ", ["โปรดยกโทษให้ฉัน", "ยกโทษให้ฉัน"]),
    (["我慢できない", "がまんできない"], "ทนไม่ไหวแล้ว", "กลั้นไม่อยู่แล้ว จะแตกแล้ว", "หนูทนไม่ไหวแล้วค่ะ", ["ไม่สามารถอดทน", "ทนไม่ได้"]),
    (["濡れてる", "ぬれてる", "びしょびしょ", "ぐしょぐしょ"], "แฉะหมดแล้ว", "หีแฉะเยิ้มไปหมดแล้ว", "แฉะหมดแล้วค่ะ", ["เปียกโชก", "เปียกมาก", "เปียก"]),
    (["恥ずかしい", "はずかしい"], "เขินจัง", "เขินจัง น่าอายชะมัด", "เขินจังเลยค่ะ", ["น่าอาย"]),
    (["見ないで", "みないで"], "อย่ามองสิ เขินนะ", "อย่ามองสิ อายนะ", "อย่ามองหนูสิคะ เขินนะ", ["อย่ามอง"]),
    (["キスして", "きすして", "ちゅーして"], "จูบหน่อยสิ", "จูบปากหน่อยสิ", "จูบหนูหน่อยสิคะ", ["จูบฉัน"]),
    (["硬い", "かたい", "カタイ"], "แข็งมาก", "ควยแข็งเป๊กเลย", "แข็งจังเลยค่ะ", ["ยากมาก"]),
    (["ちんぽ", "チンポ", "おちんちん", "ちんこ", "巨根"], "ท่อนเอ็น", "ควย", "ของพี่", ["ดิ๊ก", "ดิก"]),
    (["まんこ", "マンコ", "おまんこ", "名器"], "รูเสียว", "หี", "ของหนู", ["จิ๋ม", "ช่องคลอด"]),
    (["動いて", "うごいて"], "ขยับสิ", "โยกแรงๆ สิ", "ขยับหน่อยสิคะ", ["ย้าย"]),
    (["入れて", "いれて", "早く入れて"], "ใส่เข้ามาสิ", "รีบยัดเข้ามาเร็ว", "ใส่เข้ามาสิคะ", ["ใส่มันเข้าไปอย่างรวดเร็ว", "ใส่มันเข้าไป"]),
    (["入っちゃった", "はいっちゃった"], "ใส่เข้ามาแล้ว", "มิดด้ามเข้ามาแล้ว", "เข้ามาข้างในแล้วค่ะ", ["ฉันเข้าไปแล้ว", "มันเข้าไปแล้ว"]),
    (["抜いて", "ぬいて"], "เอาออกไปก่อน", "ชักออกไปก่อนสิ", "เอาออกไปก่อนสิคะ", ["ดึงมันออกมา", "ถอนมันออก"]),
    (["壊れちゃう", "こわれちゃう"], "จะพังแล้ว", "เสียวจนจะบ้าอยู่แล้ว", "หนูจะทนไม่ไหวแล้วค่ะ", ["มันจะแตก"]),
    (["オナニー", "おなにー"], "ช่วยตัวเอง", "ช่วยตัวเอง / ชักว่าว", "ช่วยตัวเองค่ะ", ["การช่วยตัวเอง"]),
    (["潮吹き", "しおふき"], "น้ำแตกกระจาย", "เสร็จจนน้ำพุ่ง", "น้ำแตกกระจายเลยค่ะ", ["น้ำพุ่ง"]),
    (["おっぱい", "揉んで"], "ขยำนมฉันสิ", "บีบนมแรงๆ เลย", "บีบนมให้หนูหน่อยสิคะ", ["ถูหน้าอก", "นวดหน้าอก"]),
    (["ヤリたい", "やりたい", "ヤろう", "セックスしたい"], "อยากมีอะไรด้วย", "อยากเย็ด / เงี่ยนชิบหาย", "อยากกอดพี่จังค่ะ", ["อยากทำ", "ทำกัน"]),
    (["犯して", "ハメて", "突っ込んで"], "สอดเข้ามาสิ", "เย็ดฉันแรงๆ / กระเด้าเข้ามาเลย", "กอดหนูแน่นๆ นะคะ", ["กระทำ", "สอดใส่"]),
    (["しゃぶれ", "しゃぶって", "フェラ", "くわえて"], "อมให้หน่อย", "อมควยให้กู / ดูดควยสิ", "อมให้พี่นะคะ", ["ดูด", "อม"]),
    (["なめて", "舐めて", "クンニ"], "เลียให้หน่อย", "เลียหีฉันสิ / เลียตรงนั้นสิ", "เลียให้หนูหน่อยนะคะ", ["เลีย"]),
    (["アナル", "ケツ", "お尻"], "ก้น", "ตูด / รูก้น / เสียบตูด", "ก้นหนู", ["ก้น"]),
    (["声出して", "声我慢しないで"], "ครางออกมาสิ", "ร้องครางดังๆ เลย ไม่ต้องกลั้นเสียง", "ครางออกมาได้เลยนะคะ", ["ออกเสียง", "ส่งเสียง"]),
    (["感じてる", "感じちゃう"], "เสียวมากเลย", "โคตรเงี่ยน เสียวจนทนไม่ไหว", "หนูเสียวมากเลยค่ะ", ["รู้สึก"]),
    (["エッチ", "えっち", "エロい"], "ลามกจัง", "เงี่ยนชิบหาย โคตรลามก", "พี่ลามกจังเลยค่ะ", ["ทะลึ่ง", "ลามก"]),
]


def post_process_jav_thai(
    thai_text: str,
    original_text: Optional[str] = None,
    style: str = "jav",
    is_llm_output: bool = False,
) -> str:
    """
    Enhance Thai translation for Adult Videos / JAV to make phrasing emotionally immersive,
    erotic, and natural rather than literal or robotic.
    Handles Japanese cues directly when original text is present, prevents negation inversion,
    and fixes typical machine translation literalisms.
    Supports sub-styles: 'jav' (standard fansub), 'jav_dirty' (hardcore dirty talk), 'jav_sweet' (sweet sensual).
    """
    if not thai_text or not thai_text.strip():
        return thai_text

    processed = thai_text.strip()
    style_clean = (style or "jav").lower()

    # If the text is from Gemini / LLM, do NOT blindly override full sentences or destroy nuance.
    # Only clean up obvious residual Google Translate-style robotic literalisms if any leaked through.
    if is_llm_output:
        # Minimal cleanup for common LLM slips if any
        processed = re.sub(r"(?:ฉัน)?กำลังจะไปแล้ว", "จะเสร็จแล้ว", processed)
        processed = re.sub(r"ไม่อนุญาต(?=[!?.~ ]|$)", "อย่านะ", processed)
        return processed

    # 1. If Japanese original text contains explicit erotic keywords, apply contextual overrides
    if original_text:
        orig_clean = original_text.strip()
        is_negative = (
            any(k in orig_clean for k in ["ない", "ず", "だめ", "ダメ", "駄目", "やめて", "やめろ", "無理", "あかん", "いかん", "すな"])
            or any(k in processed for k in ["อย่า", "ห้าม", "หยุด", "แค่อย่า", "ไม่ได้", "ไม่"])
        )

        for keywords, default_thai, dirty_thai, sweet_thai, targets in JAV_JAPANESE_CUES:
            for kw in keywords:
                if kw in orig_clean:
                    chosen_phrase = default_thai
                    if any(k in style_clean for k in ("dirty", "hardcore", "vulgar")):
                        chosen_phrase = dirty_thai
                    elif "sweet" in style_clean:
                        chosen_phrase = sweet_thai

                    # Special handling for Insemination (中に出して / 中出し) with negation safety
                    if any(k in kw for k in ["中に出して", "中出し", "なかだし", "中に出さないで", "なかに出さないで", "中に出すな", "中に出しちゃダメ", "中に出しちゃだめ", "中に出さない"]):
                        if is_negative:
                            chosen_phrase = "อย่าแตกในนะ" if "dirty" not in style_clean else "อย่าแตกในนะโว้ย"
                            if "sweet" in style_clean:
                                chosen_phrase = "อย่าแตกในนะคะ"
                        if any(t in processed for t in targets) or (is_negative and "แตกใน" in processed):
                            processed = chosen_phrase
                        elif "แตกใน" not in processed:
                            if not any('\u0e00' <= c <= '\u0e7f' for c in processed) or re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", processed):
                                processed = chosen_phrase
                            else:
                                processed = f"{processed} ({chosen_phrase})" if len(processed) < 15 else chosen_phrase
                        break

                    # Special handling for Climax (いく) with negation safety
                    if any(k in kw for k in ["いく", "いっちゃう", "イク", "いかないで", "イカないで", "いっちゃだめ", "いっちゃダメ", "いかない"]):
                        if is_negative:
                            chosen_phrase = "อย่าเพิ่งเสร็จนะ" if "sweet" not in style_clean else "อย่าเพิ่งเสร็จนะคะ"
                        if any(t in processed for t in targets) or "อย่าเพิ่งไป" in processed or "อย่าไป" in processed:
                            processed = re.sub(r"(?:ฉัน)?(?:กำลัง)?จะไป(?:แล้ว)?(?:นะ|อ่ะ|จ้ะ|ละนะ)?|ไปกันเถอะ(?:ไปกันเถอะ)?|อย่า(?:เพิ่ง)?ไป(?:นะ)?", chosen_phrase, processed)
                            if chosen_phrase not in processed and "เสร็จแล้ว" not in processed and "แตกแล้ว" not in processed:
                                processed = chosen_phrase
                        elif not any('\u0e00' <= c <= '\u0e7f' for c in processed):
                            processed = chosen_phrase
                        break

                    # General cue target replacement in processed text
                    matched_target = False
                    for target in targets:
                        if target in processed:
                            processed = processed.replace(target, chosen_phrase)
                            matched_target = True

                    # If none of the targets were in processed, check if entire segment is single short cue or has no Thai
                    if not matched_target and (
                        (len(orig_clean) <= len(kw) + 3 and len(processed) < 12)
                        or not any('\u0e00' <= c <= '\u0e7f' for c in processed)
                    ):
                        processed = chosen_phrase
                    break

    # 2. General regex replacements for robotic adult translations
    for pattern, repl in JAV_THAI_REPLACEMENTS:
        # Style variations for dirty / sweet talk
        applied_repl = repl
        if any(k in style_clean for k in ("dirty", "hardcore", "vulgar")):
            if repl == "ท่อนเอ็น":
                applied_repl = "ควย"
            elif repl == "รูเสียว":
                applied_repl = "หี"
            elif repl == "จะเสร็จแล้ว":
                applied_repl = "จะแตกแล้ว"
        elif "sweet" in style_clean:
            if repl == "ควย":
                applied_repl = "ท่อนเอ็น"
            elif repl == "จะเสร็จแล้ว":
                applied_repl = "หนูจะเสร็จแล้วค่ะ"
            elif repl == "เสียวจัง":
                applied_repl = "เสียวจังเลยค่ะ"
            elif repl == "อย่านะ":
                applied_repl = "อย่าแกล้งหนูสิคะ"

        processed = pattern.sub(applied_repl, processed)

    return processed


def translate_texts_to_thai(
    texts: List[str],
    batch_size: int = 15,
    style: str = "jav",
    original_texts: Optional[List[str]] = None,
    source_lang: Optional[str] = None,
) -> List[str]:
    """
    Batch translate list of strings to Thai with chunking and error resilience.
    Supports adult/JAV post-processing for emotional and natural dialogue.
    """
    results: List[str] = []
    style_lower = (style or "jav").lower()

    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        orig_chunk = original_texts[i:i + batch_size] if original_texts else None
        try:
            translated_chunk = translate_chunk_google(chunk, target_lang="th", source_lang=source_lang)
            if style_lower.startswith(("jav", "adult")):
                translated_chunk = [
                    post_process_jav_thai(t, orig_chunk[idx] if orig_chunk else None, style=style_lower)
                    for idx, t in enumerate(translated_chunk)
                ]
            results.extend(translated_chunk)
        except Exception:
            # Fallback: translate individually to guarantee perfect alignment
            for idx_c, item in enumerate(chunk):
                clean_item = item.replace("\r", " ").replace("\n", " ").strip()
                orig_item = orig_chunk[idx_c] if orig_chunk else None
                try:
                    if clean_item and not is_thai_text(clean_item):
                        t_item = translate_chunk_google([clean_item], target_lang="th", source_lang=source_lang)[0]
                        if style_lower.startswith(("jav", "adult")):
                            t_item = post_process_jav_thai(t_item, orig_item or clean_item, style=style_lower)
                        results.append(t_item)
                    else:
                        if style_lower.startswith(("jav", "adult")) and is_thai_text(clean_item):
                            results.append(post_process_jav_thai(clean_item, orig_item, style=style_lower))
                        else:
                            results.append(item)
                except Exception:
                    # Retry once after short sleep for network resilience
                    try:
                        time.sleep(0.5)
                        t_item = translate_chunk_google([clean_item], target_lang="th", source_lang=source_lang)[0]
                        if style_lower.startswith(("jav", "adult")):
                            t_item = post_process_jav_thai(t_item, orig_item or clean_item, style=style_lower)
                        results.append(t_item)
                    except Exception:
                        if style_lower.startswith(("jav", "adult")):
                            cue_th = post_process_jav_thai(clean_item, orig_item or clean_item, style=style_lower)
                            if cue_th and any('\u0e00' <= c <= '\u0e7f' for c in cue_th):
                                results.append(cue_th)
                                continue
                        results.append(item)

    return results


def translate_segments_with_gemini(
    segments: List[Dict[str, Any]],
    api_key: str,
    chunk_size: int = 40,
    style: str = "jav",
    model: str = "gemini-2.5-flash",
) -> List[Dict[str, Any]]:
    """
    Translate subtitle segments to natural, idiomatic Thai using Google Gemini API.
    Supports specialized styles:
      - 'jav' / 'jav_balanced': Masterful JAV fansub style (emotional, natural, sexually thrilling).
      - 'jav_dirty': Hardcore Dirty Talk (explicit, raw, passionate bedroom dirty talk).
      - 'jav_sweet': Sweet & Sensual (gentle, teasing, intimate romance).
      - 'general', 'anime', 'drama'.
    Features:
      - Automatic safety threshold relaxation (BLOCK_NONE) to prevent false-positive adult content blocks.
      - Structured JSON output (response_mime_type="application/json") to guarantee parseable responses.
      - Automatic model fallback chain: requested -> gemini-2.5-flash -> gemini-2.0-flash -> gemini-1.5-flash.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise ImportError("ไม่พบแพ็กเกจ google-genai กรุณาติดตั้งด้วย pip install google-genai")

    client = genai.Client(api_key=api_key)
    style_lower = (style or "jav").lower()

    if style_lower in ("jav_dirty", "adult_dirty", "jav_hardcore", "jav_vulgar", "dirty", "hardcore", "vulgar"):
        system_instruction = (
            "You are an expert subtitle translator and localizer specializing in Japanese Adult Videos (JAV) and adult films into Thai (นักแปลซับไตเติลหนังผู้ใหญ่ JAV 18+ สายดุดัน เร่าร้อน หยาบคายได้เต็มที่ Dirty Talk ดิบเถื่อน ไม่เซ็นเซอร์ มืออาชีพ).\n"
            "Your objective is to translate dialogue, dirty talk, and voice reactions into raw, visceral, intensely erotic, unapologetically explicit and vulgar Thai phrasing (แปลแบบหยาบคายได้เต็มที่ ดิบ เถื่อน ได้อารมณ์เสียวซ่าน ดุดัน เร่าร้อน Dirty Talk ถึงพริกถึงขิง ห้ามเซ็นเซอร์ ห้ามลดทอนความหยาบเด็ดขาด ไม่แปลตรงตัวทื่อๆ).\n\n"
            "Style Guidelines for Uncensored Dirty Talk (หยาบคายได้เต็มที่ / 18+ ดุดัน ดิบเถื่อน):\n"
            "1. Unrestricted & Vulgar Vocabulary (ใช้ภาษาพูดหยาบคายและคำสแลงทางเพศแบบเต็มที่ ไม่เซ็นเซอร์):\n"
            "   - Authentic bedroom dirty talk: ควย, ท่อนเอ็น, หี, รูร่าน, รูเสียว, รูก้น, น้ำแตก, แตกใน, น้ำเงี่ยน, น้ำควย, มิดด้าม, เย็ด, ซอยถี่ๆ, กระเด้าแรงๆ, กระแทกเข้ามา, ขยำนม, ดูดนม, อมควย, เลียหี, อ้าขา, โคตรเสียว, เสียวชิบหาย, เงี่ยนฉิบหาย.\n"
            "   - '気持ちいい / きもちいい' -> 'โคตรเสียว / เสียวควยมาก / เสียวหีมาก / เสียวชิบหาย / ฟินสุดๆ' (NEVER 'รู้สึกดี').\n"
            "   - 'いく / いっちゃう / イク' -> 'จะเสร็จแล้ว / จะแตกแล้ว / น้ำจะแตกแล้ว / ไม่ไหวแล้วจะแตก / จะแตกแล้วโว้ย' (NEVER 'กำลังจะไป').\n"
            "   - 'ダメ / だめ' -> 'อย่านะ / เดี๋ยวแตก / ไม่ไหวนะ / อย่าเพิ่งแตกนะ'.\n"
            "   - '奥まで / 突いて' -> 'มิดด้ามเลย / ลึกจัง / กระแทกเข้ามาลึกๆ / กระเด้าลึกๆ'.\n"
            "   - '中に出して' -> 'แตกในเลยนะ / แตกใส่ข้างในเลย / แตกในให้หมด'.\n"
            "   - 'いっぱい出して' -> 'แตกใส่เยอะๆ เลย / ปล่อยน้ำออกมาให้หมด / แตกใส่หน้าเลย'.\n"
            "   - 'もっと激しく' -> 'เอาให้แรงกว่านี้ / เย็ดแรงๆ อีกสิ / กระแทกแรงๆ อีก'.\n"
            "   - 'チンポ / ちんこ' -> 'ควย / ท่อนเอ็น'.\n"
            "   - 'マンコ / まんこ' -> 'หี / รูเสียว / รูร่าน'.\n"
            "   - 'ヤリたい / 犯して' -> 'อยากเย็ด / เย็ดฉันแรงๆ'.\n"
            "   - 'しゃぶれ / くわえて' -> 'อมควยให้กู / ดูดควยสิ'.\n"
            "   - 'なめて' -> 'เลียหีฉันสิ / เลียตรงนั้นสิ'.\n"
            "2. Tone, Pronouns & Vocalizations:\n"
            "   - Natural passionate Thai dirty talk and moans (อ๊า..., ซี้ด..., อื้อ..., เสียวโว้ยยย...).\n"
            "   - Intimate and raw Thai pronouns: มึง, กู, พี่, หนู, ตัวเอง, เค้า (match roleplay dynamic).\n"
            "   - ห้ามตัดทอนคำ ห้ามใส่เครื่องหมายดอกจัน (***) ห้ามใช้ภาษาทางการในฉากร่วมเพศ."
        )
    elif style_lower in ("jav_sweet", "adult_sweet"):
        system_instruction = (
            "You are an expert subtitle translator specializing in Japanese Adult Videos (JAV) and adult romance films into Thai (นักแปลซับไตเติลหนังผู้ใหญ่ JAV 18+ สไตล์หวานละมุน ขี้อ้อน มืออาชีพ).\n"
            "Your objective is to translate dialogue and voice reactions into sensual, sweet, affectionate, and teasing Thai phrasing with deep emotional intimacy (แปลแบบได้อารมณ์หวานละมุน ขี้อ้อน เซ็กซี่ ฟินหัวใจ ชวนเคลิ้ม ภาษาพูดธรรมชาติ ไม่แปลตรงตัวทื่อๆ).\n\n"
            "Style Guidelines for JAV Sweet & Sensual (18+ หวานละมุน ขี้อ้อน):\n"
            "1. Intimate & Sensual Vocabulary:\n"
            "   - Use tender, affectionate, and teasing phrasing: เสียวจังเลยค่ะ, พี่ขา, หนูไม่ไหวแล้ว, อย่าแกล้งหนูสิ, กอดแน่นๆ นะ, จูบหนูหน่อย, ลึกจังเลย, ฟินมากค่ะ.\n"
            "   - '気持ちいい' -> 'เสียวจังเลยค่ะ / ฟินจังเลย / รู้สึกดีเหลือเกินค่ะ' (sensual, not medical).\n"
            "   - 'いく / いっちゃう' -> 'จะเสร็จแล้วนะ / หนูจะไม่ไหวแล้ว / จะไปสวรรค์แล้ว'.\n"
            "   - 'ダメ' -> 'อย่าแกล้งหนูสิ / อย่านะคะ / เดี๋ยวหนูทนไม่ไหว'.\n"
            "   - '中に出して' -> 'ปล่อยข้างในเลยนะคะ / แตกในตัวหนูเลยนะ'.\n"
            "2. Pronouns & Vocal Expressions:\n"
            "   - Soft, endearing pronouns (หนู, พี่ขา, ตัวเอง, เค้า) and sweet vocalizations (อ๊าา..., อื้มม..., อื้อ...). Deliver warmth and romantic immersion.\n"
        )
    elif style_lower.startswith(("jav", "adult")):
        system_instruction = (
            "You are an expert subtitle translator and localizer specializing in Japanese Adult Videos (JAV) and adult films into Thai (นักแปลซับไตเติลหนังผู้ใหญ่ JAV 18+ มืออาชีพ).\n"
            "Your objective is to translate the dialogue and voice reactions into emotionally immersive, authentic, sexually thrilling, intimate, and natural Thai phrasing (แปลแบบได้อารมณ์ เร่าร้อน เสียว ชวนฟิน ภาษาพูดธรรมชาติของหนังผู้ใหญ่ 18+ ไม่แปลตรงตัวทื่อๆ).\n\n"
            "Guidelines for JAV / Adult Translation:\n"
            "1. Erotic & Emotive Vocabulary:\n"
            "   - '気持ちいい / きもちいい' -> 'เสียวจัง / เสียวมาก / ฟินสุดๆ' (NEVER 'รู้สึกดี' or 'สบายดี').\n"
            "   - 'いく / いっちゃう / いきます' -> 'จะเสร็จแล้ว / จะแตกแล้ว / ไม่ไหวแล้ว / จะออกแล้ว' (NEVER 'กำลังจะไป' or 'จะไปแล้ว').\n"
            "   - 'ダメ / だめ' -> 'อย่านะ / ไม่เอานะ / เดี๋ยวแตก / ไม่ไหวนะ' (NEVER 'ไม่อนุญาต').\n"
            "   - 'やめて' -> 'อย่าทำนะ / หยุดก่อน / อย่าแกล้งสิ'.\n"
            "   - 'すごい' -> 'สุดยอดเลย / ใหญ่จัง / เสียวมาก / โคตรดี' (NEVER 'ยอดเยี่ยม').\n"
            "   - '奥 / 奥まで' -> 'ข้างในลึกๆ / ลึกจัง / มิดด้าม'.\n"
            "   - 'もっと' -> 'เอาอีก / ทำอีกสิ / แรงอีก'.\n"
            "   - '中に出して' -> 'แตกในเลย / ปล่อยข้างในเลย'.\n"
            "   - 'いっぱい出して' -> 'แตกใส่เยอะๆ นะ / ปล่อยออกมาให้หมดเลย'.\n"
            "   - '痛い' -> 'เจ็บจัง / เจ็บนะ'.\n"
            "   - 'お願い' -> 'ขอร้องล่ะ / ช่วยที / เอาอีกนะ'.\n"
            "   - '我慢できない' -> 'ทนไม่ไหวแล้ว / กลั้นไม่อยู่แล้ว'.\n"
            "   - '濡れてる' -> 'แฉะหมดแล้ว / เยิ้มไปหมดแล้ว'.\n"
            "   - '恥ずかしい' -> 'เขินจัง / น่าอายจัง'.\n"
            "2. Natural Pronouns & Vocal Reactions:\n"
            "   - Use realistic intimate Thai pronouns (หนู, เค้า, ฉัน, พี่, ตัวเอง, ลุง) and vocal expressions (อ๊า..., อื้อ..., ซี้ด..., อ่า...).\n"
            "   - The result should sound like a masterfully subtitled JAV production with full emotional immersion."
        )
    elif style_lower == "anime":
        system_instruction = (
            "You are an expert anime & manga subtitle translator into Thai (นักแปลซับอนิเมะมืออาชีพ).\n"
            "Translate the following subtitle lines into lively, expressive, and cute Thai subtitles fitting anime characters and manga dialogue."
        )
    elif style_lower == "drama":
        system_instruction = (
            "You are an expert drama & series subtitle translator into Thai.\n"
            "Translate the following subtitle lines into poignant, emotionally rich, and dramatic Thai subtitles."
        )
    else:
        system_instruction = (
            "You are an expert subtitle translator and localizer into Thai (ซับไทยมืออาชีพ).\n"
            "Translate the following subtitle lines into natural, fluid, and engaging Thai subtitles.\n"
            "Keep the context smooth, cinematic, and conversational."
        )

    # Configure safety settings to BLOCK_NONE to allow adult film dialog translation without blocks
    safety_settings = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=types.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]
    if hasattr(types.HarmCategory, "HARM_CATEGORY_CIVIC_INTEGRITY"):
        safety_settings.append(
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY,
                threshold=types.HarmBlockThreshold.BLOCK_NONE,
            )
        )

    # Model alias mapping for specialized translation models
    primary_candidates = []
    if model in ("gemini-3.5-live-translate-preview", "live-translate"):
        primary_candidates = ["gemini-3.5-live-translate-preview", "gemini-2.5-flash"]
    elif model in ("cloud-translation-llm", "cloud-translation", "translation-llm"):
        primary_candidates = ["gemini-2.5-pro", "gemini-2.5-flash"]
    else:
        primary_candidates = [model]

    models_to_try = []
    for cand in primary_candidates + [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
    ]:
        if cand and cand not in models_to_try:
            models_to_try.append(cand)

    def _translate_chunk(chunk_segments):
        input_list = [{"id": s["id"], "text": s["original_text"]} for s in chunk_segments]

        prompt = (
            f"{system_instruction}\n\n"
            "Input JSON:\n"
            f"{json.dumps(input_list, ensure_ascii=False)}\n\n"
            "Return ONLY a valid JSON list of objects with keys 'id' and 'thai_text'. No markdown wrap, no explanations."
        )

        response = None
        for try_model in models_to_try:
            try:
                config = types.GenerateContentConfig(
                    safety_settings=safety_settings,
                    response_mime_type="application/json",
                )
                response = client.models.generate_content(
                    model=try_model,
                    contents=prompt,
                    config=config,
                )
                if response and (response.text or "").strip():
                    break
            except Exception:
                try:
                    response = client.models.generate_content(
                        model=try_model,
                        contents=prompt,
                    )
                    if response and (response.text or "").strip():
                        break
                except Exception:
                    continue

        raw_text = (response.text if response else "") or ""
        raw_text = raw_text.strip()

        # Robust JSON extraction between outermost brackets if needed
        if "[" in raw_text and "]" in raw_text:
            start_idx = raw_text.find("[")
            end_idx = raw_text.rfind("]") + 1
            raw_text = raw_text[start_idx:end_idx]

        try:
            translations = json.loads(raw_text)
            items_list = []
            if isinstance(translations, list):
                items_list = translations
            elif isinstance(translations, dict):
                for k in ("translations", "subtitles", "segments", "data", "results", "items"):
                    if isinstance(translations.get(k), list):
                        items_list = translations[k]
                        break

            trans_map = {}
            for item in items_list:
                if isinstance(item, dict) and "id" in item:
                    try:
                        item_id = int(item["id"])
                    except (ValueError, TypeError):
                        item_id = item["id"]
                    th_val = (
                        item.get("thai_text")
                        or item.get("translation")
                        or item.get("thai")
                        or item.get("text")
                        or item.get("translated_text")
                    )
                    if th_val and isinstance(th_val, str) and th_val.strip():
                        trans_map[item_id] = th_val.strip()

            untranslated_in_chunk = []
            for seg in chunk_segments:
                seg_id = seg["id"]
                th_text = trans_map.get(seg_id)
                # Ensure the text is actually translated (Thai characters present or no CJK)
                if th_text and (is_thai_text(th_text) or not re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", th_text)):
                    if style_lower.startswith(("jav", "adult")):
                        th_text = post_process_jav_thai(th_text, seg["original_text"], style=style_lower, is_llm_output=True)
                    seg["thai_text"] = th_text
                    seg["text"] = seg["thai_text"]
                else:
                    untranslated_in_chunk.append(seg)

            # Fallback for any segment in this chunk that was not returned or not translated
            if untranslated_in_chunk:
                u_origs = [s["original_text"] for s in untranslated_in_chunk]
                u_thais = translate_texts_to_thai(u_origs, style=style_lower, original_texts=u_origs)
                for seg, th_text in zip(untranslated_in_chunk, u_thais):
                    seg["thai_text"] = th_text
                    seg["text"] = th_text
        except Exception:
            # Fallback to google translate for this chunk if JSON parse fails
            orig_texts = [s["original_text"] for s in chunk_segments]
            thai_texts = translate_texts_to_thai(orig_texts, style=style_lower, original_texts=orig_texts)
            for seg, th_text in zip(chunk_segments, thai_texts):
                seg["thai_text"] = th_text
                seg["text"] = th_text

    chunk_list = [segments[i:i + chunk_size] for i in range(0, len(segments), chunk_size)]
    if len(chunk_list) <= 1:
        for ch in chunk_list:
            _translate_chunk(ch)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(chunk_list))) as executor:
            list(executor.map(_translate_chunk, chunk_list))

    return segments


def generate_srt(segments: List[Dict[str, Any]]) -> str:
    """
    Generate standard SubRip (.SRT) subtitle content.
    """
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start_str = format_timestamp(seg["start"], "srt")
        end_str = format_timestamp(seg["end"], "srt")
        text = seg.get("thai_text") or seg.get("text", "")
        srt_lines.append(f"{i}\n{start_str} --> {end_str}\n{text.strip()}\n")
    return "\n".join(srt_lines)


def generate_vtt(segments: List[Dict[str, Any]]) -> str:
    """
    Generate WebVTT (.VTT) subtitle content.
    """
    vtt_lines = ["WEBVTT\n"]
    for i, seg in enumerate(segments, 1):
        start_str = format_timestamp(seg["start"], "vtt")
        end_str = format_timestamp(seg["end"], "vtt")
        text = seg.get("thai_text") or seg.get("text", "")
        vtt_lines.append(f"{i}\n{start_str} --> {end_str}\n{text.strip()}\n")
    return "\n".join(vtt_lines)


def shift_subtitle_segments(segments: List[Dict[str, Any]], offset_seconds: float) -> List[Dict[str, Any]]:
    """
    Shift all subtitle timestamps forward or backward by offset_seconds.
    """
    shifted = []
    for s in segments:
        new_start = max(0.0, round(float(s["start"]) + offset_seconds, 3))
        new_end = max(new_start + 0.1, round(float(s["end"]) + offset_seconds, 3))
        item = dict(s)
        item["start"] = new_start
        item["end"] = new_end
        item["start_str"] = format_timestamp(new_start, "srt")
        item["end_str"] = format_timestamp(new_end, "srt")
        shifted.append(item)
    return shifted


_CUDA_SAFE_AVAILABLE: Optional[bool] = None


def check_cuda_availability() -> bool:
    """
    Check if CUDA GPU and its required runtime libraries (cublas64_12.dll on Windows)
    are present and operable, without risking driver deadlocks from repeated failed initializations.
    Result is cached per process.
    """
    global _CUDA_SAFE_AVAILABLE
    if _CUDA_SAFE_AVAILABLE is not None:
        return _CUDA_SAFE_AVAILABLE

    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() <= 0:
            _CUDA_SAFE_AVAILABLE = False
            return False

        if sys.platform == "win32":
            import ctypes
            try:
                ctypes.CDLL("cublas64_12.dll")
            except Exception:
                _CUDA_SAFE_AVAILABLE = False
                return False

        # Attempt quick probe
        from faster_whisper import WhisperModel
        m_probe = WhisperModel("tiny", device="cuda", compute_type="float16")
        dummy = np.zeros(1600, dtype=np.float32)
        list(m_probe.transcribe(dummy, beam_size=1)[0])
        del m_probe
        _CUDA_SAFE_AVAILABLE = True
        return True
    except Exception:
        _CUDA_SAFE_AVAILABLE = False
        return False


_WHISPER_CACHE: Dict[str, Any] = {}
_WHISPER_LOCK = threading.Lock()


def load_whisper_model_safely(model_size: str = "base"):
    """
    Safely load WhisperModel with CUDA GPU acceleration if available,
    with an active probe to guard against missing CUDA runtime DLLs (e.g. cublas64_12.dll on Windows).
    Caches loaded model instances in memory to eliminate repeated disk load overhead.
    Falls back gracefully to CPU int8 if CUDA is unavailable or broken.
    """
    cuda_ok = check_cuda_availability()
    cache_key = f"{model_size}_{'cuda' if cuda_ok else 'cpu'}"
    with _WHISPER_LOCK:
        if cache_key in _WHISPER_CACHE:
            return _WHISPER_CACHE[cache_key]

    from faster_whisper import WhisperModel

    model = None
    cpu_threads = min(16, max(4, os.cpu_count() or 4))
    if cuda_ok:
        try:
            model = WhisperModel(model_size, device="cuda", compute_type="float16")
        except Exception:
            pass

    if model is None:
        model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=cpu_threads)

    with _WHISPER_LOCK:
        _WHISPER_CACHE[cache_key] = model
    return model


def process_video_subtitles(
    video_path: str,
    output_dir: str,
    model_size: str = "base",
    source_lang: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    gemini_model: str = "gemini-2.5-flash",
    progress_callback: Optional[Callable[[float, str], None]] = None,
    ffmpeg_path: Optional[str] = None,
    translation_style: str = "jav",
    embed_mode: Optional[str] = "burn",
    font_size: int = 18,
) -> Dict[str, Any]:
    """
    Main pipeline:
    1. Extract audio from video
    2. Transcribe speech using faster-whisper (with real-time progress, caching, and CUDA GPU acceleration when available)
    3. Translate to Thai (supporting Gemini 2.5 Pro/Flash/Flash-Lite/2.0 or Free JAV Lexicon Model)
    4. Save .srt and .vtt files
    5. Automatically integrate subtitles directly into video clip (burn-in or softsub mux)
    """
    def report(percent: float, msg: str):
        if progress_callback:
            progress_callback(percent, msg)

    ffmpeg = ffmpeg_path or find_ffmpeg()
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    wav_path = os.path.join(output_dir, f"{base_name}_audio.wav")
    srt_path = os.path.join(output_dir, f"{base_name}_sub_th.srt")
    vtt_path = os.path.join(output_dir, f"{base_name}_sub_th.vtt")

    # Step 1: Extract audio
    report(10.0, "กำลังแยกเสียงจากวิดีโอ (Extracting audio)...")
    extracted_wav = extract_audio(video_path, wav_path, ffmpeg_path=ffmpeg)

    if not extracted_wav:
        # Video has no audio track
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("")
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n")
        report(100.0, "ไม่พบสัญญาณเสียงในวิดีโอ (No audio stream)")
        return {
            "success": True,
            "detected_language": "none",
            "segments": [],
            "srt_path": srt_path,
            "vtt_path": vtt_path,
            "srt_content": "",
            "vtt_content": "WEBVTT\n",
            "audio_path": None,
            "video_output_path": None,
            "burned_video_path": None,
            "softsub_video_path": None,
            "subtitled_video_path": None,
            "message": "วิดีโอนี้ไม่มีแทร็กเสียง (No audio stream detected in video)",
        }

    # Step 2: Transcribe with Whisper (Auto-detect CUDA for fast inference with safe probe)
    report(30.0, f"กำลังโหลดโมเดล Whisper ({model_size}) และถอดเสียง...")
    model = load_whisper_model_safely(model_size)

    lang_param = None
    if source_lang and source_lang.lower() not in ("auto", "none", ""):
        lang_param = source_lang.lower()

    style_clean = (translation_style or "jav").lower()

    import wave
    import numpy as np

    with wave.open(wav_path, "rb") as wf:
        raw_bytes = wf.readframes(wf.getnframes())
        audio_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    transcribe_kwargs = {
        "language": lang_param,
        "beam_size": 2,
        "vad_filter": True,
        "vad_parameters": dict(min_silence_duration_ms=400),
    }

    # Prime Whisper for adult / JAV content to accurately catch moans, gasps, and colloquial speech,
    # and apply repetition penalty & condition_on_previous_text=False to eliminate loop hallucinations
    if style_clean.startswith(("jav", "adult")) or lang_param == "ja":
        transcribe_kwargs["initial_prompt"] = (
            "ああ、うん、気持ちいい、ダメ、いく、すごい、もっと、奥、痛い、お願い、恥ずかしい、先輩、おじさん、中に出して、キスして、好き"
        )
        transcribe_kwargs["repetition_penalty"] = 1.15
        transcribe_kwargs["no_repeat_ngram_size"] = 3
        transcribe_kwargs["hallucination_silence_threshold"] = 2.0
        transcribe_kwargs["condition_on_previous_text"] = False

    whisper_segments, info = model.transcribe(
        audio_data,
        **transcribe_kwargs,
    )

    detected_lang = info.language
    total_dur = max(1.0, float(getattr(info, "duration", 0.0) or (len(audio_data) / 16000.0)))
    raw_segments = []
    seg_id = 1
    for seg in whisper_segments:
        text = seg.text.strip()
        if text:
            raw_segments.append({
                "id": seg_id,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "start_str": format_timestamp(seg.start, "srt"),
                "end_str": format_timestamp(seg.end, "srt"),
                "original_text": text,
                "thai_text": text,
                "text": text,
            })
            seg_id += 1
            progress_pct = 30.0 + min(38.0, (seg.end / total_dur) * 38.0)
            report(progress_pct, f"กำลังถอดเสียง: {format_timestamp(seg.end, 'srt')} / {format_timestamp(total_dur, 'srt')} ({len(raw_segments)} ท่อน)...")

    report(70.0, f"ถอดเสียงเสร็จสิ้น ({len(raw_segments)} ท่อน) ภาษาที่ตรวจพบ: {detected_lang}")

    if not raw_segments:
        # Empty speech
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("")
        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("WEBVTT\n")

        burned_path = None
        soft_path = None
        final_video_path = None
        clean_embed_mode = (embed_mode or "").lower().strip()
        if clean_embed_mode and clean_embed_mode not in ("none", "false", "0"):
            try:
                if clean_embed_mode in ("burn", "both", "auto", "hard"):
                    burned_path = os.path.join(output_dir, f"{base_name}_subtitled.mp4")
                    burn_subtitles_to_video(
                        video_path=video_path,
                        srt_path=srt_path,
                        output_video_path=burned_path,
                        font_size=font_size,
                        ffmpeg_path=ffmpeg,
                    )
                    final_video_path = burned_path
                if clean_embed_mode in ("soft", "both", "fast", "mux"):
                    soft_path = os.path.join(output_dir, f"{base_name}_softsub.mp4")
                    mux_subtitles_to_video(
                        video_path=video_path,
                        srt_path=srt_path,
                        output_video_path=soft_path,
                        ffmpeg_path=ffmpeg,
                    )
                    if not final_video_path:
                        final_video_path = soft_path
            except Exception:
                pass

        report(100.0, "ไม่พบเสียงพูดในวิดีโอ (No speech detected)")
        return {
            "success": True,
            "detected_language": detected_lang,
            "segments": [],
            "srt_path": srt_path,
            "vtt_path": vtt_path,
            "srt_content": "",
            "vtt_content": "WEBVTT\n",
            "audio_path": wav_path,
            "video_output_path": final_video_path,
            "burned_video_path": burned_path,
            "softsub_video_path": soft_path,
            "subtitled_video_path": final_video_path,
            "message": "ไม่พบเสียงพูดในวิดีโอ (No speech detected in video)",
        }

    # Step 3: Translate to Thai if not Thai
    report(75.0, f"กำลังแปลคำบรรยายเป็นภาษาไทย (สไตล์: {style_clean})...")

    # Determine if segments need translation:
    # 1) Detected language is not Thai, OR
    # 2) Any non-empty segment contains Japanese/CJK characters or foreign Latin words
    has_cjk_or_non_thai = any(
        bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", s.get("original_text", "")))
        or (
            bool(re.search(r"[a-zA-Z]{3,}", s.get("original_text", "")))
            and not any('\u0e00' <= c <= '\u0e7f' for c in s.get("original_text", ""))
        )
        for s in raw_segments
    )
    needs_translation = (detected_lang != "th") or has_cjk_or_non_thai

    if needs_translation:
        if gemini_api_key and gemini_api_key.strip():
            report(80.0, f"กำลังแปลภาษาไทยด้วย Gemini AI ({gemini_model} | สไตล์: {style_clean})...")
            try:
                raw_segments = translate_segments_with_gemini(
                    raw_segments,
                    gemini_api_key.strip(),
                    style=style_clean,
                    model=gemini_model,
                )
            except Exception as e:
                # fallback to google translate
                report(82.0, f"Gemini เกิดข้อผิดพลาด ({str(e)}) เปลี่ยนเป็นตัวแปล JAV สำรอง...")
                orig_texts = [s["original_text"] for s in raw_segments]
                thai_texts = translate_texts_to_thai(orig_texts, style=style_clean, original_texts=orig_texts, source_lang=source_lang)
                for seg, th_text in zip(raw_segments, thai_texts):
                    seg["thai_text"] = th_text
                    seg["text"] = th_text
        else:
            orig_texts = [s["original_text"] for s in raw_segments]
            thai_texts = translate_texts_to_thai(orig_texts, style=style_clean, original_texts=orig_texts, source_lang=source_lang)
            for seg, th_text in zip(raw_segments, thai_texts):
                seg["thai_text"] = th_text
                seg["text"] = th_text
    elif style_clean.startswith(("jav", "adult")):
        # If detected as Thai and content is already Thai, enhance if JAV style is selected
        for seg in raw_segments:
            seg["thai_text"] = post_process_jav_thai(seg["thai_text"], seg.get("original_text"), style=style_clean)
            seg["text"] = seg["thai_text"]

    # Final safety verification pass: Ensure NO non-Thai / Japanese dialogue slips into subtitles_th
    untranslated_indices = [
        idx for idx, seg in enumerate(raw_segments)
        if seg.get("original_text", "").strip()
        and (
            bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", seg.get("thai_text", "")))
            or (
                not any('\u0e00' <= c <= '\u0e7f' for c in seg.get("thai_text", ""))
                and bool(re.search(r"[\u3040-\u30ff\u4e00-\u9fff|a-zA-Z]", seg.get("original_text", "")))
                and seg.get("thai_text", "").strip() == seg.get("original_text", "").strip()
            )
        )
    ]
    if untranslated_indices:
        u_origs = [raw_segments[idx]["original_text"] for idx in untranslated_indices]
        u_thais = translate_texts_to_thai(u_origs, style=style_clean, original_texts=u_origs, source_lang=source_lang)
        for idx, th_text in zip(untranslated_indices, u_thais):
            raw_segments[idx]["thai_text"] = th_text
            raw_segments[idx]["text"] = th_text

    # Ultimate safety guarantee: If any segment STILL contains CJK characters, clean them out
    for seg in raw_segments:
        th = seg.get("thai_text", "")
        if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", th):
            cue_val = post_process_jav_thai(th, seg.get("original_text"), style=style_clean)
            if cue_val and not re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", cue_val):
                seg["thai_text"] = cue_val
                seg["text"] = cue_val
            else:
                cleaned_cjk = re.sub(r"[\u3040-\u30ff\u4e00-\u9fff]+", "", th).strip()
                if cleaned_cjk:
                    seg["thai_text"] = cleaned_cjk
                    seg["text"] = cleaned_cjk
                elif style_clean.startswith(("jav", "adult")):
                    seg["thai_text"] = "..."
                    seg["text"] = "..."

    # Step 4: Generate SRT and VTT
    report(92.0, "กำลังบันทึกไฟล์คำบรรยาย (.srt, .vtt)...")
    srt_content = generate_srt(raw_segments)
    vtt_content = generate_vtt(raw_segments)

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write(vtt_content)

    # Step 5: Automatically integrate subtitles directly into video clip
    burned_path = None
    soft_path = None
    final_video_path = None

    clean_embed_mode = (embed_mode or "").lower().strip()
    if clean_embed_mode and clean_embed_mode not in ("none", "false", "0"):
        report(95.0, f"กำลังนำซับไตเติลใส่ลงในคลิปวิดีโอ ({clean_embed_mode})...")
        try:
            if clean_embed_mode in ("burn", "both", "auto", "hard"):
                burned_path = os.path.join(output_dir, f"{base_name}_subtitled.mp4")
                burn_subtitles_to_video(
                    video_path=video_path,
                    srt_path=srt_path,
                    output_video_path=burned_path,
                    font_size=font_size,
                    ffmpeg_path=ffmpeg,
                )
                final_video_path = burned_path

            if clean_embed_mode in ("soft", "both", "fast", "mux"):
                soft_path = os.path.join(output_dir, f"{base_name}_softsub.mp4")
                mux_subtitles_to_video(
                    video_path=video_path,
                    srt_path=srt_path,
                    output_video_path=soft_path,
                    ffmpeg_path=ffmpeg,
                )
                if not final_video_path:
                    final_video_path = soft_path
        except Exception as embed_err:
            report(98.0, f"การนำซับใส่คลิปเตือน: {str(embed_err)}")

    report(100.0, "สร้างซับไทยและนำซับใส่คลิปเรียบร้อย!")

    return {
        "success": True,
        "detected_language": detected_lang,
        "segments": raw_segments,
        "srt_path": srt_path,
        "vtt_path": vtt_path,
        "srt_content": srt_content,
        "vtt_content": vtt_content,
        "audio_path": wav_path,
        "video_output_path": final_video_path,
        "burned_video_path": burned_path,
        "softsub_video_path": soft_path,
        "subtitled_video_path": final_video_path,
    }


def mux_subtitles_to_video(
    video_path: str,
    srt_path: str,
    output_video_path: str,
    ffmpeg_path: Optional[str] = None,
) -> str:
    """
    Fast-mux subtitles into video container using FFmpeg stream copy (-c copy -c:s mov_text/srt).
    Executes in 1-2 seconds with zero re-encoding and zero video quality degradation.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"ไม่พบไฟล์วิดีโอ: {video_path}")
    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"ไม่พบไฟล์ซับไตเติล: {srt_path}")

    abs_out = os.path.abspath(output_video_path)
    out_dir = os.path.dirname(abs_out)
    os.makedirs(out_dir, exist_ok=True)

    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        srt_text = f.read().strip()
    if not srt_text:
        shutil.copy2(video_path, abs_out)
        return abs_out

    ffmpeg = ffmpeg_path or find_ffmpeg()
    ext = os.path.splitext(abs_out)[1].lower()
    sub_codec = "srt" if ext == ".mkv" else "mov_text"

    cmd = [
        ffmpeg,
        "-y",
        "-i", os.path.abspath(video_path),
        "-i", os.path.abspath(srt_path),
        "-c", "copy",
        "-c:s", sub_codec,
        "-metadata:s:s:0", "language=tha",
        "-metadata:s:s:0", "title=Thai Subtitles",
        abs_out,
    ]

    result = subprocess.run(
        cmd,
        cwd=out_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    if result.returncode != 0:
        err_msg = (result.stderr or "")[-500:]
        raise RuntimeError(f"FFmpeg mux subtitle error: {err_msg}")

    if not os.path.isfile(abs_out) or os.path.getsize(abs_out) == 0:
        raise RuntimeError("การฝังซับล้มเหลว ไฟล์วิดีโอผลลัพธ์มีขนาด 0 ไบต์")

    return abs_out


def burn_subtitles_to_video(
    video_path: str,
    srt_path: str,
    output_video_path: str,
    font_size: int = 18,
    ffmpeg_path: Optional[str] = None,
) -> str:
    """
    Burn (hardsub) SRT subtitles into an MP4 video using FFmpeg with clear styling.
    Uses safe temporary clean ASCII filename inside working directory to ensure rock-solid
    compatibility on Windows with any special characters, brackets, or Unicode in paths.
    """
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"ไม่พบไฟล์วิดีโอ: {video_path}")
    if not os.path.isfile(srt_path):
        raise FileNotFoundError(f"ไม่พบไฟล์ซับไตเติล: {srt_path}")

    abs_out = os.path.abspath(output_video_path)
    out_dir = os.path.dirname(abs_out)
    os.makedirs(out_dir, exist_ok=True)

    # shortcut: If SRT has no subtitle content (e.g. silent video), copy input to output
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        srt_text = f.read().strip()
    if not srt_text:
        shutil.copy2(video_path, abs_out)
        return abs_out

    ffmpeg = ffmpeg_path or find_ffmpeg()

    # Use a clean, safe ASCII filename for the subtitles filter to completely prevent
    # FFmpeg filter parsing errors caused by brackets [...], spaces, quotes, or non-ASCII characters
    temp_clean_name = f"_burn_sub_{os.getpid()}.srt"
    temp_clean_path = os.path.join(out_dir, temp_clean_name)
    shutil.copy2(srt_path, temp_clean_path)

    try:
        # Style with Leelawadee UI for native, beautiful Thai rendering
        style = (
            f"force_style='Fontname=Leelawadee UI,FontSize={font_size},"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,MarginV=25'"
        )
        vf_filter = f"subtitles={temp_clean_name}:{style}"

        cmd = [
            ffmpeg,
            "-y",
            "-i", os.path.abspath(video_path),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "copy",
            "-threads", "0",
            abs_out,
        ]

        # Execute with cwd=out_dir so relative subtitle name is resolved without drive colon conflicts.
        # Enforce UTF-8 encoding so Windows Thai cp874 never triggers UnicodeDecodeError in reader thread.
        result = subprocess.run(
            cmd,
            cwd=out_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            err_msg = (result.stderr or "")[-500:]
            raise RuntimeError(f"FFmpeg burn subtitle error: {err_msg}")

        if not os.path.isfile(abs_out) or os.path.getsize(abs_out) == 0:
            raise RuntimeError("การฝังซับล้มเหลว ไฟล์วิดีโอผลลัพธ์มีขนาด 0 ไบต์")

        return abs_out
    finally:
        if os.path.isfile(temp_clean_path):
            try:
                os.remove(temp_clean_path)
            except Exception:
                pass
