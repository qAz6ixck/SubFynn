"""
Command-Line Interface (CLI) for Thai Subtitle Generator.
Usage:
    python cli.py input_video.mp4
    python cli.py input_video.mp4 --model base --lang en --burn
"""

import os
import sys
import argparse

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

from engine import (
    process_video_subtitles,
    burn_subtitles_to_video,
    shift_subtitle_segments,
    generate_srt,
    generate_vtt,
    find_ffmpeg,
)


def main():
    parser = argparse.ArgumentParser(
        description="โปรแกรมสร้างซับไทยอัตโนมัติ (AI Thai Subtitle Generator CLI)"
    )
    parser.add_argument("video", help="ไฟล์วิดีโอต้นฉบับ เช่น movie.mp4, clip.mkv")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="ขนาดโมเดล Whisper (default: base, แนะนำ medium หรือ large-v3 สำหรับ JAV)",
    )
    parser.add_argument(
        "--style",
        default="jav",
        choices=["jav", "jav_dirty", "jav_hardcore", "jav_vulgar", "jav_sweet", "general", "anime", "drama"],
        help="สไตล์การแปลคำบรรยาย (default: jav แปลหนังผู้ใหญ่ 18+ ได้อารมณ์, jav_dirty/jav_hardcore: สายดุดัน หยาบคายได้เต็มที่ ไม่เซ็นเซอร์, jav_sweet: สายหวานอ้อน)",
    )
    parser.add_argument(
        "--gemini-model",
        default="gemini-2.5-flash",
        choices=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        help="โมเดล Gemini สำหรับแปลภาษา (default: gemini-2.5-flash, แนะนำ gemini-2.5-pro สำหรับ JAV 18+ ขั้นสุด)",
    )
    parser.add_argument("--lang", default="auto", help="ภาษาเสียงต้นฉบับ เช่น en, ja, zh, ko, auto (default: auto)")
    parser.add_argument("--gemini-key", default=None, help="Google Gemini API Key (optional)")
    parser.add_argument("--outdir", default=None, help="โฟลเดอร์สำหรับบันทึกผลลัพธ์ (default: โฟลเดอร์เดียวกับวิดีโอ)")
    parser.add_argument("--shift-seconds", type=float, default=0.0, help="เลื่อนเวลาซับไตเติล (+/- วินาที เช่น +0.5 หรือ -1.0)")
    parser.add_argument(
        "--embed-mode",
        default="burn",
        choices=["burn", "soft", "both", "none"],
        help="โหมดนำซับไตเติลใส่ลงในคลิปวิดีโอ (default: burn ฝังซับติดภาพ, soft: ฝังซับเร็ว 1 วิ เปิด/ปิดได้, both: ทำทั้งคู่, none: ไม่ใส่)",
    )
    parser.add_argument("--burn", action="store_true", help="ฝังซับไตเติลลงในวิดีโอ MP4 อัตโนมัติ (เทียบเท่า --embed-mode burn)")

    args = parser.parse_args()

    video_path = os.path.abspath(args.video)
    if not os.path.isfile(video_path):
        print(f"ข้อผิดพลาด: ไม่พบไฟล์วิดีโอ {video_path}")
        sys.exit(1)

    out_dir = args.outdir or os.path.dirname(video_path)
    os.makedirs(out_dir, exist_ok=True)

    embed_choice = getattr(args, "embed_mode", "burn" if getattr(args, "burn", False) else "none")
    if getattr(args, "burn", False):
        embed_choice = "burn"

    print(f"🎬 กำลังประมวลผลวิดีโอ: {os.path.basename(video_path)}")
    print(f"⚙️ โมเดล Whisper: {args.model} | โมเดลแปลภาษา: {args.gemini_model} | ภาษาต้นฉบับ: {args.lang} | สไตล์: {args.style} | นำซับใส่คลิป: {embed_choice}")

    def on_progress(pct, msg):
        print(f"[{pct:5.1f}%] {msg}")

    try:
        res = process_video_subtitles(
            video_path=video_path,
            output_dir=out_dir,
            model_size=args.model,
            source_lang=args.lang,
            gemini_api_key=args.gemini_key,
            gemini_model=args.gemini_model,
            translation_style=args.style,
            embed_mode=embed_choice,
            progress_callback=on_progress,
        )

        if args.shift_seconds != 0.0 and res["segments"]:
            print(f"⏱️ กำลังปรับเลื่อนเวลาซับ: {args.shift_seconds:+.2f} วินาที...")
            shifted_segs = shift_subtitle_segments(res["segments"], args.shift_seconds)
            res["segments"] = shifted_segs
            res["srt_content"] = generate_srt(shifted_segs)
            res["vtt_content"] = generate_vtt(shifted_segs)
            with open(res["srt_path"], "w", encoding="utf-8") as f:
                f.write(res["srt_content"])
            with open(res["vtt_path"], "w", encoding="utf-8") as f:
                f.write(res["vtt_content"])

        print(f"\n✅ สร้างซับไทยสำเร็จ!")
        print(f"📌 ภาษาที่ตรวจพบ: {res['detected_language']}")
        print(f"📌 จำนวนท่อนซับ: {len(res['segments'])}")
        print(f"📁 ไฟล์ SRT: {res['srt_path']}")
        print(f"📁 ไฟล์ VTT: {res['vtt_path']}")

        if res.get("burned_video_path") and os.path.isfile(res["burned_video_path"]):
            print(f"🎬 บันทึกวิดีโอพร้อมซับไทย (Hardsub): {res['burned_video_path']}")
        elif getattr(args, "burn", False):
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            burned_mp4 = os.path.join(out_dir, f"{base_name}_subtitled.mp4")
            print(f"\n🎬 กำลังฝังซับไตเติลลงวิดีโอ: {burned_mp4} ...")
            burn_subtitles_to_video(
                video_path=video_path,
                srt_path=res["srt_path"],
                output_video_path=burned_mp4,
            )
            print(f"✅ บันทึกวิดีโอพร้อมซับไทยเรียบร้อย: {burned_mp4}")

        if res.get("softsub_video_path") and os.path.isfile(res["softsub_video_path"]):
            print(f"🎬 บันทึกวิดีโอพร้อมซับไทย (Softsub): {res['softsub_video_path']}")

    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
