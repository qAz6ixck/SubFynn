"""
SubFynn Python Engine Sidecar Daemon.

High-performance, long-running Line-Delimited JSON (NDJSON) daemon communicating
over standard I/O (stdin/stdout) for Tauri v2 Rust host and frontend.

Features:
- Full NDJSON RPC protocol with methods (engine.ping, engine.load_model, engine.process_video,
  engine.shift_time, engine.burn_subtitles, engine.mux_subtitles, engine.shutdown).
- Streaming real-time progress events for video processing pipeline.
- Absolute stdout isolation: all logging, warnings, and library prints redirected to stderr.
- Stdin EOF watchdog: terminates immediately via os._exit(0) on EOF or broken pipe.
"""

import os
import sys
import json
import time
import queue
import logging
import warnings
import threading
import traceback
from typing import Any, Dict, List, Optional, Tuple, Callable

# Ensure UTF-8 console encoding on Windows
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import core engine
import engine

# Protocol output stream (direct standard output channel)
_PROTOCOL_STDOUT = sys.__stdout__ or sys.stdout
_STDOUT_LOCK = threading.Lock()


def send_message(obj: Dict[str, Any], stream=None) -> None:
    """
    Serializes obj to a single NDJSON line and writes to protocol stdout with immediate flush.
    """
    target = stream or _PROTOCOL_STDOUT
    line = json.dumps(obj, ensure_ascii=False)
    with _STDOUT_LOCK:
        try:
            target.write(line + "\n")
            target.flush()
        except Exception as e:
            sys.stderr.write(f"[ERROR] Failed to write protocol message: {str(e)}\n")
            sys.stderr.flush()


def classify_stage(percent: float, message: str) -> str:
    """
    Classifies the current pipeline stage based on percentage and message text.
    """
    msg_lower = (message or "").lower()
    if "แยกเสียง" in msg_lower or "extract" in msg_lower or percent < 25.0:
        return "extracting_audio"
    if "ถอดเสียง" in msg_lower or "transcrib" in msg_lower or percent < 70.0:
        return "transcribing"
    if "แปล" in msg_lower or "translat" in msg_lower or percent < 92.0:
        return "translating"
    if "บันทึก" in msg_lower or "subtitle" in msg_lower or percent < 95.0:
        return "generating_subtitles"
    if "นำซับ" in msg_lower or "ใส่คลิป" in msg_lower or "embed" in msg_lower or "burn" in msg_lower or "mux" in msg_lower or percent < 100.0:
        return "embedding_subtitles"
    return "completed"


def rpc_ping(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    engine.ping: Returns health status, version, CUDA GPU availability, cached models, and FFmpeg path.
    """
    cuda_available = bool(engine.check_cuda_availability())
    ffmpeg_path = engine.find_ffmpeg()
    with engine._WHISPER_LOCK:
        cached_models = list(engine._WHISPER_CACHE.keys())
    return {
        "status": "ready",
        "version": "1.0.0",
        "cuda_available": cuda_available,
        "cached_models": cached_models,
        "ffmpeg_path": ffmpeg_path,
    }


def rpc_load_model(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    engine.load_model: Pre-warms Whisper model in memory cache.
    """
    params = params or {}
    model_size = params.get("model_size", "large-v3")
    engine.load_whisper_model_safely(model_size)
    cuda_available = bool(engine.check_cuda_availability())
    return {
        "loaded": True,
        "model_size": model_size,
        "device": "cuda" if cuda_available else "cpu",
    }


def rpc_shift_time(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    engine.shift_time: Applies time offset to subtitle segments and returns updated segments + SRT/VTT.
    """
    params = params or {}
    segments = params.get("segments")
    if segments is None:
        raise ValueError("Missing required 'segments' parameter")
    if not isinstance(segments, list):
        raise TypeError("'segments' parameter must be a list")

    offset_seconds = float(params.get("offset_seconds", 0.0))
    shifted = engine.shift_subtitle_segments(segments, offset_seconds)
    srt_content = engine.generate_srt(shifted)
    vtt_content = engine.generate_vtt(shifted)
    return {
        "segments": shifted,
        "srt_content": srt_content,
        "vtt_content": vtt_content,
    }


def rpc_process_video(
    params: Optional[Dict[str, Any]],
    req_id: Any,
    progress_cb: Optional[Callable[[Any, float, str, str], None]] = None,
) -> Dict[str, Any]:
    """
    engine.process_video: Full transcription and translation pipeline with streaming progress callbacks.
    """
    params = params or {}
    video_path = params.get("video_path")
    if not video_path:
        raise ValueError("Missing required 'video_path' parameter")
    abs_video = os.path.abspath(video_path)
    if not os.path.isfile(abs_video):
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    output_dir = params.get("output_dir")
    if not output_dir:
        output_dir = os.path.dirname(abs_video)
    abs_out_dir = os.path.abspath(output_dir)

    default_model = "large-v3" if engine.check_cuda_availability() else "base"
    model_size = params.get("model_size") or params.get("whisper_model") or default_model
    source_lang = params.get("source_lang") or params.get("audio_language")
    gemini_api_key = params.get("gemini_api_key")
    gemini_model = params.get("gemini_model", "gemini-2.5-flash")
    translation_style = params.get("translation_style", "jav")
    embed_mode = params.get("embed_mode", "burn")
    font_size = int(params.get("font_size", 18))
    ffmpeg_path = params.get("ffmpeg_path")

    def internal_progress(pct: float, msg: str):
        if progress_cb:
            stage = classify_stage(pct, msg)
            progress_cb(req_id, pct, stage, msg)

    res = engine.process_video_subtitles(
        video_path=abs_video,
        output_dir=abs_out_dir,
        model_size=model_size,
        source_lang=source_lang,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        progress_callback=internal_progress,
        ffmpeg_path=ffmpeg_path,
        translation_style=translation_style,
        embed_mode=embed_mode,
        font_size=font_size,
    )

    # Ensure srt_content and vtt_content are populated in result
    if "srt_content" not in res or res["srt_content"] is None:
        if os.path.isfile(res.get("srt_path", "")):
            with open(res["srt_path"], "r", encoding="utf-8", errors="ignore") as f:
                res["srt_content"] = f.read()
        elif res.get("segments"):
            res["srt_content"] = engine.generate_srt(res["segments"])
        else:
            res["srt_content"] = ""

    if "vtt_content" not in res or res["vtt_content"] is None:
        if os.path.isfile(res.get("vtt_path", "")):
            with open(res["vtt_path"], "r", encoding="utf-8", errors="ignore") as f:
                res["vtt_content"] = f.read()
        elif res.get("segments"):
            res["vtt_content"] = engine.generate_vtt(res["segments"])
        else:
            res["vtt_content"] = "WEBVTT\n"

    return res


def rpc_burn_subtitles(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    engine.burn_subtitles: Hardsubs subtitles into video using bundled FFmpeg with ASCII path isolation.
    """
    params = params or {}
    video_path = params.get("video_path")
    if not video_path:
        raise ValueError("Missing required 'video_path' parameter")
    abs_video = os.path.abspath(video_path)
    if not os.path.isfile(abs_video):
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    output_video_path = params.get("output_video_path")
    if not output_video_path:
        base, _ = os.path.splitext(abs_video)
        output_video_path = f"{base}_burned.mp4"
    abs_out_video = os.path.abspath(output_video_path)

    font_size = int(params.get("font_size", 18))
    ffmpeg_path = params.get("ffmpeg_path")

    srt_path = params.get("srt_path")
    srt_content = params.get("srt_content")

    temp_srt_path = None
    if srt_path and os.path.isfile(os.path.abspath(srt_path)):
        actual_srt_path = os.path.abspath(srt_path)
    elif srt_content is not None:
        out_dir = os.path.dirname(abs_out_video)
        os.makedirs(out_dir, exist_ok=True)
        temp_srt_path = os.path.join(out_dir, f"_temp_burn_{os.getpid()}_{int(time.time()*1000)}.srt")
        with open(temp_srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        actual_srt_path = temp_srt_path
    else:
        raise ValueError("Either 'srt_path' or 'srt_content' must be provided")

    try:
        out = engine.burn_subtitles_to_video(
            video_path=abs_video,
            srt_path=actual_srt_path,
            output_video_path=abs_out_video,
            font_size=font_size,
            ffmpeg_path=ffmpeg_path,
        )
        return {
            "output_video_path": out,
            "success": True,
        }
    finally:
        if temp_srt_path and os.path.isfile(temp_srt_path):
            try:
                os.remove(temp_srt_path)
            except Exception:
                pass


def rpc_mux_subtitles(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    engine.mux_subtitles: Softsubs subtitles into video container using FFmpeg stream copy.
    """
    params = params or {}
    video_path = params.get("video_path")
    if not video_path:
        raise ValueError("Missing required 'video_path' parameter")
    abs_video = os.path.abspath(video_path)
    if not os.path.isfile(abs_video):
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    output_video_path = params.get("output_video_path")
    if not output_video_path:
        base, ext = os.path.splitext(abs_video)
        ext = ext if ext else ".mp4"
        output_video_path = f"{base}_softsub{ext}"
    abs_out_video = os.path.abspath(output_video_path)

    ffmpeg_path = params.get("ffmpeg_path")
    srt_path = params.get("srt_path")
    srt_content = params.get("srt_content")

    temp_srt_path = None
    if srt_path and os.path.isfile(os.path.abspath(srt_path)):
        actual_srt_path = os.path.abspath(srt_path)
    elif srt_content is not None:
        out_dir = os.path.dirname(abs_out_video)
        os.makedirs(out_dir, exist_ok=True)
        temp_srt_path = os.path.join(out_dir, f"_temp_mux_{os.getpid()}_{int(time.time()*1000)}.srt")
        with open(temp_srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        actual_srt_path = temp_srt_path
    else:
        raise ValueError("Either 'srt_path' or 'srt_content' must be provided")

    try:
        out = engine.mux_subtitles_to_video(
            video_path=abs_video,
            srt_path=actual_srt_path,
            output_video_path=abs_out_video,
            ffmpeg_path=ffmpeg_path,
        )
        return {
            "output_video_path": out,
            "success": True,
        }
    finally:
        if temp_srt_path and os.path.isfile(temp_srt_path):
            try:
                os.remove(temp_srt_path)
            except Exception:
                pass


def rpc_shutdown(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    engine.shutdown: Clean daemon teardown.
    """
    return {"status": "shutting_down"}


def dispatch_rpc(
    req: Dict[str, Any],
    progress_cb: Optional[Callable[[Any, float, str, str], None]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], bool]:
    """
    Dispatches a single JSON-RPC request dictionary.
    Returns: (result_dict, error_dict, is_shutdown_bool)
    """
    method = req.get("method")
    params = req.get("params") or {}
    req_id = req.get("id")

    if not method or not isinstance(method, str):
        return None, {"code": -32600, "message": "Invalid Request: method string is required"}, False

    norm_method = method
    if norm_method.startswith("engine."):
        norm_method = norm_method[len("engine."):]

    handlers = {
        "ping": lambda p: rpc_ping(p),
        "health": lambda p: rpc_ping(p),
        "load_model": lambda p: rpc_load_model(p),
        "process_video": lambda p: rpc_process_video(p, req_id, progress_cb),
        "shift_time": lambda p: rpc_shift_time(p),
        "burn_subtitles": lambda p: rpc_burn_subtitles(p),
        "mux_subtitles": lambda p: rpc_mux_subtitles(p),
        "shutdown": lambda p: rpc_shutdown(p),
    }

    if norm_method not in handlers:
        return None, {"code": -32601, "message": f"Method not found: '{method}'"}, False

    try:
        res = handlers[norm_method](params)
        is_shutdown = (norm_method == "shutdown")
        return res, None, is_shutdown
    except Exception as e:
        if isinstance(e, (ValueError, TypeError, FileNotFoundError)):
            sys.stderr.write(f"[RPC ERROR] in {method}: {str(e)}\n")
        else:
            tb = traceback.format_exc()
            sys.stderr.write(f"[RPC ERROR] in {method}: {str(e)}\n{tb}\n")
        sys.stderr.flush()
        return None, {"code": -32603, "message": str(e)}, False


def make_response(req_id: Any, result: Any, error: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Formats standard JSON-RPC response object.
    """
    resp: Dict[str, Any] = {"id": req_id}
    if error is not None:
        resp["result"] = None
        resp["error"] = error
    else:
        resp["result"] = result
        resp["error"] = None
    return resp


def run_daemon() -> None:
    """
    Main daemon entrypoint:
    - Redirects logging and warnings to stderr.
    - Sets sys.stdout to sys.stderr so library prints do not pollute stdout.
    - Runs a dedicated worker thread for request execution.
    - Main thread acts as Stdin EOF Watchdog, exiting immediately via os._exit(0) upon EOF.
    """
    # Setup stderr logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Route warnings to stderr
    def _warn_handler(message, category, filename, lineno, file=None, line=None):
        sys.stderr.write(f"[WARNING] {category.__name__}: {message} ({filename}:{lineno})\n")
        sys.stderr.flush()

    warnings.showwarning = _warn_handler

    # Redirect general prints to stderr so protocol stdout remains pristine NDJSON
    sys.stdout = sys.stderr

    request_queue: queue.Queue = queue.Queue()

    def progress_callback(req_id: Any, percent: float, stage: str, message: str):
        event = {
            "type": "progress",
            "data": {
                "task_id": req_id,
                "percent": round(percent, 2),
                "stage": stage,
                "message": message,
            },
        }
        send_message(event)

    def worker_loop():
        while True:
            item = request_queue.get()
            if item is None:
                break
            line_str = item
            try:
                req = json.loads(line_str)
            except Exception as e:
                send_message({
                    "id": None,
                    "result": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
                })
                request_queue.task_done()
                continue

            if not isinstance(req, dict):
                send_message({
                    "id": None,
                    "result": None,
                    "error": {"code": -32600, "message": "Invalid Request: expected JSON object"},
                })
                request_queue.task_done()
                continue

            req_id = req.get("id")
            result, error, is_shutdown = dispatch_rpc(req, progress_cb=progress_callback)
            resp = make_response(req_id, result, error)
            send_message(resp)
            request_queue.task_done()

            if is_shutdown:
                try:
                    _PROTOCOL_STDOUT.flush()
                except Exception:
                    pass
                os._exit(0)

    worker_thread = threading.Thread(target=worker_loop, daemon=True, name="RpcWorker")
    worker_thread.start()

    # Main thread runs Stdin EOF watchdog loop
    while True:
        try:
            line = sys.stdin.readline()
        except Exception:
            os._exit(0)

        # Stdin EOF watchdog: when sys.stdin.readline() == "", terminates immediately via os._exit(0)
        if line == "":
            os._exit(0)

        clean = line.strip()
        if clean:
            request_queue.put(clean)


if __name__ == "__main__":
    run_daemon()
