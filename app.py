"""
Web Application for Thai Subtitle Generator.
Run via: python app.py
Opens http://localhost:5000 in your web browser.
"""

import os
import sys

# Ensure stdout and stderr exist (in windowed/frozen mode they may be None)
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

# Ensure console supports UTF-8 on Windows Thai codepage (cp874)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import uuid
import shutil
import threading
import webbrowser
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any

from engine import (
    process_video_subtitles,
    burn_subtitles_to_video,
    generate_srt,
    generate_vtt,
    shift_subtitle_segments,
    find_ffmpeg,
)

BASE_DIR = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)

# Determine writable data directory (Vercel and AWS Lambda have read-only filesystems except /tmp)
IS_SERVERLESS = bool(
    os.environ.get("VERCEL")
    or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or not os.access(BASE_DIR, os.W_OK)
)

if IS_SERVERLESS:
    DATA_DIR = os.path.join("/tmp", "subfynn_data")
else:
    DATA_DIR = os.path.join(BASE_DIR, "data")

UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")

try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
except Exception:
    pass

# In-memory task tracker
tasks: Dict[str, Dict[str, Any]] = {}
tasks_lock = threading.Lock()


def run_process_task(
    task_id: str,
    video_path: str,
    model_size: str,
    source_lang: str,
    gemini_key: str,
    translation_style: str = "jav",
    gemini_model: str = "gemini-2.5-flash",
    embed_mode: str = "burn",
):
    def on_progress(percent: float, message: str):
        with tasks_lock:
            if task_id in tasks:
                tasks[task_id]["progress"] = percent
                tasks[task_id]["status_message"] = message

    try:
        task_out_dir = os.path.join(OUTPUT_DIR, task_id)
        os.makedirs(task_out_dir, exist_ok=True)

        res = process_video_subtitles(
            video_path=video_path,
            output_dir=task_out_dir,
            model_size=model_size,
            source_lang=source_lang,
            gemini_api_key=gemini_key,
            gemini_model=gemini_model,
            translation_style=translation_style,
            embed_mode=embed_mode,
            progress_callback=on_progress,
        )

        out_video = os.path.join(OUTPUT_DIR, task_id, "video_with_th_subtitles.mp4")
        if res.get("video_output_path") and os.path.isfile(res["video_output_path"]):
            if os.path.abspath(res["video_output_path"]) != os.path.abspath(out_video):
                shutil.copy2(res["video_output_path"], out_video)

        with tasks_lock:
            tasks[task_id]["state"] = "completed"
            tasks[task_id]["progress"] = 100.0
            tasks[task_id]["status_message"] = "สร้างซับไทยและนำซับใส่คลิปเสร็จสิ้น!"
            tasks[task_id]["result"] = res
            if os.path.isfile(out_video):
                tasks[task_id]["subtitled_video_url"] = f"/api/download_video?task_id={task_id}"
    except Exception as e:
        with tasks_lock:
            tasks[task_id]["state"] = "failed"
            tasks[task_id]["status_message"] = f"เกิดข้อผิดพลาด: {str(e)}"
            tasks[task_id]["error"] = str(e)


def run_burn_task(burn_id: str, task_id: str, font_size: int):
    try:
        with tasks_lock:
            tasks[burn_id]["state"] = "processing"
            tasks[burn_id]["status_message"] = "กำลังฝังซับไตเติลลงในวิดีโอด้วย FFmpeg..."

        task_data = None
        with tasks_lock:
            task_data = tasks.get(task_id)

        if not task_data or "result" not in task_data:
            raise ValueError("ไม่พบข้อมูลงานต้นฉบับ")

        video_path = task_data["video_path"]
        srt_path = task_data["result"]["srt_path"]
        out_video = os.path.join(OUTPUT_DIR, task_id, "video_with_th_subtitles.mp4")

        burn_subtitles_to_video(
            video_path=video_path,
            srt_path=srt_path,
            output_video_path=out_video,
            font_size=font_size,
        )

        with tasks_lock:
            tasks[burn_id]["state"] = "completed"
            tasks[burn_id]["progress"] = 100.0
            tasks[burn_id]["status_message"] = "ฝังซับลงวิดีโอเรียบร้อย!"
            tasks[burn_id]["burned_video_path"] = out_video
    except Exception as e:
        with tasks_lock:
            tasks[burn_id]["state"] = "failed"
            tasks[burn_id]["status_message"] = f"การฝังซับล้มเหลว: {str(e)}"
            tasks[burn_id]["error"] = str(e)


INDEX_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SubFynn Studio — โปรแกรมสร้างซับไทยอัตโนมัติ (AI Thai Subtitle Generator)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Kanit:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        /* Kanit Typography Classes */
        .kanit-thin {
          font-family: "Kanit", sans-serif;
          font-weight: 100;
          font-style: normal;
        }

        .kanit-extralight {
          font-family: "Kanit", sans-serif;
          font-weight: 200;
          font-style: normal;
        }

        .kanit-light {
          font-family: "Kanit", sans-serif;
          font-weight: 300;
          font-style: normal;
        }

        .kanit-regular {
          font-family: "Kanit", sans-serif;
          font-weight: 400;
          font-style: normal;
        }

        .kanit-medium {
          font-family: "Kanit", sans-serif;
          font-weight: 500;
          font-style: normal;
        }

        .kanit-semibold {
          font-family: "Kanit", sans-serif;
          font-weight: 600;
          font-style: normal;
        }

        .kanit-bold {
          font-family: "Kanit", sans-serif;
          font-weight: 700;
          font-style: normal;
        }

        .kanit-extrabold {
          font-family: "Kanit", sans-serif;
          font-weight: 800;
          font-style: normal;
        }

        .kanit-black {
          font-family: "Kanit", sans-serif;
          font-weight: 900;
          font-style: normal;
        }

        .kanit-thin-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 100;
          font-style: italic;
        }

        .kanit-extralight-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 200;
          font-style: italic;
        }

        .kanit-light-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 300;
          font-style: italic;
        }

        .kanit-regular-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 400;
          font-style: italic;
        }

        .kanit-medium-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 500;
          font-style: italic;
        }

        .kanit-semibold-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 600;
          font-style: italic;
        }

        .kanit-bold-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 700;
          font-style: italic;
        }

        .kanit-extrabold-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 800;
          font-style: italic;
        }

        .kanit-black-italic {
          font-family: "Kanit", sans-serif;
          font-weight: 900;
          font-style: italic;
        }

        :root {
            --bg-deep: #23212C;
            --glass-surface: rgba(44, 41, 56, 0.78);
            --glass-surface-hover: rgba(53, 49, 68, 0.88);
            --glass-surface-active: rgba(62, 57, 80, 0.94);
            --glass-border: rgba(210, 200, 230, 0.18);
            --glass-border-hover: rgba(210, 200, 230, 0.32);
            --glass-highlight: rgba(255, 255, 255, 0.22);
            --accent-indigo: #8b5cf6;
            --accent-pink: #d946ef;
            --accent-cyan: #38bdf8;
            --accent-emerald: #10b981;
            --text-heading: #f8fafc;
            --text-primary: #f1f5f9;
            --text-body: #e2e8f0;
            --text-secondary: #cbd5e1;
            --text-muted: #94a3b8;
            --radius-card: 24px;
            --radius-input: 14px;
            --radius-pill: 9999px;
            --glass-shadow: 0 20px 48px rgba(10, 8, 18, 0.42), inset 0 1px 0 rgba(255, 255, 255, 0.12);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Kanit', sans-serif;
        }

        body, button, input, select, textarea {
            font-family: 'Kanit', sans-serif;
        }

        body {
            background-color: var(--bg-deep);
            background-image: 
                radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.18) 0px, transparent 55%),
                radial-gradient(at 100% 0%, rgba(217, 70, 239, 0.14) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(56, 189, 248, 0.08) 0px, transparent 60%),
                radial-gradient(at 0% 100%, rgba(35, 33, 44, 0.9) 0px, transparent 55%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.12) 0px, transparent 55%);
            background-attachment: fixed;
            background-size: cover;
            color: var(--text-body);
            font-size: 16px;
            line-height: 1.65;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
            padding: 30px 20px 60px;
        }

        /* 1. Ambient Floating Canvas Orbs */
        .ambient-canvas {
            position: fixed;
            inset: 0;
            z-index: 0;
            overflow: hidden;
            pointer-events: none;
        }

        .orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(110px);
            opacity: 0.35;
            animation: floatOrb 18s ease-in-out infinite alternate;
        }

        .orb-1 {
            width: 540px;
            height: 540px;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.45), transparent 70%);
            top: -100px;
            left: -100px;
        }

        .orb-2 {
            width: 480px;
            height: 480px;
            background: radial-gradient(circle, rgba(217, 70, 239, 0.35), transparent 70%);
            bottom: -100px;
            right: -80px;
            animation-delay: -6s;
        }

        .orb-3 {
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(56, 189, 248, 0.28), transparent 70%);
            top: 45%;
            left: 50%;
            transform: translate(-50%, -50%);
            opacity: 0.35;
            animation-delay: -12s;
        }

        @keyframes floatOrb {
            0% { transform: translate(0, 0) scale(1); }
            100% { transform: translate(45px, -35px) scale(1.08); }
        }

        /* 2. App Shell & Layout Structure */
        .app-shell {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 24px;
            position: relative;
            z-index: 1;
        }

        /* 3. Glass Panels */
        .glass-panel {
            background: var(--glass-surface);
            backdrop-filter: blur(28px) saturate(135%);
            -webkit-backdrop-filter: blur(28px) saturate(135%);
            border: 1px solid var(--glass-border);
            border-top: 1px solid var(--glass-highlight);
            border-left: 1px solid var(--glass-highlight);
            border-radius: var(--radius-card);
            box-shadow: var(--glass-shadow);
            padding: 32px;
            transition: border-color 0.2s ease, background-color 0.2s ease;
        }

        .glass-panel:hover {
            border-color: var(--glass-border-hover);
        }

        /* 3. Centered Header Banner */
        .header-banner {
            text-align: center;
            margin-bottom: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .banner-title-row {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 14px;
            flex-wrap: wrap;
        }

        .banner-title {
            font-size: 2.1rem;
            font-weight: 700;
            color: var(--text-heading);
            letter-spacing: -0.02em;
            text-shadow: 0 2px 14px rgba(0, 0, 0, 0.4);
            margin: 0;
        }

        .banner-badge {
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.24);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: var(--radius-pill);
            padding: 5px 16px;
            font-size: 0.85rem;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: 0.5px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
        }

        .banner-desc {
            color: var(--text-body);
            font-size: 1.02rem;
            max-width: 720px;
            line-height: 1.6;
            margin: 0;
        }

        .banner-actions {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
            margin-top: 4px;
        }

        .status-pill {
            padding: 6px 16px;
            border-radius: var(--radius-pill);
            font-size: 0.82rem;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.35);
            box-shadow: 0 2px 10px rgba(16, 185, 129, 0.2);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn-intro-pill {
            background: rgba(139, 92, 246, 0.22);
            border: 1px solid rgba(139, 92, 246, 0.45);
            color: #ffffff;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-intro-pill:hover {
            background: rgba(139, 92, 246, 0.38);
            border-color: rgba(139, 92, 246, 0.65);
            transform: translateY(-1px);
        }

        /* 5. Dropzone Glass */
        .dropzone-glass {
            border: 2px dashed rgba(255, 255, 255, 0.25);
            border-radius: 20px;
            padding: 42px 24px;
            text-align: center;
            background: rgba(25, 23, 34, 0.45);
            cursor: pointer;
            transition: all 0.25s ease;
        }

        .dropzone-glass:hover, .dropzone-glass.dragover {
            border-color: var(--accent-cyan);
            background: rgba(56, 189, 248, 0.08);
            transform: translateY(-2px);
            box-shadow: 0 0 30px rgba(56, 189, 248, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }

        .upload-icon-wrapper {
            margin-bottom: 12px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .dropzone-glass h3 {
            color: var(--text-heading);
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 6px;
        }

        .file-info {
            margin-top: 16px;
            font-weight: 600;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.15);
            display: none;
            padding: 8px 22px;
            border-radius: var(--radius-pill);
            border: 1px solid rgba(56, 189, 248, 0.35);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            font-size: 0.95rem;
        }

        .file-info:not(:empty) {
            display: inline-block;
        }

        /* 6. Form Controls & Grid with Equal Alignment */
        .options-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-top: 24px;
        }

        .option-group {
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }

        .option-group label {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-secondary);
            min-height: 48px;
            display: flex;
            align-items: flex-end;
            margin-bottom: 8px;
            line-height: 1.35;
        }

        .option-group select, 
        .option-group input[type="text"], 
        .option-group input[type="password"] {
            width: 100%;
            height: 48px;
            box-sizing: border-box;
            background: rgba(25, 23, 34, 0.75);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-input);
            padding: 0 16px;
            color: var(--text-heading);
            font-size: 0.96rem;
            outline: none;
            transition: all 0.2s ease;
            box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4);
        }

        .option-group select:focus, 
        .option-group input:focus {
            border-color: var(--accent-indigo);
            background: rgba(30, 27, 42, 0.90);
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.3), 0 0 18px rgba(139, 92, 246, 0.25);
        }

        .option-group select option {
            background-color: #23212C;
            color: #ffffff;
            padding: 8px;
        }

        /* 8. Glowing Action Buttons */
        .btn {
            padding: 12px 24px;
            font-size: 0.98rem;
            font-weight: 600;
            border-radius: var(--radius-input);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            text-decoration: none;
            border: 1px solid transparent;
        }

        .btn-glass-primary {
            background: linear-gradient(135deg, #7c3aed, #a855f7);
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 16px;
            padding: 15px 36px;
            color: #ffffff;
            font-weight: 700;
            font-size: 1.05rem;
            cursor: pointer;
            box-shadow: 0 10px 24px -6px rgba(124, 58, 237, 0.5);
            transition: all 0.25s ease;
        }

        .btn-glass-primary:hover:not(:disabled) {
            transform: translateY(-2px) scale(1.01);
            box-shadow: 0 14px 30px -6px rgba(168, 85, 247, 0.6);
            border-color: rgba(255, 255, 255, 0.55);
        }

        .btn-glass-primary:disabled {
            opacity: 0.40;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .btn-emerald {
            background: linear-gradient(135deg, #059669, #10b981);
            color: #ffffff;
            border: 1px solid rgba(52, 211, 153, 0.4);
            box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4);
        }

        .btn-emerald:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(16, 185, 129, 0.6);
        }

        .btn-violet {
            background: linear-gradient(135deg, #6d28d9, #8b5cf6);
            color: #ffffff;
            border: 1px solid rgba(196, 181, 253, 0.36);
            box-shadow: 0 8px 20px rgba(109, 40, 217, 0.36);
        }

        .btn-violet:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 12px 26px rgba(109, 40, 217, 0.5);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
            border: 1px solid rgba(255, 255, 255, 0.16);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
        }

        .btn-secondary:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.16);
            border-color: rgba(255, 255, 255, 0.35);
            transform: translateY(-1px);
        }

        .btn-sm {
            padding: 7px 16px;
            font-size: 0.85rem;
            border-radius: var(--radius-input);
        }

        .btn-danger {
            background: rgba(239, 68, 68, 0.2);
            color: #fecaca;
            border: 1px solid rgba(239, 68, 68, 0.45);
        }

        .btn-danger:hover:not(:disabled) {
            background: rgba(239, 68, 68, 0.35);
            color: #ffffff;
            border-color: #ef4444;
        }

        /* 9. Glowing Gradient Progress Bar */
        .progress-box {
            display: none;
            margin-top: 24px;
        }

        .progress-bar-bg {
            background: rgba(25, 23, 34, 0.7);
            border-radius: var(--radius-pill);
            height: 12px;
            overflow: hidden;
            margin-bottom: 10px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.6);
        }

        .progress-bar-fill {
            background: linear-gradient(90deg, #8b5cf6, var(--accent-cyan));
            box-shadow: 0 0 16px rgba(56, 189, 248, 0.42);
            width: 0%;
            height: 100%;
            transition: width 0.35s ease;
            border-radius: var(--radius-pill);
        }

        .progress-status {
            font-size: 0.94rem;
            color: var(--text-body);
            text-align: center;
            font-weight: 500;
        }

        /* 10. Result Section & Subtitle Editor */
        .result-section {
            display: none;
        }

        .preview-layout {
            display: grid;
            grid-template-columns: 1fr;
            gap: 24px;
        }

        @media (min-width: 920px) {
            .preview-layout {
                grid-template-columns: 1.15fr 1fr;
            }
        }

        .video-container {
            width: 100%;
            background: #000000;
            border-radius: 20px;
            overflow: hidden;
            position: relative;
            border: 1px solid rgba(255, 255, 255, 0.16);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
        }

        video {
            width: 100%;
            display: block;
            max-height: 460px;
        }

        .tools-panel {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 14px;
            padding: 12px 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
        }

        .shift-tools {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }

        .subtitles-editor {
            max-height: 480px;
            overflow-y: auto;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 20px;
            background: rgba(25, 23, 34, 0.75);
            box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.5);
            padding: 8px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .sub-row {
            padding: 12px 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.035);
            display: flex;
            flex-direction: column;
            gap: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .sub-row:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: rgba(255, 255, 255, 0.20);
        }

        .sub-row.active {
            background: rgba(139, 92, 246, 0.18) !important;
            border-color: rgba(139, 92, 246, 0.5) !important;
            border-left: 4px solid var(--accent-indigo) !important;
        }

        .sub-time {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 3px 10px;
            border-radius: 8px;
            font-weight: 600;
        }

        .sub-text-orig {
            font-size: 0.85rem;
            color: var(--text-muted);
        }

        .sub-text-thai {
            font-size: 0.98rem;
            color: var(--text-heading);
            width: 100%;
            background: rgba(25, 23, 34, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 8px 12px;
        }

        .sub-text-thai:focus {
            background: rgba(30, 27, 42, 0.9);
            border-color: var(--accent-indigo);
            outline: none;
            box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.25);
        }

        .actions-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 24px;
        }

        :focus-visible {
            outline: 3px solid rgba(56, 189, 248, 0.9);
            outline-offset: 3px;
        }

        .sub-text-thai,
        .sub-text-orig {
            line-height: 1.65;
        }

        @media (max-width: 640px) {
            body { padding: 16px 12px 32px; }
            .app-shell { gap: 16px; }
            .glass-panel { padding: 20px; border-radius: 20px; }
            .banner-title { font-size: 1.55rem; }
            .options-grid { grid-template-columns: 1fr; gap: 16px; }
            .dropzone-glass { padding: 30px 18px; }
            .actions-bar .btn { flex: 1 1 100%; }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: 0.01ms !important;
            }
        }
    </style>
</head>
<body>
    <!-- 1. Ambient Floating Glowing Orbs -->
    <div class="ambient-canvas">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
    </div>

    <div class="app-shell">
        <!-- 2. Header Banner -->
        <header class="header-banner">
            <div class="banner-title-row">
                <h1 class="banner-title kanit-bold">SubFynn - โปรแกรมสร้างซับไทยอัตโนมัติ</h1>
                <span class="banner-badge kanit-semibold">SubFynn Glass Edition</span>
            </div>
            <p class="banner-desc kanit-light">อัปโหลดวิดีโอจากที่ไหนก็ได้ แล้วระบบจะถอดเสียงและแปลซับไทยให้อัตโนมัติ พร้อมฝังซับลงวิดีโอ</p>
            <div class="banner-actions">
                <button class="status-pill btn-intro-pill kanit-medium" onclick="openIntroModal()">ดูวิดีโอเปิดตัว (Intro)</button>
                <span class="status-pill kanit-regular">● Engine Ready</span>
            </div>
        </header>

        <!-- 3. Upload & Configuration Glass Panel -->
        <main class="glass-panel">
            <div class="dropzone-glass" id="dropZone" onclick="document.getElementById('videoFile').click()">
                <div class="upload-icon-wrapper">
                    <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent-cyan); filter: drop-shadow(0 4px 12px rgba(56, 189, 248, 0.35));">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="17 8 12 3 7 8"></polyline>
                        <line x1="12" y1="3" x2="12" y2="15"></line>
                    </svg>
                </div>
                <h3 class="kanit-semibold">ลากไฟล์วิดีโอมาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์</h3>
                <p class="kanit-light" style="color: var(--text-muted); font-size: 0.88rem; margin-top: 4px;">รองรับ MP4, MKV, MOV, AVI, WEBM, FLV, TS</p>
                <div class="file-info kanit-semibold" id="fileInfo"></div>
                <input type="file" id="videoFile" accept="video/*,audio/*" style="display: none;" onchange="handleFileSelect(this.files[0])">
            </div>

            <div class="options-grid">
                <div class="option-group">
                    <label for="modelSelect" class="kanit-medium">ขนาดโมเดล Whisper (AI Speech-to-Text)</label>
                    <select id="modelSelect" class="kanit-regular">
                        <option value="large-v3" selected>Large-v3 (แม่นยำสูงสุด ถอดเสียงชัดเจน)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="styleSelect" class="kanit-medium">สไตล์การแปลคำบรรยาย (Translation Style)</label>
                    <select id="styleSelect" class="kanit-regular">
                        <option value="jav" selected>หนังผู้ใหญ่ / JAV 18+ (มาตรฐานแฟนซับ: เร่าร้อน เสียว เป็นธรรมชาติ)</option>
                        <option value="jav_dirty">หนังผู้ใหญ่ / JAV 18+ (สายดุดัน / หยาบคายได้เต็มที่: ควย หี เย็ด ซอยยับ แตกใน โคตรเสียว ไม่เซ็นเซอร์)</option>
                        <option value="jav_hardcore">หนังผู้ใหญ่ / JAV 18+ (Hardcore ดิบเถื่อน หยาบคายขั้นสุด)</option>
                        <option value="jav_sweet">หนังผู้ใหญ่ / JAV 18+ (สายหวานอ้อน: เสียวจัง พี่คะ หนูไม่ไหวแล้ว)</option>
                        <option value="general">ทั่วไป / ภาพยนตร์ (General / Cinematic)</option>
                        <option value="anime">อนิเมะ / การ์ตูน (Anime & Manga)</option>
                        <option value="drama">ดราม่า / ซีรีส์ (Drama & Emotional)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="geminiModelSelect" class="kanit-medium">โมเดล AI แปลภาษา (Translation Model)</label>
                    <select id="geminiModelSelect" class="kanit-regular">
                        <option value="gemini-2.5-flash" selected>Gemini 2.5 Flash (เร็ว แม่นยำสูง แนะนำ)</option>
                        <option value="gemini-2.5-pro">Gemini 2.5 Pro (แปลลึกซึ้ง บริบทแม่นยำ)</option>
                        <option value="gemini-3.5-live-translate-preview">Gemini Live Translate (3.5 Preview แปลบทสนทนาสด)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="embedModeSelect" class="kanit-medium">เอาซับใส่คลิปวิดีโอทันที (Auto-embed Video)</label>
                    <select id="embedModeSelect" class="kanit-regular">
                        <option value="burn" selected>ฝังซับติดภาพถาวร (Hardsub Burn-in - แนะนำ)</option>
                        <option value="soft">ฝังซับในไฟล์เร็ว 1 วิ (Fast Softsub - เปิด/ปิดได้ ไม่เสียความคมชัด)</option>
                        <option value="both">ทำทั้ง 2 แบบ (ทั้ง Hardsub และ Softsub)</option>
                        <option value="none">สร้างเฉพาะไฟล์ซับ (.SRT / .VTT)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="langSelect" class="kanit-medium">ภาษาเสียงพูดต้นฉบับในวิดีโอ (ซับไตเติลผลลัพธ์จะเป็นภาษาไทยเสมอ)</label>
                    <select id="langSelect" class="kanit-regular">
                        <option value="ja" selected>ญี่ปุ่น (Japanese - แนะนำสำหรับ JAV/อนิเมะ)</option>
                        <option value="auto">ตรวจจับอัตโนมัติ (Auto-Detect)</option>
                        <option value="en">อังกฤษ (English)</option>
                        <option value="zh">จีน (Chinese)</option>
                        <option value="ko">เกาหลี (Korean)</option>
                        <option value="th">ไทย (Thai - กรณีเสียงต้นฉบับพูดไทยอยู่แล้ว)</option>
                        <option value="fr">ฝรั่งเศส (French)</option>
                        <option value="de">เยอรมัน (German)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="geminiKey" class="kanit-medium">Google Gemini API Key (ไม่บังคับ - ปลดล็อกการแปลขั้นสุด)</label>
                    <input type="password" id="geminiKey" class="kanit-regular" placeholder="วาง API Key หรือเว้นว่างเพื่อใช้ระบบแปล JAV ฟรี">
                </div>
            </div>

            <div style="margin-top: 28px; text-align: center;">
                <button class="btn btn-glass-primary kanit-bold" id="startBtn" onclick="startProcessing()" disabled>
                    เริ่มสร้างซับไทย (Generate Thai Subtitles)
                </button>
            </div>

            <div class="progress-box" id="progressBox">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="progressBar"></div>
                </div>
                <div class="progress-status kanit-medium" id="progressStatus">กำลังเตรียมการ...</div>
            </div>
        </main>

        <!-- 4. Result Preview & Subtitle Editor Glass Panel -->
        <section class="glass-panel result-section" id="resultCard">
            <h2 class="kanit-bold" style="margin-bottom: 20px; font-size: 1.35rem; color: #ffffff;">ตัวอย่างวิดีโอและคำบรรยายซับไทย</h2>
            <div class="preview-layout">
                <div class="video-container">
                    <video id="videoPlayer" controls playsinline></video>
                </div>
                <div>
                    <div class="tools-panel">
                        <div class="shift-tools">
                            <span class="kanit-medium" style="font-size: 0.85rem; color: var(--text-secondary);">ปรับเวลา:</span>
                            <button class="btn btn-secondary btn-sm kanit-medium" onclick="shiftSubtitles(-0.5)" title="เลื่อนซับเร็วขึ้น 0.5 วินาที">-0.5s</button>
                            <button class="btn btn-secondary btn-sm kanit-medium" onclick="shiftSubtitles(0.5)" title="เลื่อนซับช้าลง 0.5 วินาที">+0.5s</button>
                            <button class="btn btn-secondary btn-sm kanit-medium" onclick="promptCustomShift()">กำหนดเอง...</button>
                        </div>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <span id="subCount" class="kanit-semibold" style="font-size: 0.88rem; color: #38bdf8; font-weight: 600;">0 ท่อน</span>
                        </div>
                    </div>
                    <div class="subtitles-editor" id="subEditor"></div>
                </div>
            </div>

            <div class="actions-bar">
                <a class="btn btn-emerald kanit-semibold" id="downloadVideoBtn" href="#" style="text-decoration: none;">ดาวน์โหลดวิดีโอพร้อมซับ (Subtitled Video MP4)</a>
                <button class="btn btn-secondary kanit-medium" onclick="downloadSRT()">ดาวน์โหลดไฟล์ .SRT</button>
                <button class="btn btn-secondary kanit-medium" onclick="downloadVTT()">ดาวน์โหลดไฟล์ .VTT</button>
                <button class="btn btn-violet kanit-semibold" id="burnBtn" onclick="burnSubtitles()">ฝังซับใหม่ (Custom Burn)</button>
                <button class="btn btn-secondary kanit-medium" onclick="copyAllText()">คัดลอกข้อความทั้งหมด</button>
            </div>

            <div class="progress-box" id="burnProgressBox" style="margin-top: 18px;">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="burnProgressBar" style="width: 100%;"></div>
                </div>
                <div class="progress-status kanit-medium" id="burnStatus">กำลังฝังซับไตเติล...</div>
            </div>
        </section>

        <!-- 5. Intro Video Modal Dialog -->
        <div id="introModal" style="display: none; position: fixed; inset: 0; background: rgba(5, 10, 20, 0.85); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); z-index: 9999; align-items: center; justify-content: center; padding: 20px;" onclick="if(event.target===this) closeIntroModal()">
            <div class="glass-panel" style="max-width: 860px; width: 100%; padding: 24px; border-radius: 24px; position: relative; box-shadow: 0 25px 60px rgba(0,0,0,0.7);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <div>
                        <h3 class="kanit-bold" style="font-size: 1.25rem; color: #ffffff; margin: 0;">SubFynn — Launch Intro Video</h3>
                        <p class="kanit-light" style="font-size: 0.85rem; color: var(--text-muted); margin: 0;">ความยาว 3.5 วินาที • Animated by HyperFrames • Kanit Typography</p>
                    </div>
                    <button onclick="closeIntroModal()" class="btn btn-secondary btn-sm kanit-medium" style="border-radius: 50%; width: 36px; height: 36px; padding: 0; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; cursor: pointer;">✕</button>
                </div>
                <div style="border-radius: 16px; overflow: hidden; background: #000; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                    <video id="introVideoPlayer" controls playsinline style="width: 100%; display: block; max-height: 480px;">
                        <source src="/assets/subfynn_intro.mp4" type="video/mp4">
                    </video>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; flex-wrap: wrap; gap: 10px;">
                    <div class="kanit-light-italic" style="font-size: 0.85rem; color: var(--accent-cyan);">วิดีโอเปิดตัวพร้อมเสียงและแอนิเมชัน 3D Glassmorphism</div>
                    <div style="display: flex; gap: 8px;">
                        <a href="/assets/subfynn_intro.mp4" download="subfynn_intro.mp4" class="btn btn-secondary btn-sm kanit-medium" style="text-decoration: none;">ดาวน์โหลด MP4</a>
                        <button onclick="const p=document.getElementById('introVideoPlayer'); if(p){p.currentTime=0; p.play();}" class="btn btn-emerald btn-sm kanit-medium">เล่นซ้ำ</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentFile = null;
        let currentTaskId = null;
        let currentSegments = [];
        let activeRowId = null;

        // Drag & Drop
        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('dragover');
            });
        });
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
            });
        });
        dropZone.addEventListener('drop', (e) => {
            if (e.dataTransfer.files.length) {
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        function handleFileSelect(file) {
            if (!file) return;
            currentFile = file;
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            document.getElementById('fileInfo').innerText = `เลือกแล้ว: ${file.name} (${sizeMB} MB)`;
            document.getElementById('startBtn').disabled = false;
        }

        function startProcessing() {
            if (!currentFile) return;

            const startBtn = document.getElementById('startBtn');
            const progressBox = document.getElementById('progressBox');
            const progressBar = document.getElementById('progressBar');
            const progressStatus = document.getElementById('progressStatus');

            startBtn.disabled = true;
            progressBox.style.display = 'block';
            progressBar.style.width = '0%';
            progressStatus.innerText = 'กำลังอัปโหลดวิดีโอ (0%)...';

            // Upload via XMLHttpRequest to report smooth, real-time upload progress
            const xhr = new XMLHttpRequest();
            const uploadUrl = `/api/upload?filename=${encodeURIComponent(currentFile.name)}`;
            xhr.open('POST', uploadUrl, true);
            xhr.setRequestHeader('Content-Type', 'application/octet-stream');

            xhr.upload.onprogress = (e) => {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = `${Math.min(99, pct)}%`;
                    progressStatus.innerText = `กำลังอัปโหลดวิดีโอ (${pct}%)...`;
                }
            };

            xhr.onload = async () => {
                if (xhr.status === 200) {
                    try {
                        const uploadData = JSON.parse(xhr.responseText);
                        if (!uploadData.success) throw new Error(uploadData.error || 'Upload failed');
                        currentTaskId = uploadData.task_id;
                        progressStatus.innerText = 'อัปโหลดสำเร็จ กำลังเริ่มต้นขั้นตอนถอดเสียง...';

                        // Trigger processing
                        await fetch('/api/process', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                task_id: currentTaskId,
                                model_size: document.getElementById('modelSelect').value,
                                source_lang: document.getElementById('langSelect').value,
                                translation_style: document.getElementById('styleSelect').value,
                                gemini_model: document.getElementById('geminiModelSelect').value,
                                gemini_api_key: document.getElementById('geminiKey').value.trim(),
                                embed_mode: document.getElementById('embedModeSelect') ? document.getElementById('embedModeSelect').value : 'burn'
                            })
                        });

                        pollProgress(currentTaskId);
                    } catch (err) {
                        alert('เกิดข้อผิดพลาด: ' + err.message);
                        startBtn.disabled = false;
                        progressBox.style.display = 'none';
                    }
                } else {
                    alert('การอัปโหลดล้มเหลว HTTP ' + xhr.status);
                    startBtn.disabled = false;
                    progressBox.style.display = 'none';
                }
            };

            xhr.onerror = () => {
                alert('การเชื่อมต่อล้มเหลวระหว่างอัปโหลด');
                startBtn.disabled = false;
                progressBox.style.display = 'none';
            };

            xhr.send(currentFile);
        }

        function pollProgress(taskId) {
            const progressBar = document.getElementById('progressBar');
            const progressStatus = document.getElementById('progressStatus');

            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/progress?task_id=${taskId}`);
                    const data = await res.json();

                    progressBar.style.width = `${data.progress || 0}%`;
                    progressStatus.innerText = data.status_message || 'กำลังประมวลผล...';

                    if (data.state === 'completed') {
                        clearInterval(interval);
                        displayResults(data.result);
                    } else if (data.state === 'failed') {
                        clearInterval(interval);
                        alert('ล้มเหลว: ' + (data.error || data.status_message));
                        document.getElementById('startBtn').disabled = false;
                    }
                } catch (e) {
                    console.error(e);
                }
            }, 1000);
        }

        function displayResults(result) {
            document.getElementById('progressBox').style.display = 'none';
            document.getElementById('startBtn').disabled = false;
            document.getElementById('resultCard').style.display = 'block';

            const dlVideoBtn = document.getElementById('downloadVideoBtn');
            if (dlVideoBtn) {
                dlVideoBtn.href = `/api/download_video?task_id=${currentTaskId}`;
            }

            currentSegments = result.segments || [];
            document.getElementById('subCount').innerText = `${currentSegments.length} ท่อน`;

            // Setup video player
            const video = document.getElementById('videoPlayer');
            video.src = `/media/${currentTaskId}`;

            // Attach / reload WebVTT subtitle track
            reloadSubTrack();

            // Wire up real-time subtitle row highlighting on playback
            video.removeEventListener('timeupdate', onVideoTimeUpdate);
            video.addEventListener('timeupdate', onVideoTimeUpdate);

            // Render subtitle table
            renderSubtitleEditor();

            // Scroll to preview
            document.getElementById('resultCard').scrollIntoView({ behavior: 'smooth' });
        }

        function reloadSubTrack() {
            const video = document.getElementById('videoPlayer');
            const oldTrack = document.getElementById('subTrack');
            if (oldTrack) oldTrack.remove();

            const newTrack = document.createElement('track');
            newTrack.id = 'subTrack';
            newTrack.label = 'Thai';
            newTrack.kind = 'subtitles';
            newTrack.srclang = 'th';
            newTrack.default = true;
            newTrack.src = `/api/download_vtt?task_id=${currentTaskId}&t=${Date.now()}`;
            video.appendChild(newTrack);

            setTimeout(() => {
                if (newTrack.track) {
                    newTrack.track.mode = 'showing';
                }
            }, 100);
        }

        function onVideoTimeUpdate() {
            const video = document.getElementById('videoPlayer');
            const curTime = video.currentTime;

            const activeSeg = currentSegments.find(s => curTime >= s.start && curTime <= s.end);
            const activeId = activeSeg ? `sub-row-${activeSeg.id}` : null;

            if (activeId !== activeRowId) {
                if (activeRowId) {
                    const prevRow = document.getElementById(activeRowId);
                    if (prevRow) prevRow.classList.remove('active');
                }
                if (activeId) {
                    const curRow = document.getElementById(activeId);
                    if (curRow) {
                        curRow.classList.add('active');
                        // Auto scroll container smoothly if user is not actively typing in an input
                        if (document.activeElement.tagName !== 'INPUT') {
                            curRow.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                        }
                    }
                }
                activeRowId = activeId;
            }
        }

        function renderSubtitleEditor() {
            const container = document.getElementById('subEditor');
            container.innerHTML = '';

            if (currentSegments.length === 0) {
                container.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-muted);">ไม่มีรายการคำบรรยาย (วิดีโออาจไม่มีเสียงพูด)</div>';
                return;
            }

            currentSegments.forEach((seg, index) => {
                const row = document.createElement('div');
                row.className = 'sub-row';
                row.id = `sub-row-${seg.id}`;
                row.onclick = (e) => {
                    if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON') {
                        const video = document.getElementById('videoPlayer');
                        video.currentTime = seg.start;
                        video.play();
                    }
                };

                row.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="sub-time">#${seg.id} [${seg.start_str} ➔ ${seg.end_str}]</span>
                        <button class="btn btn-sm btn-danger" style="padding: 2px 8px; font-size: 0.75rem;" onclick="deleteSegment(${index})" title="ลบท่อนนี้">ลบ</button>
                    </div>
                    <div class="sub-text-orig">${escapeHtml(seg.original_text)}</div>
                    <input type="text" class="sub-text-thai" value="${escapeHtml(seg.thai_text || seg.text)}" onchange="updateSegmentText(${index}, this.value)">
                `;
                container.appendChild(row);
            });
        }

        function updateSegmentText(index, newText) {
            if (currentSegments[index]) {
                currentSegments[index].thai_text = newText;
                currentSegments[index].text = newText;
                // Sync back to server
                fetch('/api/save_subtitles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_id: currentTaskId,
                        segments: currentSegments
                    })
                }).then(() => {
                    reloadSubTrack();
                });
            }
        }

        function deleteSegment(index) {
            if (confirm('ต้องการลบท่อนซับไตเติลนี้หรือไม่?')) {
                currentSegments.splice(index, 1);
                // Re-index
                currentSegments.forEach((s, idx) => s.id = idx + 1);
                document.getElementById('subCount').innerText = `${currentSegments.length} ท่อน`;
                renderSubtitleEditor();

                fetch('/api/save_subtitles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_id: currentTaskId,
                        segments: currentSegments
                    })
                }).then(() => {
                    reloadSubTrack();
                });
            }
        }

        async function shiftSubtitles(seconds) {
            if (!currentTaskId || currentSegments.length === 0) return;
            try {
                const res = await fetch('/api/shift_subtitles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        task_id: currentTaskId,
                        offset_seconds: seconds
                    })
                });
                const data = await res.json();
                if (data.success && data.segments) {
                    currentSegments = data.segments;
                    renderSubtitleEditor();
                    reloadSubTrack();
                } else {
                    alert('ไม่สามารถปรับเวลาได้: ' + (data.error || ''));
                }
            } catch (e) {
                alert('เกิดข้อผิดพลาดในการปรับเวลา: ' + e.message);
            }
        }

        function promptCustomShift() {
            const val = prompt('กรอกจำนวนวินาทีที่ต้องการเลื่อน (เช่น +0.8 หรือ -1.2):', '0.5');
            if (val !== null) {
                const sec = parseFloat(val);
                if (!isNaN(sec) && sec !== 0) {
                    shiftSubtitles(sec);
                }
            }
        }

        function downloadSRT() {
            if (!currentTaskId) return;
            window.open(`/api/download_srt?task_id=${currentTaskId}`, '_blank');
        }

        function downloadVTT() {
            if (!currentTaskId) return;
            window.open(`/api/download_vtt?task_id=${currentTaskId}`, '_blank');
        }

        async function burnSubtitles() {
            if (!currentTaskId) return;
            const burnBtn = document.getElementById('burnBtn');
            const box = document.getElementById('burnProgressBox');
            const status = document.getElementById('burnStatus');

            burnBtn.disabled = true;
            box.style.display = 'block';
            status.innerText = 'กำลังประมวลผลการฝังซับลงวิดีโอ (อาจใช้เวลาสักครู่)...';

            try {
                const res = await fetch('/api/burn_subtitles', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task_id: currentTaskId, font_size: 18 })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error);

                // Poll burn progress
                const pollBurn = setInterval(async () => {
                    const bRes = await fetch(`/api/progress?task_id=${data.burn_id}`);
                    const bData = await bRes.json();
                    status.innerText = bData.status_message;

                    if (bData.state === 'completed') {
                        clearInterval(pollBurn);
                        burnBtn.disabled = false;
                        status.innerText = 'สำเร็จ! กำลังเริ่มดาวน์โหลดวิดีโอ...';
                        window.location.href = `/api/download_video?task_id=${currentTaskId}`;
                    } else if (bData.state === 'failed') {
                        clearInterval(pollBurn);
                        burnBtn.disabled = false;
                        alert('ฝังซับล้มเหลว: ' + bData.error);
                    }
                }, 1500);

            } catch (e) {
                alert('เกิดข้อผิดพลาด: ' + e.message);
                burnBtn.disabled = false;
                box.style.display = 'none';
            }
        }

        function openIntroModal() {
            const modal = document.getElementById('introModal');
            const p = document.getElementById('introVideoPlayer');
            if (modal) {
                modal.style.display = 'flex';
                if (p) {
                    p.currentTime = 0;
                    p.play().catch(() => {});
                }
            }
        }

        function closeIntroModal() {
            const modal = document.getElementById('introModal');
            const p = document.getElementById('introVideoPlayer');
            if (p) {
                p.pause();
            }
            if (modal) {
                modal.style.display = 'none';
            }
        }

        function playIntroVideo() {
            openIntroModal();
        }

        function copyAllText() {
            const allText = currentSegments.map(s => s.thai_text || s.text).join('\\n');
            navigator.clipboard.writeText(allText).then(() => {
                alert('คัดลอกข้อความซับไทยทั้งหมดแล้ว!');
            });
        }

        function escapeHtml(text) {
            return (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }
    </script>
</body>
</html>
"""


class AppRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Clean console logging
        pass

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def get_request_path(self):
        """
        Extract the logical request path and query parameters, correctly resolving
        Vercel edge rewrites and proxy headers (x-vercel-matched-path, x-matched-path,
        x-forwarded-uri, x-original-url).
        """
        forwarded = (
            self.headers.get("x-vercel-matched-path")
            or self.headers.get("x-matched-path")
            or self.headers.get("x-forwarded-uri")
            or self.headers.get("x-original-url")
        )
        target = forwarded if forwarded else self.path
        parsed = urlparse(target)
        path = parsed.path

        # If running under a Vercel rewrite where the destination is /api/index.py
        if path in ("/api/index.py", "/api/index"):
            path = "/api/status"

        query = parse_qs(parsed.query) if parsed.query else parse_qs(urlparse(self.path).query)
        return path, query

    def do_GET(self):
        path, query = self.get_request_path()

        if path in ("/api", "/api/", "/api/status", "/api/health", "/api/info"):
            self.send_json(
                {
                    "status": "online",
                    "app": "SubFynn Studio — AI Thai Subtitle Generator",
                    "version": "1.0.0",
                    "font": "Kanit",
                    "typography": {
                        "primary": "Kanit, sans-serif",
                        "weights": [100, 200, 300, 400, 500, 600, 700, 800, 900],
                        "styles": ["normal", "italic"],
                    },
                    "features": [
                        "whisper_speech_to_text",
                        "gemini_translation",
                        "jav_slang_engine",
                        "liquid_glassmorphism",
                        "hyperframes_intro_video",
                    ],
                    "intro_video": "/assets/subfynn_intro.mp4",
                }
            )
            return

        if path == "/" or path == "/index.html":
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path in ("/subfynn_intro.mp4", "/assets/subfynn_intro.mp4"):
            intro_path = os.path.join(BASE_DIR, "assets", "subfynn_intro.mp4")
            if not os.path.isfile(intro_path):
                intro_path = os.path.join(BASE_DIR, "subfynn_intro.mp4")
            if os.path.isfile(intro_path):
                self.serve_file_with_range(intro_path, "video/mp4")
                return
            self.send_error(404, "Intro video not found")
            return

        if path.startswith("/media/"):
            task_id = path.split("/media/")[1].split("?")[0]
            with tasks_lock:
                task = tasks.get(task_id)
            if not task or not os.path.isfile(task.get("video_path", "")):
                self.send_error(404, "Video not found")
                return
            self.serve_file_with_range(task["video_path"], "video/mp4")
            return

        if path == "/api/progress":
            task_id = query.get("task_id", [""])[0]
            with tasks_lock:
                task = tasks.get(task_id)
            if not task:
                self.send_json({"error": "Task not found"}, 404)
                return
            self.send_json(task)
            return

        if path == "/api/download_srt":
            task_id = query.get("task_id", [""])[0]
            with tasks_lock:
                task = tasks.get(task_id)
            if not task or "result" not in task:
                self.send_error(404, "Subtitle not found")
                return
            srt_path = task["result"]["srt_path"]
            if not os.path.isfile(srt_path):
                self.send_error(404, "SRT file missing")
                return
            with open(srt_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-subrip; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="subtitles_th.srt"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/download_vtt":
            task_id = query.get("task_id", [""])[0]
            with tasks_lock:
                task = tasks.get(task_id)
            if not task or "result" not in task:
                self.send_error(404, "Subtitle not found")
                return
            vtt_path = task["result"]["vtt_path"]
            if not os.path.isfile(vtt_path):
                self.send_error(404, "VTT file missing")
                return
            with open(vtt_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/vtt; charset=utf-8")
            self.send_header("Content-Disposition", f'inline; filename="subtitles_th.vtt"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/download_video":
            task_id = query.get("task_id", [""])[0]
            out_video = os.path.join(OUTPUT_DIR, task_id, "video_with_th_subtitles.mp4")
            if not os.path.isfile(out_video):
                self.send_error(404, "Burned video not found")
                return
            self.serve_file_with_range(out_video, "video/mp4", as_attachment=True)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        path, query = self.get_request_path()

        if path == "/api/upload":
            raw_filename = query.get("filename", ["video.mp4"])[0]
            safe_filename = os.path.basename(raw_filename).replace(" ", "_")
            if not safe_filename:
                safe_filename = "video.mp4"
            task_id = str(uuid.uuid4())[:8]

            task_dir = os.path.join(UPLOAD_DIR, task_id)
            os.makedirs(task_dir, exist_ok=True)
            saved_path = os.path.join(task_dir, safe_filename)

            content_length = int(self.headers.get("Content-Length", 0))
            remaining = content_length
            with open(saved_path, "wb") as f:
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            with tasks_lock:
                tasks[task_id] = {
                    "task_id": task_id,
                    "video_path": saved_path,
                    "filename": safe_filename,
                    "state": "uploaded",
                    "progress": 0.0,
                    "status_message": "อัปโหลดเสร็จสมบูรณ์",
                }
            self.send_json({"success": True, "task_id": task_id, "filename": safe_filename})
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_data = json.loads(body)
        except Exception:
            req_data = {}

        if path == "/api/process":
            task_id = req_data.get("task_id")
            with tasks_lock:
                task_exists = task_id in tasks if task_id else False
            if not task_id or not task_exists:
                self.send_json({"success": False, "error": "Invalid task_id"}, 400)
                return

            with tasks_lock:
                tasks[task_id]["state"] = "processing"
                tasks[task_id]["progress"] = 5.0
                tasks[task_id]["status_message"] = "กำลังเริ่มขั้นตอนสร้างซับ..."
                video_path = tasks[task_id]["video_path"]

            t = threading.Thread(
                target=run_process_task,
                args=(
                    task_id,
                    video_path,
                    req_data.get("model_size", "base"),
                    req_data.get("source_lang", "auto"),
                    req_data.get("gemini_api_key", ""),
                    req_data.get("translation_style", "jav"),
                    req_data.get("gemini_model", "gemini-2.5-flash"),
                    req_data.get("embed_mode", "burn"),
                ),
                daemon=True,
            )
            t.start()
            self.send_json({"success": True, "task_id": task_id})
            return

        if path == "/api/save_subtitles":
            task_id = req_data.get("task_id")
            segments = req_data.get("segments", [])
            with tasks_lock:
                task = tasks.get(task_id)
            if not task or "result" not in task:
                self.send_json({"success": False, "error": "Task not found"}, 404)
                return

            srt_content = generate_srt(segments)
            vtt_content = generate_vtt(segments)
            with open(task["result"]["srt_path"], "w", encoding="utf-8") as f:
                f.write(srt_content)
            with open(task["result"]["vtt_path"], "w", encoding="utf-8") as f:
                f.write(vtt_content)

            with tasks_lock:
                task["result"]["segments"] = segments
                task["result"]["srt_content"] = srt_content
                task["result"]["vtt_content"] = vtt_content
            self.send_json({"success": True})
            return

        if path == "/api/shift_subtitles":
            task_id = req_data.get("task_id")
            offset_seconds = float(req_data.get("offset_seconds", 0.0))
            with tasks_lock:
                task = tasks.get(task_id)
            if not task or "result" not in task:
                self.send_json({"success": False, "error": "Task not found"}, 404)
                return

            segments = task["result"].get("segments", [])
            shifted = shift_subtitle_segments(segments, offset_seconds)
            srt_content = generate_srt(shifted)
            vtt_content = generate_vtt(shifted)

            with open(task["result"]["srt_path"], "w", encoding="utf-8") as f:
                f.write(srt_content)
            with open(task["result"]["vtt_path"], "w", encoding="utf-8") as f:
                f.write(vtt_content)

            with tasks_lock:
                task["result"]["segments"] = shifted
                task["result"]["srt_content"] = srt_content
                task["result"]["vtt_content"] = vtt_content
            self.send_json({"success": True, "segments": shifted})
            return

        if path == "/api/burn_subtitles":
            task_id = req_data.get("task_id")
            font_size = int(req_data.get("font_size", 18))
            with tasks_lock:
                task_exists = task_id in tasks if task_id else False
            if not task_id or not task_exists:
                self.send_json({"success": False, "error": "Invalid task_id"}, 400)
                return

            burn_id = f"burn_{str(uuid.uuid4())[:8]}"
            with tasks_lock:
                tasks[burn_id] = {
                    "burn_id": burn_id,
                    "task_id": task_id,
                    "state": "pending",
                    "progress": 0.0,
                    "status_message": "กำลังเตรียมการฝังซับ...",
                }

            t = threading.Thread(
                target=run_burn_task,
                args=(burn_id, task_id, font_size),
                daemon=True,
            )
            t.start()
            self.send_json({"success": True, "burn_id": burn_id})
            return

        self.send_error(404, "Not Found")

    def serve_file_with_range(self, file_path: str, mime_type: str, as_attachment: bool = False):
        """
        Serve file supporting RFC 7233 HTTP 206 Partial Content Range requests (including suffix byte ranges)
        for smooth video seeking and player compatibility.
        """
        file_size = os.path.getsize(file_path)
        range_header = self.headers.get("Range")

        start = 0
        end = file_size - 1

        if range_header and range_header.startswith("bytes="):
            spec = range_header[6:].strip()
            if spec.startswith("-"):
                # Suffix byte range: bytes=-500 (requesting last 500 bytes)
                suffix_len = int(spec[1:])
                start = max(0, file_size - suffix_len)
                end = file_size - 1
            elif "-" in spec:
                parts = spec.split("-")
                if parts[0]:
                    start = int(parts[0])
                if len(parts) > 1 and parts[1]:
                    end = int(parts[1])

        if start >= file_size or start > end:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{file_size}")
            self.end_headers()
            return

        length = end - start + 1
        if range_header:
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        else:
            self.send_response(200)

        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        if as_attachment:
            filename = os.path.basename(file_path)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()

        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                bytes_left = length
                while bytes_left > 0:
                    chunk = f.read(min(bytes_left, 65536))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    bytes_left -= len(chunk)
        except (ConnectionResetError, BrokenPipeError):
            pass


from io import BytesIO


class WSGIApp:
    """
    WSGI Application adapter that routes WSGI requests to AppRequestHandler.
    Enables SubFynn to run seamlessly on Vercel Serverless Functions, AWS Lambda,
    Gunicorn, uWSGI, and standard WSGI servers.
    """
    def __init__(self, handler_class=None):
        self.handler_class = handler_class or AppRequestHandler

    def __call__(self, environ: Dict[str, Any], start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = environ.get("PATH_INFO", "/")
        query = environ.get("QUERY_STRING", "")
        if query:
            path += "?" + query

        content_length_str = environ.get("CONTENT_LENGTH")
        try:
            content_length = int(content_length_str) if content_length_str else 0
        except ValueError:
            content_length = 0

        body = b""
        if content_length > 0 and "wsgi.input" in environ:
            try:
                body = environ["wsgi.input"].read(content_length)
            except Exception:
                body = b""

        raw_headers = [f"{method} {path} HTTP/1.1\r\n".encode("latin-1")]
        host = environ.get("HTTP_HOST", "localhost")
        raw_headers.append(f"Host: {host}\r\n".encode("latin-1"))

        if content_length > 0:
            raw_headers.append(f"Content-Length: {content_length}\r\n".encode("latin-1"))

        content_type = environ.get("CONTENT_TYPE")
        if content_type:
            raw_headers.append(f"Content-Type: {content_type}\r\n".encode("latin-1"))

        for k, v in environ.items():
            if k.startswith("HTTP_"):
                header_name = k[5:].replace("_", "-")
                raw_headers.append(f"{header_name}: {v}\r\n".encode("latin-1"))
            elif k.lower() in ("x_vercel_matched_path", "x_matched_path", "x_forwarded_uri"):
                header_name = k.replace("_", "-")
                raw_headers.append(f"{header_name}: {v}\r\n".encode("latin-1"))

        raw_headers.append(b"\r\n")
        raw_req = b"".join(raw_headers) + body

        rfile = BytesIO(raw_req)
        wfile = BytesIO()

        class _Wsock:
            def makefile(self, mode, *args, **kwargs):
                if "r" in mode:
                    return rfile
                return wfile

            def sendall(self, b):
                wfile.write(b)

        class _Wserver:
            pass

        try:
            handler_instance = self.handler_class(_Wsock(), ("127.0.0.1", 80), _Wserver())
        except Exception as e:
            err_body = json.dumps({"error": str(e), "status": "error"}).encode("utf-8")
            start_response("500 Internal Server Error", [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(err_body))),
            ])
            return [err_body]

        output = wfile.getvalue()
        if b"\r\n\r\n" in output:
            header_data, resp_body = output.split(b"\r\n\r\n", 1)
        else:
            header_data = output
            resp_body = b""

        lines = header_data.decode("iso-8859-1", errors="replace").split("\r\n")
        status_line = lines[0] if lines else "HTTP/1.1 200 OK"
        status = status_line.split(" ", 1)[1] if " " in status_line else "200 OK"

        response_headers = []
        for line in lines[1:]:
            if ":" in line:
                name, val = line.split(":", 1)
                response_headers.append((name.strip(), val.strip()))

        start_response(status, response_headers)
        return [resp_body]


# Global WSGI application instance
wsgi_application = WSGIApp(AppRequestHandler)

# Top-level exports for Vercel Serverless Function and WSGI runtime discovery
class handler(AppRequestHandler):
    """Vercel BaseHTTPRequestHandler entrypoint."""
    pass


app = wsgi_application
application = wsgi_application


_global_web_server = None
_global_web_thread = None
_global_web_port = 5000


def find_available_port(start_port: int = 5000, max_attempts: int = 20) -> int:
    """
    Find an available local port starting from start_port up to start_port + max_attempts.
    """
    import socket
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return start_port


def start_server_in_background(port: int = 5000, max_attempts: int = 20) -> int:
    """
    Start the web app server in a background daemon thread on an available port.
    Returns the port number the server is listening on.
    """
    global _global_web_server, _global_web_thread, _global_web_port
    if _global_web_server is not None:
        return _global_web_port

    actual_port = find_available_port(port, max_attempts)
    _global_web_server = HTTPServer(("127.0.0.1", actual_port), AppRequestHandler)
    _global_web_port = actual_port
    _global_web_thread = threading.Thread(target=_global_web_server.serve_forever, daemon=True)
    _global_web_thread.start()
    return actual_port


def start_server(port: int = 5000, open_browser: bool = True, max_attempts: int = 20):
    actual_port = find_available_port(port, max_attempts)
    server = HTTPServer(("127.0.0.1", actual_port), AppRequestHandler)
    url = f"http://127.0.0.1:{actual_port}"
    print(f"==================================================")
    print(f"   AI Thai Subtitle Generator (Web App)")
    print(f"   เปิดใช้งานที่: {url}")
    print(f"==================================================")

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nหยุดการทำงานเรียบร้อย")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 5000
    start_server(port=port, open_browser=True)
