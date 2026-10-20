"""
Desktop GUI for SubFynn - AI Thai Subtitle Generator using CustomTkinter.
Redesigned with #23212C theme, zero emojis, Whisper Large-v3 default,
and specialized Gemini translation models.
"""

import os
import sys
import subprocess
import threading
from tkinter import filedialog, messagebox, ttk
from typing import Optional, List, Dict, Any
import customtkinter as ctk

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

from engine import (
    process_video_subtitles,
    burn_subtitles_to_video,
    generate_srt,
    shift_subtitle_segments,
    find_ffmpeg,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================
# Studio Dark Palette (#23212C Theme & Zero Emojis)
# ==========================================
COLOR_BG = "#23212C"
COLOR_CARD = "#1C1924"
COLOR_CARD_HOVER = "#262232"
COLOR_CARD_BORDER = "#3D374D"
COLOR_CARD_HEADER = "#2B2638"
COLOR_INPUT_BG = "#16141D"
COLOR_INPUT_BORDER = "#433C55"
COLOR_DROPDOWN_BG = "#292436"
COLOR_DROPDOWN_HOVER = "#3B344D"
COLOR_TEXT_WHITE = "#FFFFFF"
COLOR_TEXT_MUTED = "#A6A0B5"
COLOR_TEXT_DIM = "#7B758D"
COLOR_ACCENT_PRIMARY = "#6366F1"        # Vibrant Indigo
COLOR_ACCENT_PRIMARY_HOVER = "#4F46E5"
COLOR_ACCENT_CYAN = "#38BDF8"           # Electric Cyan
COLOR_ACCENT_CYAN_HOVER = "#0284C7"
COLOR_ACCENT_EMERALD = "#10B981"        # Success Emerald
COLOR_ACCENT_EMERALD_BG = "#13382D"
COLOR_ACCENT_ROSE = "#F43F5E"           # Burn/Export Rose
COLOR_ACCENT_ROSE_HOVER = "#E11D48"


class ThaiSubtitleApp(ctk.CTk):
    def __init__(self, initial_video: Optional[str] = None):
        super().__init__()

        self.title("SubFynn - AI Thai Subtitle Studio")
        self.geometry("1060x880")
        self.minsize(920, 760)
        self.configure(fg_color=COLOR_BG)

        # Base directories
        self.base_dir = (
            os.path.dirname(sys.executable)
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )
        self.output_dir = os.path.join(self.base_dir, "data", "SubFynn_Outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.last_output_dir = self.output_dir
        self.last_result = None
        self.video_path = ""

        # Set Window Icon
        self._setup_icon()

        # Apply Windows 11 Acrylic / Mica effect if available
        try:
            import pywinstyles
            pywinstyles.apply_style(self, "acrylic")
            pywinstyles.change_border_color(self, COLOR_CARD_BORDER)
            pywinstyles.change_header_color(self, COLOR_BG)
            pywinstyles.change_title_color(self, COLOR_TEXT_WHITE)
        except Exception:
            pass

        try:
            self.tk.eval("proc bgerror {args} {}")
        except Exception:
            pass

        self._build_ui()
        if initial_video:
            self.load_video(initial_video)

    def _setup_icon(self):
        icon_ico = os.path.join(self.base_dir, "assets", "app_icon.ico")
        if os.path.isfile(icon_ico):
            try:
                self.iconbitmap(icon_ico)
            except Exception:
                pass
        icon_png = os.path.join(self.base_dir, "assets", "app_icon.png")
        if os.path.isfile(icon_png):
            try:
                from PIL import Image, ImageTk
                img = ImageTk.PhotoImage(Image.open(icon_png).resize((64, 64)))
                self.iconphoto(False, img)
                self._icon_ref = img
            except Exception:
                pass

    def _build_ui(self):
        page = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLOR_CARD_BORDER,
            scrollbar_button_hover_color=COLOR_ACCENT_PRIMARY,
        )
        page.pack(fill="both", expand=True, padx=12, pady=12)

        def make_card(parent=page):
            return ctk.CTkFrame(
                parent,
                corner_radius=18,
                fg_color=COLOR_CARD,
                border_width=1,
                border_color=COLOR_CARD_BORDER,
            )

        # ----------------------------------------------------
        # 1. Header Bar
        # ----------------------------------------------------
        header = make_card()
        header.pack(fill="x", pady=(0, 12))
        header_row = ctk.CTkFrame(header, fg_color="transparent")
        header_row.pack(fill="x", padx=20, pady=16)

        brand = ctk.CTkFrame(header_row, fg_color="transparent")
        brand.pack(side="left", fill="x", expand=True)

        brand_badge = ctk.CTkLabel(
            brand,
            text="SF",
            width=46,
            height=46,
            corner_radius=12,
            fg_color=COLOR_ACCENT_PRIMARY,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
        )
        brand_badge.pack(side="left", padx=(0, 14))

        title_group = ctk.CTkFrame(brand, fg_color="transparent")
        title_group.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            title_group,
            text="SubFynn Studio",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_group,
            text="AI Thai Subtitle Generator (Windows Desktop Edition)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        header_tags = ctk.CTkFrame(header_row, fg_color="transparent")
        header_tags.pack(side="right")

        ctk.CTkLabel(
            header_tags,
            text="Whisper Large-v3",
            corner_radius=10,
            fg_color="#213247",
            text_color=COLOR_ACCENT_CYAN,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=12,
            pady=6,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            header_tags,
            text="Standalone EXE",
            corner_radius=10,
            fg_color=COLOR_ACCENT_EMERALD_BG,
            text_color=COLOR_ACCENT_EMERALD,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=12,
            pady=6,
        ).pack(side="left")

        # ----------------------------------------------------
        # 2. File Selection Zone
        # ----------------------------------------------------
        file_card = make_card()
        file_card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            file_card,
            text="เลือกไฟล์วิดีโอ (Source Video File)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(anchor="w", padx=20, pady=(16, 8))

        file_row = ctk.CTkFrame(file_card, fg_color="transparent")
        file_row.pack(fill="x", padx=20, pady=(0, 16))

        self.file_entry = ctk.CTkEntry(
            file_row,
            placeholder_text="คลิกปุ่มเลือกไฟล์ หรือลากไฟล์วิดีโอมาวางที่นี่",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            corner_radius=12,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_WHITE,
            placeholder_text_color=COLOR_TEXT_DIM,
            height=42,
        )
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = ctk.CTkButton(
            file_row,
            text="เลือกไฟล์...",
            width=130,
            height=42,
            corner_radius=12,
            fg_color=COLOR_DROPDOWN_BG,
            hover_color=COLOR_DROPDOWN_HOVER,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self.browse_video,
        )
        browse_btn.pack(side="right")

        # ----------------------------------------------------
        # 3. Model Configuration Grid
        # ----------------------------------------------------
        options_card = make_card()
        options_card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            options_card,
            text="ตั้งค่าโมเดลและการแปลภาษา (Engine & Translation Settings)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(anchor="w", padx=20, pady=(16, 12))

        options_grid = ctk.CTkFrame(options_card, fg_color="transparent")
        options_grid.pack(fill="x", padx=14, pady=(0, 16))
        options_grid.grid_columnconfigure(0, weight=1, uniform="opt-col")
        options_grid.grid_columnconfigure(1, weight=1, uniform="opt-col")

        # Variables
        self.model_var = ctk.StringVar(value="large-v3 (โมเดลแม่นยำสูงสุด ล็อคมาตรฐาน)")
        self.style_var = ctk.StringVar(value="jav_dirty (หนังผู้ใหญ่ 18+ หยาบคายได้เต็มที่ / Dirty Talk)")
        self.gemini_model_var = ctk.StringVar(value="gemini-3.5-live-translate-preview (Gemini Live Translate)")
        self.embed_mode_var = ctk.StringVar(value="burn (ฝังซับติดภาพถาวร)")
        self.lang_var = ctk.StringVar(value="ja (ญี่ปุ่น - แนะนำ JAV)")

        def create_dropdown_field(row, column, label_title, options, var_ref):
            box = ctk.CTkFrame(options_grid, fg_color="transparent")
            box.grid(row=row, column=column, sticky="ew", padx=6, pady=8)
            ctk.CTkLabel(
                box,
                text=label_title,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLOR_TEXT_WHITE,
            ).pack(anchor="w", pady=(0, 6))

            menu = ctk.CTkOptionMenu(
                box,
                values=options,
                variable=var_ref,
                corner_radius=11,
                height=38,
                fg_color=COLOR_DROPDOWN_BG,
                button_color=COLOR_CARD_BORDER,
                button_hover_color=COLOR_DROPDOWN_HOVER,
                text_color=COLOR_TEXT_WHITE,
                dropdown_fg_color=COLOR_INPUT_BG,
                dropdown_text_color=COLOR_TEXT_WHITE,
                dropdown_hover_color=COLOR_DROPDOWN_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=12),
                dropdown_font=ctk.CTkFont(family="Segoe UI", size=12),
            )
            menu.pack(fill="x")
            return menu

        # Row 0: STT Model (Locked to Large-v3) & Translation Style
        self.model_menu = create_dropdown_field(
            0, 0,
            "โมเดล Whisper Speech-to-Text (ค่าเริ่มต้น Large-v3)",
            [
                "large-v3 (โมเดลแม่นยำสูงสุด ล็อคมาตรฐาน)",
            ],
            self.model_var,
        )

        self.style_menu = create_dropdown_field(
            0, 1,
            "สไตล์การแปลคำบรรยายไทย",
            [
                "jav_dirty (หนังผู้ใหญ่ 18+ หยาบคายได้เต็มที่ / Dirty Talk)",
                "jav (หนังผู้ใหญ่ 18+ มาตรฐานแฟนซับ)",
                "jav_sweet (หนังผู้ใหญ่ 18+ สายหวานอ้อน)",
                "general (ทั่วไป / ภาพยนตร์)",
                "anime (อนิเมะ / ซีรีส์)",
            ],
            self.style_var,
        )

        # Row 1: 3 Specialized Gemini Models & Auto-embed mode
        self.gemini_model_menu = create_dropdown_field(
            1, 0,
            "โมเดล AI แปลภาษาเฉพาะทาง (3 รุ่นล่าสุด)",
            [
                "gemini-3.5-live-translate-preview (Gemini Live Translate)",
                "cloud-translation-llm (Cloud Translation LLM)",
                "gemini-2.5-flash (Gemini Adaptive Translation)",
            ],
            self.gemini_model_var,
        )

        self.embed_mode_menu = create_dropdown_field(
            1, 1,
            "การนำซับไตเติลใส่คลิปวิดีโอ",
            [
                "burn (ฝังซับติดภาพถาวร)",
                "soft (ฝังซับในไฟล์เร็ว)",
                "both (บันทึกทั้ง 2 แบบ)",
                "none (เฉพาะไฟล์ .SRT)",
            ],
            self.embed_mode_var,
        )

        # Row 2: Source Audio Language & Gemini API Key
        self.lang_menu = create_dropdown_field(
            2, 0,
            "ภาษาเสียงพูดต้นฉบับ",
            [
                "ja (ญี่ปุ่น - แนะนำ JAV)",
                "auto (ตรวจจับอัตโนมัติ)",
                "en (อังกฤษ)",
                "zh (จีน)",
                "ko (เกาหลี)",
                "th (ไทย)",
            ],
            self.lang_var,
        )

        api_field = ctk.CTkFrame(options_grid, fg_color="transparent")
        api_field.grid(row=2, column=1, sticky="ew", padx=6, pady=8)
        ctk.CTkLabel(
            api_field,
            text="Google Gemini API Key (ไม่บังคับ - เว้นว่างเพื่อใช้ระบบฟรี)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(anchor="w", pady=(0, 6))

        self.gemini_entry = ctk.CTkEntry(
            api_field,
            placeholder_text="วาง Gemini API Key ที่นี่ (ถ้ามี)",
            show="*",
            corner_radius=11,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_WHITE,
            placeholder_text_color=COLOR_TEXT_DIM,
            height=38,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.gemini_entry.pack(fill="x")

        # ----------------------------------------------------
        # 4. Action & Progress Zone
        # ----------------------------------------------------
        action_card = make_card()
        action_card.pack(fill="x", pady=8)

        self.start_btn = ctk.CTkButton(
            action_card,
            text="เริ่มสร้างซับไทย (Start Subtitle Generation)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=48,
            corner_radius=13,
            fg_color=COLOR_ACCENT_PRIMARY,
            hover_color=COLOR_ACCENT_PRIMARY_HOVER,
            text_color=COLOR_TEXT_WHITE,
            command=self.start_processing,
        )
        self.start_btn.pack(fill="x", padx=20, pady=(16, 10))

        self.progress_bar = ctk.CTkProgressBar(
            action_card,
            corner_radius=5,
            height=8,
            fg_color=COLOR_INPUT_BG,
            progress_color=COLOR_ACCENT_CYAN,
        )
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 8))
        self.progress_bar.set(0)

        self.status_lbl = ctk.CTkLabel(
            action_card,
            text="พร้อมทำงาน กรุณาเลือกไฟล์วิดีโอแล้วกดเริ่มสร้างซับ",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_TEXT_MUTED,
            wraplength=980,
        )
        self.status_lbl.pack(padx=20, pady=(0, 16))

        # ----------------------------------------------------
        # 5. Interactive Subtitle Editor & Exporter
        # ----------------------------------------------------
        out_card = make_card()
        out_card.pack(fill="both", expand=True, pady=(8, 12))

        out_header = ctk.CTkFrame(out_card, fg_color="transparent")
        out_header.pack(fill="x", padx=20, pady=(16, 10))

        ctk.CTkLabel(
            out_header,
            text="ตารางแก้ไขคำบรรยายซับไทย (Subtitle Editor)",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(side="left")

        self.sub_count_lbl = ctk.CTkLabel(
            out_header,
            text="0 บรรทัด",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_TEXT_DIM,
        )
        self.sub_count_lbl.pack(side="left", padx=(10, 0))

        # Time Shifting Controls
        self.shift_plus_btn = ctk.CTkButton(
            out_header,
            text="+0.5 วินาที",
            width=90,
            height=30,
            corner_radius=9,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLOR_DROPDOWN_BG,
            hover_color=COLOR_DROPDOWN_HOVER,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            text_color=COLOR_TEXT_WHITE,
            command=lambda: self.shift_time(0.5),
            state="disabled",
        )
        self.shift_plus_btn.pack(side="right", padx=(6, 0))

        self.shift_minus_btn = ctk.CTkButton(
            out_header,
            text="-0.5 วินาที",
            width=90,
            height=30,
            corner_radius=9,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=COLOR_DROPDOWN_BG,
            hover_color=COLOR_DROPDOWN_HOVER,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            text_color=COLOR_TEXT_WHITE,
            command=lambda: self.shift_time(-0.5),
            state="disabled",
        )
        self.shift_minus_btn.pack(side="right")

        # Subtitle Textbox (Compatible & full-view editable)
        self.srt_textbox = ctk.CTkTextbox(
            out_card,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=12,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_INPUT_BORDER,
            text_color=COLOR_TEXT_WHITE,
            height=260,
        )
        self.srt_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 14))

        # Bottom Action Bar
        export_row = ctk.CTkFrame(out_card, fg_color="transparent")
        export_row.pack(fill="x", padx=20, pady=(0, 18))

        self.save_srt_btn = ctk.CTkButton(
            export_row,
            text="บันทึกไฟล์ซับ (.SRT)",
            command=self.save_srt,
            state="disabled",
            width=180,
            height=40,
            corner_radius=11,
            fg_color=COLOR_DROPDOWN_BG,
            hover_color=COLOR_DROPDOWN_HOVER,
            border_width=1,
            border_color=COLOR_CARD_BORDER,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
        )
        self.save_srt_btn.pack(side="left", padx=(0, 10))

        self.burn_btn = ctk.CTkButton(
            export_row,
            text="ฝังซับลงวิดีโอ (Burn-in MP4)",
            command=self.burn_video,
            state="disabled",
            fg_color=COLOR_ACCENT_ROSE,
            hover_color=COLOR_ACCENT_ROSE_HOVER,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            width=210,
            height=40,
            corner_radius=11,
        )
        self.burn_btn.pack(side="left", padx=(0, 10))

        self.open_folder_btn = ctk.CTkButton(
            export_row,
            text="เปิดโฟลเดอร์ผลลัพธ์",
            command=self.open_output_folder,
            state="disabled",
            fg_color=COLOR_ACCENT_EMERALD_BG,
            hover_color="#18503E",
            border_width=1,
            border_color=COLOR_ACCENT_EMERALD,
            text_color=COLOR_ACCENT_EMERALD,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            width=180,
            height=40,
            corner_radius=11,
        )
        self.open_folder_btn.pack(side="left")

    def load_video(self, video_path: str):
        if not video_path:
            return
        abs_path = os.path.abspath(video_path)
        if os.path.isfile(abs_path):
            self.video_path = abs_path
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, abs_path)
            size_mb = os.path.getsize(abs_path) / (1024 * 1024)
            self.status_lbl.configure(
                text=f"เลือกไฟล์: {os.path.basename(abs_path)} ({size_mb:.1f} MB)",
                text_color=COLOR_TEXT_WHITE,
            )

    def browse_video(self):
        filetypes = [
            ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.wmv *.m4v"),
            ("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac *.ogg"),
            ("All files", "*.*"),
        ]
        filename = filedialog.askopenfilename(title="เลือกไฟล์วิดีโอ", filetypes=filetypes)
        if filename:
            self.load_video(filename)

    def start_processing(self):
        video_file = self.file_entry.get().strip()
        if not video_file or not os.path.isfile(video_file):
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกไฟล์วิดีโอที่ถูกต้องก่อนเริ่ม")
            return

        self.video_path = video_file
        model_choice = "large-v3"  # Default locked to Large-v3
        raw_model_val = self.model_var.get().strip().split()[0].lower()
        if raw_model_val in ("large-v3", "large", "medium", "small", "base", "tiny"):
            model_choice = raw_model_val

        lang_choice = self.lang_var.get().split()[0]
        style_choice = self.style_var.get().split()[0]
        gemini_model_choice = self.gemini_model_var.get().split()[0]
        gemini_key = self.gemini_entry.get().strip()
        embed_choice = self.embed_mode_var.get().split()[0]

        video_dir = os.path.dirname(os.path.abspath(self.video_path))
        target_output_dir = video_dir if os.path.isdir(video_dir) else self.output_dir
        self.last_output_dir = target_output_dir

        self.start_btn.configure(state="disabled")
        self.save_srt_btn.configure(state="disabled")
        self.burn_btn.configure(state="disabled")
        self.open_folder_btn.configure(state="disabled")
        self.shift_minus_btn.configure(state="disabled")
        self.shift_plus_btn.configure(state="disabled")
        self.progress_bar.set(0.05)
        self.status_lbl.configure(text="กำลังเริ่มต้นกระบวนการ...", text_color=COLOR_ACCENT_CYAN)

        def worker():
            def on_progress(pct, msg):
                self.after(0, lambda: self._update_progress(pct, msg))

            try:
                res = process_video_subtitles(
                    video_path=self.video_path,
                    output_dir=target_output_dir,
                    model_size=model_choice,
                    source_lang=lang_choice,
                    gemini_api_key=gemini_key,
                    gemini_model=gemini_model_choice,
                    translation_style=style_choice,
                    embed_mode=embed_choice,
                    progress_callback=on_progress,
                )
                self.after(0, lambda: self._on_success(res))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _update_progress(self, pct, msg):
        self.progress_bar.set(pct / 100.0)
        self.status_lbl.configure(text=msg)

    def _on_success(self, res):
        self.last_result = res
        self.start_btn.configure(state="normal")
        self.save_srt_btn.configure(state="normal")
        self.burn_btn.configure(state="normal")
        self.open_folder_btn.configure(state="normal")
        self.shift_minus_btn.configure(state="normal")
        self.shift_plus_btn.configure(state="normal")
        self.progress_bar.set(1.0)
        self.status_lbl.configure(
            text="สร้างซับไทยและนำซับใส่คลิปสำเร็จเรียบร้อย",
            text_color=COLOR_ACCENT_EMERALD,
        )

        srt_text = res.get("srt_content", "")
        self.srt_textbox.delete("1.0", "end")
        self.srt_textbox.insert("1.0", srt_text)

        segs_count = len(res.get("segments", []))
        self.sub_count_lbl.configure(text=f"{segs_count} บรรทัด")

        vid_path = res.get("video_output_path") or res.get("burned_video_path") or res.get("softsub_video_path")
        if vid_path and os.path.isfile(vid_path):
            msg = (
                f"สร้างซับไทยและนำซับใส่คลิปเสร็จเรียบร้อยแล้ว\n\n"
                f"ไฟล์วิดีโอ: {os.path.basename(vid_path)}\n"
                f"ที่อยู่ไฟล์: {os.path.dirname(vid_path)}\n\n"
                f"ต้องการเปิดโฟลเดอร์ดูไฟล์ทันทีเลยหรือไม่?"
            )
            if messagebox.askyesno("สำเร็จ", msg):
                self.open_output_folder()
        else:
            messagebox.showinfo(
                "สำเร็จ",
                f"สร้างซับไทยเสร็จเรียบร้อย ตรวจพบภาษา: {res.get('detected_language', 'ja')} ({segs_count} ท่อน)",
            )

    def open_output_folder(self):
        target_dir = getattr(self, "last_output_dir", self.output_dir)
        if not os.path.isdir(target_dir):
            target_dir = self.output_dir
        if sys.platform == "win32":
            os.startfile(target_dir)
        else:
            subprocess.Popen(["xdg-open", target_dir])

    def _on_error(self, err_msg):
        self.start_btn.configure(state="normal")
        self.progress_bar.set(0.0)
        self.status_lbl.configure(text=f"เกิดข้อผิดพลาด: {err_msg}", text_color=COLOR_ACCENT_ROSE)
        messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถสร้างซับไทยได้:\n{err_msg}")

    def shift_time(self, offset_seconds: float):
        if not self.last_result or "segments" not in self.last_result:
            return
        segs = self.last_result["segments"]
        if not segs:
            return
        shifted = shift_subtitle_segments(segs, offset_seconds)
        self.last_result["segments"] = shifted
        new_srt = generate_srt(shifted)
        self.last_result["srt_content"] = new_srt
        self.srt_textbox.delete("1.0", "end")
        self.srt_textbox.insert("1.0", new_srt)

        if "srt_path" in self.last_result and os.path.isfile(self.last_result["srt_path"]):
            with open(self.last_result["srt_path"], "w", encoding="utf-8") as f:
                f.write(new_srt)
        self.status_lbl.configure(
            text=f"ปรับเลื่อนเวลาซับ {offset_seconds:+.1f} วินาทีเรียบร้อย",
            text_color=COLOR_ACCENT_CYAN,
        )

    def save_srt(self):
        if not self.last_result:
            return
        content = self.srt_textbox.get("1.0", "end").strip()
        save_path = filedialog.asksaveasfilename(
            title="บันทึกไฟล์ .SRT",
            defaultextension=".srt",
            filetypes=[("SubRip Subtitles", "*.srt")],
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("สำเร็จ", f"บันทึกไฟล์เรียบร้อยแล้วที่:\n{save_path}")

    def burn_video(self):
        if not self.last_result or not self.video_path:
            return

        save_video_path = filedialog.asksaveasfilename(
            title="เลือกตำแหน่งบันทึกวิดีโอพร้อมซับ",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")],
        )
        if not save_video_path:
            return

        import time
        current_srt = self.srt_textbox.get("1.0", "end").strip()
        temp_srt = os.path.join(self.output_dir, f"temp_burn_{int(time.time() * 1000)}.srt")
        with open(temp_srt, "w", encoding="utf-8") as f:
            f.write(current_srt)

        self.burn_btn.configure(state="disabled")
        self.status_lbl.configure(text="กำลังฝังซับไตเติลลงวิดีโอด้วย FFmpeg...", text_color=COLOR_ACCENT_CYAN)

        def burn_worker():
            try:
                burn_subtitles_to_video(
                    video_path=self.video_path,
                    srt_path=temp_srt,
                    output_video_path=save_video_path,
                )
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        "สำเร็จ",
                        f"ฝังซับและบันทึกวิดีโอเรียบร้อยแล้วที่:\n{save_video_path}",
                    ),
                )
                self.after(
                    0,
                    lambda: self.status_lbl.configure(
                        text="ฝังซับลงวิดีโอเรียบร้อย",
                        text_color=COLOR_ACCENT_EMERALD,
                    ),
                )
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"การฝังซับล้มเหลว:\n{str(e)}"))
                self.after(
                    0,
                    lambda: self.status_lbl.configure(
                        text=f"ฝังซับล้มเหลว: {str(e)}",
                        text_color=COLOR_ACCENT_ROSE,
                    ),
                )
            finally:
                if os.path.isfile(temp_srt):
                    try:
                        os.remove(temp_srt)
                    except Exception:
                        pass
                self.after(0, lambda: self.burn_btn.configure(state="normal"))

        t = threading.Thread(target=burn_worker, daemon=True)
        t.start()


if __name__ == "__main__":
    init_video = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    app = ThaiSubtitleApp(initial_video=init_video)
    app.mainloop()
