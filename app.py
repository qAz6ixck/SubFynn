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
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
            --bg-deep: #09121f;
            --glass-surface: rgba(20, 32, 50, 0.82);
            --glass-surface-hover: rgba(26, 40, 60, 0.90);
            --glass-surface-active: rgba(32, 48, 70, 0.94);
            --glass-border: rgba(195, 213, 235, 0.20);
            --glass-border-hover: rgba(195, 213, 235, 0.36);
            --glass-highlight: rgba(255, 255, 255, 0.24);
            --accent-indigo: #7896ff;
            --accent-pink: #bb9bff;
            --accent-cyan: #65d4e8;
            --accent-emerald: #4ed2a0;
            --text-heading: #f7f9fd;
            --text-primary: #f1f5fb;
            --text-body: #e0e8f3;
            --text-secondary: #bdcadd;
            --text-muted: #aebbd0;
            --radius-card: 24px;
            --radius-input: 14px;
            --radius-pill: 9999px;
            --glass-shadow: 0 20px 48px rgba(2, 8, 18, 0.34), inset 0 1px 0 rgba(255, 255, 255, 0.14);
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
                radial-gradient(at 0% 0%, rgba(64, 91, 145, 0.34) 0px, transparent 55%),
                radial-gradient(at 100% 0%, rgba(39, 116, 139, 0.24) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(60, 80, 122, 0.18) 0px, transparent 60%),
                radial-gradient(at 0% 100%, rgba(15, 31, 50, 0.7) 0px, transparent 55%),
                radial-gradient(at 100% 100%, rgba(35, 66, 88, 0.28) 0px, transparent 55%);
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
            opacity: 0.30;
            animation: floatOrb 18s ease-in-out infinite alternate;
        }

        .orb-1 {
            width: 540px;
            height: 540px;
            background: radial-gradient(circle, rgba(111, 151, 225, 0.55), transparent 70%);
            top: -100px;
            left: -100px;
        }

        .orb-2 {
            width: 480px;
            height: 480px;
            background: radial-gradient(circle, rgba(76, 168, 177, 0.44), transparent 70%);
            bottom: -100px;
            right: -80px;
            animation-delay: -6s;
        }

        .orb-3 {
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(114, 139, 196, 0.34), transparent 70%);
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

        /* 4. Glass Navigation Bar */
        .glass-navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 18px 30px;
            flex-wrap: wrap;
            gap: 16px;
        }

        .brand-group {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .brand-logo {
            width: 46px;
            height: 46px;
            border-radius: 14px;
            background: linear-gradient(135deg, #5274c4, #398fa7);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.3rem;
            color: #ffffff;
            box-shadow: 0 8px 24px rgba(78, 126, 180, 0.28);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }

        .brand-title {
            font-size: 1.45rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            background: linear-gradient(to right, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-subtitle {
            font-size: 0.85rem;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .nav-status-group {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
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

        .edition-badge {
            padding: 6px 16px;
            border-radius: var(--radius-pill);
            font-size: 0.82rem;
            font-weight: 600;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.35);
            box-shadow: 0 2px 10px rgba(56, 189, 248, 0.2);
        }

        /* 5. Dropzone Glass */
        .dropzone-glass {
            border: 2px dashed rgba(255, 255, 255, 0.25);
            border-radius: 20px;
            padding: 42px 24px;
            text-align: center;
            background: rgba(15, 23, 42, 0.40);
            cursor: pointer;
            transition: all 0.25s ease;
        }

        .dropzone-glass:hover, .dropzone-glass.dragover {
            border-color: var(--accent-cyan);
            background: rgba(6, 182, 212, 0.08);
            transform: translateY(-2px);
            box-shadow: 0 0 30px rgba(6, 182, 212, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.2);
        }

        .upload-icon {
            font-size: 46px;
            margin-bottom: 12px;
            display: inline-block;
            filter: drop-shadow(0 4px 12px rgba(99, 102, 241, 0.4));
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

        /* 6. Form Controls & Grid */
        .options-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-top: 24px;
        }

        .option-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        label {
            font-size: 0.96rem;
            font-weight: 600;
            color: var(--text-secondary);
        }

        select, input[type="text"], input[type="password"] {
            width: 100%;
            background: rgba(15, 23, 42, 0.65);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: var(--radius-input);
            padding: 13px 16px;
            color: var(--text-heading);
            font-size: 1rem;
            line-height: 1.5;
            outline: none;
            transition: all 0.2s ease;
            box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.4);
        }

        select:focus, input:focus {
            border-color: var(--accent-indigo);
            background: rgba(15, 23, 42, 0.85);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.3), 0 0 18px rgba(99, 102, 241, 0.25);
        }

        select option {
            background-color: #0f172a;
            color: #ffffff;
            padding: 8px;
        }

        /* 7. JAV 18+ Special Glass Banner */
        .banner-jav-glass {
            background: rgba(244, 63, 94, 0.12);
            border: 1px solid rgba(244, 63, 94, 0.32);
            border-radius: 18px;
            padding: 16px 22px;
            margin-top: 22px;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 8px 24px rgba(244, 63, 94, 0.15);
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
            background: linear-gradient(135deg, #5578c8, #397e9d);
            border: 1px solid rgba(255, 255, 255, 0.35);
            border-radius: 16px;
            padding: 15px 36px;
            color: #ffffff;
            font-weight: 700;
            font-size: 1.05rem;
            cursor: pointer;
            box-shadow: 0 10px 24px -6px rgba(47, 103, 153, 0.42);
            transition: all 0.25s ease;
        }

        .btn-glass-primary:hover:not(:disabled) {
            transform: translateY(-2px) scale(1.01);
            box-shadow: 0 14px 30px -6px rgba(47, 103, 153, 0.52);
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
            background: linear-gradient(135deg, #536ca8, #647bb4);
            color: #ffffff;
            border: 1px solid rgba(177, 196, 226, 0.36);
            box-shadow: 0 8px 20px rgba(48, 72, 114, 0.32);
        }

        .btn-violet:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 12px 26px rgba(48, 72, 114, 0.44);
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
            background: rgba(15, 23, 42, 0.7);
            border-radius: var(--radius-pill);
            height: 12px;
            overflow: hidden;
            margin-bottom: 10px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.6);
        }

        .progress-bar-fill {
            background: linear-gradient(90deg, #6686d4, var(--accent-cyan));
            box-shadow: 0 0 16px rgba(101, 172, 196, 0.42);
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
            background: rgba(10, 15, 28, 0.75);
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
            background: rgba(99, 102, 241, 0.18) !important;
            border-color: rgba(99, 102, 241, 0.5) !important;
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
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 8px 12px;
        }

        .sub-text-thai:focus {
            background: rgba(15, 23, 42, 0.9);
            border-color: var(--accent-indigo);
            outline: none;
            box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.25);
        }

        .actions-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 24px;
        }

        :focus-visible {
            outline: 3px solid rgba(101, 212, 232, 0.9);
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
            .glass-navbar { padding: 18px 20px; }
            .brand-title { font-size: 1.25rem; }
            .brand-subtitle { font-size: 0.82rem; }
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
        <!-- 2. Glass Navigation Header -->
        <header class="glass-panel glass-navbar">
            <div class="brand-group">
                <div class="brand-logo">SF</div>
                <div>
                    <div class="brand-title">SubFynn Studio</div>
                    <div class="brand-subtitle">โปรแกรมสร้างซับไทยอัตโนมัติ (AI Thai Subtitle Generator)</div>
                </div>
            </div>
            <div class="nav-status-group">
                <button class="status-pill kanit-medium" onclick="playIntroVideo()" style="background: rgba(120, 150, 255, 0.22); border: 1px solid rgba(120, 150, 255, 0.45); color: #ffffff; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s ease;">🎬 ดูวิดีโอเปิดตัว (Intro)</button>
                <span class="status-pill">● Engine Ready</span>
                <span class="edition-badge">💎 Liquid Glass Edition</span>
            </div>
        </header>

        <!-- 3. Upload & Configuration Glass Panel -->
        <main class="glass-panel">
            <div class="dropzone-glass" id="dropZone" onclick="document.getElementById('videoFile').click()">
                <span class="upload-icon">🎬</span>
                <h3>ลากไฟล์วิดีโอมาวางที่นี่ หรือคลิกเพื่อเลือกไฟล์</h3>
                <p style="color: var(--text-muted); font-size: 0.88rem; margin-top: 4px;">รองรับ MP4, MKV, MOV, AVI, WEBM, FLV, TS (สูงสุด 2GB)</p>
                <div class="file-info" id="fileInfo"></div>
                <input type="file" id="videoFile" accept="video/*,audio/*" style="display: none;" onchange="handleFileSelect(this.files[0])">
            </div>

            <div class="options-grid">
                <div class="option-group">
                    <label for="modelSelect">ขนาดโมเดล Whisper (AI Speech-to-Text)</label>
                    <select id="modelSelect">
                        <option value="base" selected>Base (แนะนำทั่วไป - รวดเร็ว สมดุล)</option>
                        <option value="tiny">Tiny (เร็วที่สุด ใช้ทรัพยากรน้อย)</option>
                        <option value="small">Small (แม่นยำปานกลาง)</option>
                        <option value="medium">Medium (แม่นยำสูง แนะนำสำหรับ JAV/ญี่ปุ่น)</option>
                        <option value="large-v3">Large-v3 (แม่นยำสูงสุด ถอดเสียงคราง/กระซิบชัด)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="styleSelect">สไตล์การแปลคำบรรยาย (Translation Style)</label>
                    <select id="styleSelect">
                        <option value="jav" selected>🔥 หนังผู้ใหญ่ / JAV 18+ (มาตรฐานแฟนซับ: เร่าร้อน เสียว เป็นธรรมชาติ)</option>
                        <option value="jav_dirty">💥 หนังผู้ใหญ่ / JAV 18+ (สายดุดัน / หยาบคายได้เต็มที่: ควย หี เย็ด ซอยยับ แตกใน โคตรเสียว ไม่เซ็นเซอร์)</option>
                        <option value="jav_hardcore">🔞 หนังผู้ใหญ่ / JAV 18+ (Hardcore ดิบเถื่อน หยาบคายขั้นสุด)</option>
                        <option value="jav_sweet">💖 หนังผู้ใหญ่ / JAV 18+ (สายหวานอ้อน: เสียวจัง พี่คะ หนูไม่ไหวแล้ว)</option>
                        <option value="general">🎬 ทั่วไป / ภาพยนตร์ (General / Cinematic)</option>
                        <option value="anime">🌸 อนิเมะ / การ์ตูน (Anime & Manga)</option>
                        <option value="drama">🎭 ดราม่า / ซีรีส์ (Drama & Emotional)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="geminiModelSelect">โมเดล AI แปลภาษา (Translation Model)</label>
                    <select id="geminiModelSelect">
                        <option value="gemini-2.5-flash" selected>Gemini 2.5 Flash (เร็ว ฉลาด ได้อารมณ์ - แนะนำ)</option>
                        <option value="gemini-2.5-pro">Gemini 2.5 Pro (แปลได้อารมณ์ลึกซึ้งขั้นสุด - พรีเมียม 18+)</option>
                        <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash-Lite (เร็วขั้นสุด ลื่นไหล ประหยัดโควตา)</option>
                        <option value="gemini-2.0-flash">Gemini 2.0 Flash (เสถียรและรวดเร็วสูง)</option>
                        <option value="gemini-2.0-flash-lite">Gemini 2.0 Flash-Lite (เบาและรวดเร็วสูง)</option>
                        <option value="gemini-1.5-flash">Gemini 1.5 Flash (ประหยัดโควตา เข้าถึงได้ทุกบัญชี)</option>
                        <option value="gemini-1.5-pro">Gemini 1.5 Pro (วิเคราะห์ละเอียด แม่นยำ)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="embedModeSelect">เอาซับใส่คลิปวิดีโอทันที (Auto-embed Video)</label>
                    <select id="embedModeSelect">
                        <option value="burn" selected>🎬 ฝังซับติดภาพถาวร (Hardsub Burn-in - แนะนำ)</option>
                        <option value="soft">⚡ ฝังซับในไฟล์เร็ว 1 วิ (Fast Softsub - เปิด/ปิดได้ ไม่เสียความคมชัด)</option>
                        <option value="both">✨ ทำทั้ง 2 แบบ (ทั้ง Hardsub และ Softsub)</option>
                        <option value="none">📄 สร้างเฉพาะไฟล์ซับ (.SRT / .VTT)</option>
                    </select>
                </div>
                <div class="option-group">
                    <label for="langSelect">ภาษาเสียงพูดต้นฉบับในวิดีโอ (ซับไตเติลผลลัพธ์จะเป็นภาษาไทยเสมอ)</label>
                    <select id="langSelect">
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
                    <label for="geminiKey">Google Gemini API Key (ไม่บังคับ - ปลดล็อกการแปล 18+ ขั้นสุด)</label>
                    <input type="password" id="geminiKey" placeholder="วาง API Key หรือเว้นว่างเพื่อใช้ระบบแปล JAV ฟรี">
                </div>
            </div>

            <div class="banner-jav-glass">
                <span style="font-size: 1.8rem;">🔞</span>
                <div style="font-size: 0.92rem; line-height: 1.5;">
                    <strong style="color: #ffffff;">โหมดแปล JAV / หนังผู้ใหญ่ 18+ ได้อารมณ์สมจริง:</strong>
                    <span style="color: rgba(255, 255, 255, 0.85);"> ปรับสำนวนซับไทยให้อินเนอร์มาเต็ม (เสียว, จะเสร็จแล้ว, อย่านะ, มิดด้าม, ควย, หี, แตกใน) พร้อมระบบ Anti-Hallucination ตัดเสียงครางวนซ้ำ และปลดล็อกระบบกรองคำของ Gemini AI</span>
                </div>
            </div>

            <div style="margin-top: 28px; text-align: center;">
                <button class="btn btn-glass-primary" id="startBtn" onclick="startProcessing()" disabled>
                    ✨ เริ่มสร้างซับไทย (Generate Thai Subtitles)
                </button>
            </div>

            <div class="progress-box" id="progressBox">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="progressBar"></div>
                </div>
                <div class="progress-status" id="progressStatus">กำลังเตรียมการ...</div>
            </div>
        </main>

        <!-- 4. Result Preview & Subtitle Editor Glass Panel -->
        <section class="glass-panel result-section" id="resultCard">
            <h2 style="margin-bottom: 20px; font-size: 1.35rem; color: #ffffff;">🎬 ตัวอย่างวิดีโอและคำบรรยายซับไทย</h2>
            <div class="preview-layout">
                <div class="video-container">
                    <video id="videoPlayer" controls playsinline></video>
                </div>
                <div>
                    <div class="tools-panel">
                        <div class="shift-tools">
                            <span style="font-size: 0.85rem; color: var(--text-secondary);">ปรับเวลา:</span>
                            <button class="btn btn-secondary btn-sm" onclick="shiftSubtitles(-0.5)" title="เลื่อนซับเร็วขึ้น 0.5 วินาที">⏪ -0.5s</button>
                            <button class="btn btn-secondary btn-sm" onclick="shiftSubtitles(0.5)" title="เลื่อนซับช้าลง 0.5 วินาที">⏩ +0.5s</button>
                            <button class="btn btn-secondary btn-sm" onclick="promptCustomShift()">⏱️ กำหนดเอง...</button>
                        </div>
                        <div style="display: flex; gap: 6px; align-items: center;">
                            <span id="subCount" style="font-size: 0.88rem; color: #38bdf8; font-weight: 600;">0 ท่อน</span>
                        </div>
                    </div>
                    <div class="subtitles-editor" id="subEditor"></div>
                </div>
            </div>

            <div class="actions-bar">
                <a class="btn btn-emerald" id="downloadVideoBtn" href="#" style="text-decoration: none;">🎬 ดาวน์โหลดวิดีโอพร้อมซับ (Subtitled Video MP4)</a>
                <button class="btn btn-secondary" onclick="downloadSRT()">📥 ดาวน์โหลดไฟล์ .SRT</button>
                <button class="btn btn-secondary" onclick="downloadVTT()">📥 ดาวน์โหลดไฟล์ .VTT</button>
                <button class="btn btn-violet" id="burnBtn" onclick="burnSubtitles()">🎬 ฝังซับใหม่ (Custom Burn)</button>
                <button class="btn btn-secondary" onclick="copyAllText()">📋 คัดลอกข้อความทั้งหมด</button>
            </div>

            <div class="progress-box" id="burnProgressBox" style="margin-top: 18px;">
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="burnProgressBar" style="width: 100%;"></div>
                </div>
                <div class="progress-status" id="burnStatus">กำลังฝังซับไตเติล...</div>
            </div>
        </section>
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

        function playIntroVideo() {
            const resSec = document.getElementById('resultSection');
            const vp = document.getElementById('videoPlayer');
            if (resSec && vp) {
                resSec.style.display = 'block';
                vp.src = '/assets/subfynn_intro.mp4';
                vp.currentTime = 0;
                vp.play().catch(() => {});
                resSec.scrollIntoView({ behavior: 'smooth' });
            } else {
                window.open('/assets/subfynn_intro.mp4', '_blank');
            }
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

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

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
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

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
