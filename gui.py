"""
Desktop GUI for Thai Subtitle Generator using CustomTkinter.
Run via: python gui.py
"""

import os
import sys
import subprocess
import threading
from tkinter import filedialog, messagebox
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
# Glassmorphism Dark & Crisp White Palette
# Pure pitch black, frosted acrylic & crisp white borders
# ==========================================
COLOR_BG = "#000000"                  # Pure pitch black
COLOR_GLASS_CARD = "#12121c"          # Translucent dark frosted glass card
COLOR_GLASS_BORDER = "#ffffff"        # Crisp pure white border line
COLOR_GLASS_BORDER_SUBTLE = "#ffffff" # Crisp pure white border line
COLOR_INPUT_BG = "#08080f"            # Deep recessed input field
COLOR_DROPDOWN_BG = "#141420"         # Dropdown pill background
COLOR_DROPDOWN_HOVER = "#242436"      # Dropdown hover
COLOR_TEXT_WHITE = "#ffffff"          # Crisp pure white text
COLOR_TEXT_MUTED = "#f8fafc"          # Crisp bright white text
COLOR_TEXT_DIM = "#cbd5e1"            # Subtle secondary white text
COLOR_ACCENT_WHITE = "#ffffff"        # High-contrast white accent button
COLOR_ACCENT_HOVER = "#e2e8f0"        # Hover for white button

from typing import Optional


class ThaiSubtitleApp(ctk.CTk):
    def __init__(self, initial_video: Optional[str] = None):
        super().__init__()

        self.title("SubFynn - โปรแกรมสร้างซับไทยอัตโนมัติ (AI Thai Subtitle Generator)")
        self.geometry("940x780")
        self.minsize(840, 700)
        self.configure(fg_color=COLOR_BG)

        # Apply Windows 11 Acrylic Glassmorphism effect
        try:
            import pywinstyles
            pywinstyles.apply_style(self, "acrylic")
            pywinstyles.change_border_color(self, "#ffffff")
            pywinstyles.change_header_color(self, "#000000")
            pywinstyles.change_title_color(self, "#ffffff")
        except Exception:
            pass

        try:
            self.tk.eval("proc bgerror {args} {}")
        except Exception:
            pass

        self.video_path = ""
        base_dir = (
            os.path.dirname(sys.executable)
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )
        self.output_dir = os.path.join(base_dir, "data", "SubFynn_Outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.last_result = None

        self._build_ui()
        if initial_video:
            self.load_video(initial_video)

    def _build_ui(self):
        # 1. Header Glass Card (Ultra-Rounded Pill Card)
        header_frame = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=COLOR_GLASS_CARD,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
        )
        header_frame.pack(fill="x", padx=16, pady=(16, 8))

        top_header_bar = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_header_bar.pack(fill="x", padx=18, pady=(14, 2))

        title_lbl = ctk.CTkLabel(
            top_header_bar,
            text="🎬 SubFynn - โปรแกรมสร้างซับไทยอัตโนมัติ",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        )
        title_lbl.pack(side="left")

        self.web_btn = ctk.CTkButton(
            top_header_bar,
            text="🌐 เปิดโหมด Web App",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=14,
            fg_color="#181826",
            hover_color="#242436",
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            height=30,
            command=self.open_web_mode,
        )
        self.web_btn.pack(side="right", padx=(8, 0))

        badge_lbl = ctk.CTkLabel(
            top_header_bar,
            text="💎 SubFynn Glass Edition",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
            fg_color="#181826",
            corner_radius=14,
            padx=14,
            pady=6,
        )
        badge_lbl.pack(side="right")

        subtitle_lbl = ctk.CTkLabel(
            header_frame,
            text="โหลดวิดีโอจากข้างนอกมาใส่ แล้วสร้างซับไตเติลภาษาไทยอัตโนมัติ พร้อมส่งออกไฟล์ .SRT หรือฝังซับลงวิดีโอ",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED,
        )
        subtitle_lbl.pack(padx=18, pady=(0, 14), anchor="w")

        # 2. File Selection Glass Card
        file_frame = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=COLOR_GLASS_CARD,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
        )
        file_frame.pack(fill="x", padx=16, pady=8)

        file_label = ctk.CTkLabel(
            file_frame,
            text="เลือกไฟล์วิดีโอ:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        )
        file_label.pack(anchor="w", padx=18, pady=(12, 4))

        file_input_box = ctk.CTkFrame(file_frame, fg_color="transparent")
        file_input_box.pack(fill="x", padx=18, pady=(0, 14))

        self.file_entry = ctk.CTkEntry(
            file_input_box,
            placeholder_text="คลิกปุ่ม 'เลือกไฟล์' เพื่อนำเข้าวิดีโอ...",
            font=ctk.CTkFont(size=13),
            corner_radius=14,
            fg_color=COLOR_INPUT_BG,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            placeholder_text_color="#94a3b8",
            height=38,
        )
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = ctk.CTkButton(
            file_input_box,
            text="📁 เลือกไฟล์...",
            width=120,
            height=38,
            corner_radius=14,
            fg_color=COLOR_ACCENT_WHITE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#000000",
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.browse_video,
        )
        browse_btn.pack(side="right")

        # 3. Options Glass Card
        opts_frame = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=COLOR_GLASS_CARD,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
        )
        opts_frame.pack(fill="x", padx=16, pady=8)

        opts_row1 = ctk.CTkFrame(opts_frame, fg_color="transparent")
        opts_row1.pack(fill="x", padx=16, pady=(12, 4))

        # Col 1: Model
        col1 = ctk.CTkFrame(opts_row1, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col1, text="โมเดล Whisper:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(anchor="w")
        self.model_var = ctk.StringVar(value="base")
        self.model_menu = ctk.CTkOptionMenu(
            col1,
            values=[
                "base (แนะนำทั่วไป)",
                "tiny (เร็วสุด)",
                "small (แม่นยำ)",
                "medium (แม่นยำสูง แนะนำ JAV/ญี่ปุ่น)",
                "large-v3 (แม่นยำสูงสุด สำหรับ JAV 18+)",
            ],
            variable=self.model_var,
            corner_radius=14,
            height=34,
            fg_color=COLOR_DROPDOWN_BG,
            button_color="#1c1c28",
            button_hover_color=COLOR_DROPDOWN_HOVER,
            text_color=COLOR_TEXT_WHITE,
            dropdown_fg_color="#08080e",
            dropdown_text_color=COLOR_TEXT_WHITE,
            dropdown_hover_color="#242436",
        )
        self.model_menu.pack(fill="x", pady=(4, 0))

        # Col 2: Translation Style
        col2 = ctk.CTkFrame(opts_row1, fg_color="transparent")
        col2.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col2, text="สไตล์การแปลคำบรรยาย:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(anchor="w")
        self.style_var = ctk.StringVar(value="jav (หนังผู้ใหญ่ 18+ มาตรฐานแฟนซับ)")
        self.style_menu = ctk.CTkOptionMenu(
            col2,
            values=[
                "jav (หนังผู้ใหญ่ 18+ มาตรฐานแฟนซับ)",
                "jav_dirty (หนังผู้ใหญ่ 18+ หยาบคายได้เต็มที่ / Dirty Talk)",
                "jav_hardcore (หนังผู้ใหญ่ 18+ Hardcore ดิบเถื่อน หยาบคายขั้นสุด)",
                "jav_sweet (หนังผู้ใหญ่ 18+ สายหวานอ้อน)",
                "general (ทั่วไป / ภาพยนตร์)",
                "anime (อนิเมะ / การ์ตตอน)",
                "drama (ดราม่า / ซีรีส์)",
            ],
            variable=self.style_var,
            corner_radius=14,
            height=34,
            fg_color=COLOR_DROPDOWN_BG,
            button_color="#1c1c28",
            button_hover_color=COLOR_DROPDOWN_HOVER,
            text_color=COLOR_TEXT_WHITE,
            dropdown_fg_color="#08080e",
            dropdown_text_color=COLOR_TEXT_WHITE,
            dropdown_hover_color="#242436",
        )
        self.style_menu.pack(fill="x", pady=(4, 0))

        opts_row2 = ctk.CTkFrame(opts_frame, fg_color="transparent")
        opts_row2.pack(fill="x", padx=16, pady=(4, 4))

        # Col 3: Language
        col3 = ctk.CTkFrame(opts_row2, fg_color="transparent")
        col3.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col3, text="ภาษาเสียงพูดต้นฉบับ:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(anchor="w")
        self.lang_var = ctk.StringVar(value="ja (ญี่ปุ่น - แนะนำ JAV)")
        self.lang_menu = ctk.CTkOptionMenu(
            col3,
            values=[
                "ja (ญี่ปุ่น - แนะนำ JAV)",
                "auto (ตรวจจับอัตโนมัติ)",
                "en (อังกฤษ)",
                "zh (จีน)",
                "ko (เกาหลี)",
                "th (ไทย)",
            ],
            variable=self.lang_var,
            corner_radius=14,
            height=34,
            fg_color=COLOR_DROPDOWN_BG,
            button_color="#1c1c28",
            button_hover_color=COLOR_DROPDOWN_HOVER,
            text_color=COLOR_TEXT_WHITE,
            dropdown_fg_color="#08080e",
            dropdown_text_color=COLOR_TEXT_WHITE,
            dropdown_hover_color="#242436",
        )
        self.lang_menu.pack(fill="x", pady=(4, 0))

        # Col 4: AI Model
        col4 = ctk.CTkFrame(opts_row2, fg_color="transparent")
        col4.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col4, text="โมเดล AI แปลภาษา:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(anchor="w")
        self.gemini_model_var = ctk.StringVar(value="gemini-2.5-flash (แนะนำ เร็ว ฉลาด)")
        self.gemini_model_menu = ctk.CTkOptionMenu(
            col4,
            values=[
                "gemini-2.5-flash (แนะนำ เร็ว ฉลาด)",
                "gemini-2.5-pro (แปลได้อารมณ์ลึกซึ้งขั้นสุด)",
                "gemini-2.5-flash-lite (เร็วขั้นสุด ประหยัดโควตา)",
                "gemini-2.0-flash (เสถียร รวดเร็ว)",
                "gemini-2.0-flash-lite (เบา รวดเร็ว)",
                "gemini-1.5-flash (ประหยัดโควตา)",
                "gemini-1.5-pro (ละเอียด แม่นยำ)",
            ],
            variable=self.gemini_model_var,
            corner_radius=14,
            height=34,
            fg_color=COLOR_DROPDOWN_BG,
            button_color="#1c1c28",
            button_hover_color=COLOR_DROPDOWN_HOVER,
            text_color=COLOR_TEXT_WHITE,
            dropdown_fg_color="#08080e",
            dropdown_text_color=COLOR_TEXT_WHITE,
            dropdown_hover_color="#242436",
        )
        self.gemini_model_menu.pack(fill="x", pady=(4, 0))

        opts_row3 = ctk.CTkFrame(opts_frame, fg_color="transparent")
        opts_row3.pack(fill="x", padx=16, pady=(4, 8))

        # Col 5: API Key
        col5 = ctk.CTkFrame(opts_row3, fg_color="transparent")
        col5.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col5, text="Gemini API Key (ไม่บังคับ - ปลดล็อกการแปล 18+ ขั้นสุด):", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(anchor="w")
        self.gemini_entry = ctk.CTkEntry(
            col5,
            placeholder_text="วาง API Key ที่นี่ หรือเว้นว่างไว้เพื่อใช้ระบบโมเดลคลังศัพท์ JAV ฟรีในตัว",
            show="*",
            corner_radius=14,
            fg_color=COLOR_INPUT_BG,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            placeholder_text_color="#94a3b8",
            height=34,
        )
        self.gemini_entry.pack(fill="x", pady=(4, 0))

        # Col 6: Auto Embed Mode
        col6 = ctk.CTkFrame(opts_row3, fg_color="transparent")
        col6.pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col6, text="เอาซับใส่คลิปทันที:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_WHITE).pack(anchor="w")
        self.embed_mode_var = ctk.StringVar(value="burn (ฝังซับติดภาพถาวร)")
        self.embed_mode_menu = ctk.CTkOptionMenu(
            col6,
            values=[
                "burn (ฝังซับติดภาพถาวร)",
                "soft (ฝังซับในไฟล์เร็ว 1 วิ)",
                "both (ทำทั้ง 2 แบบ)",
                "none (เฉพาะไฟล์ .SRT)",
            ],
            variable=self.embed_mode_var,
            corner_radius=14,
            height=34,
            fg_color=COLOR_DROPDOWN_BG,
            button_color="#1c1c28",
            button_hover_color=COLOR_DROPDOWN_HOVER,
            text_color=COLOR_TEXT_WHITE,
            dropdown_fg_color="#08080e",
            dropdown_text_color=COLOR_TEXT_WHITE,
            dropdown_hover_color="#242436",
        )
        self.embed_mode_menu.pack(fill="x", pady=(4, 0))

        # JAV Notice pill banner
        jav_notice_frame = ctk.CTkFrame(
            opts_frame,
            corner_radius=14,
            fg_color="#180e14",
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
        )
        jav_notice_frame.pack(fill="x", padx=16, pady=(4, 12))

        jav_notice = ctk.CTkLabel(
            jav_notice_frame,
            text="🔞 โหมดแปล JAV / หนังผู้ใหญ่ 18+: แปลได้อารมณ์เสียว ฟิน เป็นธรรมชาติ พร้อมตัดเสียงครางวนซ้ำ",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff",
        )
        jav_notice.pack(padx=14, pady=6, anchor="w")

        # 4. Action Glass Card
        action_frame = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=COLOR_GLASS_CARD,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
        )
        action_frame.pack(fill="x", padx=16, pady=8)

        self.start_btn = ctk.CTkButton(
            action_frame,
            text="✨ เริ่มสร้างซับไทย (Generate Thai Subtitles)",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            corner_radius=16,
            fg_color=COLOR_ACCENT_WHITE,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="#000000",
            border_width=2,
            border_color=COLOR_GLASS_BORDER,
            command=self.start_processing,
        )
        self.start_btn.pack(fill="x", padx=18, pady=(14, 8))

        self.progress_bar = ctk.CTkProgressBar(
            action_frame,
            corner_radius=6,
            height=8,
            fg_color="#181824",
            progress_color=COLOR_ACCENT_WHITE,
        )
        self.progress_bar.pack(fill="x", padx=18, pady=(0, 6))
        self.progress_bar.set(0)

        self.status_lbl = ctk.CTkLabel(
            action_frame,
            text="พร้อมทำงาน กรุณาเลือกไฟล์วิดีโอแล้วกดเริ่มสร้างซับ",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_WHITE,
        )
        self.status_lbl.pack(pady=(0, 12))

        # 5. Subtitle Output Glass Card
        out_frame = ctk.CTkFrame(
            self,
            corner_radius=22,
            fg_color=COLOR_GLASS_CARD,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
        )
        out_frame.pack(fill="both", expand=True, padx=16, pady=8)

        top_bar = ctk.CTkFrame(out_frame, fg_color="transparent")
        top_bar.pack(fill="x", padx=18, pady=(12, 6))

        ctk.CTkLabel(
            top_bar,
            text="ผลลัพธ์คำบรรยายซับไทย (.SRT):",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(side="left")

        self.shift_plus_btn = ctk.CTkButton(
            top_bar,
            text="⏩ +0.5s",
            width=75,
            height=28,
            corner_radius=12,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#14141e",
            hover_color="#242436",
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            command=lambda: self.shift_time(0.5),
            state="disabled",
        )
        self.shift_plus_btn.pack(side="right", padx=(6, 0))

        self.shift_minus_btn = ctk.CTkButton(
            top_bar,
            text="⏪ -0.5s",
            width=75,
            height=28,
            corner_radius=12,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#14141e",
            hover_color="#242436",
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            command=lambda: self.shift_time(-0.5),
            state="disabled",
        )
        self.shift_minus_btn.pack(side="right")

        self.srt_textbox = ctk.CTkTextbox(
            out_frame,
            font=ctk.CTkFont(family="Consolas", size=13),
            corner_radius=16,
            fg_color=COLOR_INPUT_BG,
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color="#ffffff",
        )
        self.srt_textbox.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        # Export Buttons Row (Pill-shaped)
        export_box = ctk.CTkFrame(out_frame, fg_color="transparent")
        export_box.pack(fill="x", padx=18, pady=(0, 14))

        self.save_srt_btn = ctk.CTkButton(
            export_box,
            text="💾 บันทึกไฟล์ซับ (.SRT)",
            command=self.save_srt,
            state="disabled",
            width=170,
            height=36,
            corner_radius=14,
            fg_color="#14141e",
            hover_color="#242436",
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.save_srt_btn.pack(side="left", padx=(0, 10))

        self.burn_btn = ctk.CTkButton(
            export_box,
            text="🎬 ฝังซับลงวิดีโอ (Burn-in MP4)",
            command=self.burn_video,
            state="disabled",
            fg_color=COLOR_ACCENT_WHITE,
            hover_color=COLOR_ACCENT_HOVER,
            border_width=2,
            border_color=COLOR_GLASS_BORDER,
            text_color="#000000",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=210,
            height=36,
            corner_radius=14,
        )
        self.burn_btn.pack(side="left", padx=(0, 10))

        self.open_folder_btn = ctk.CTkButton(
            export_box,
            text="📂 เปิดโฟลเดอร์ผลลัพธ์",
            command=self.open_output_folder,
            state="disabled",
            fg_color="#14141e",
            hover_color="#242436",
            border_width=1.5,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=180,
            height=36,
            corner_radius=14,
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
            self.status_lbl.configure(text=f"เลือกไฟล์: {os.path.basename(abs_path)} ({size_mb:.1f} MB)", text_color="white")

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
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกไฟล์วิดีโอที่ถูกต้อง")
            return

        self.video_path = video_file
        model_choice = self.model_var.get().split()[0]
        lang_choice = self.lang_var.get().split()[0]
        style_choice = self.style_var.get().split()[0]
        gemini_model_choice = self.gemini_model_var.get().split()[0]
        gemini_key = self.gemini_entry.get().strip()
        embed_choice = self.embed_mode_var.get().split()[0]

        # Use same directory as input video so user finds their output right next to original video!
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
        self.status_lbl.configure(text="กำลังเริ่มต้นกระบวนการ...", text_color="#38bdf8")

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
        self.status_lbl.configure(text="✅ สร้างซับไทยและนำซับใส่คลิปสำเร็จเรียบร้อย!", text_color="#10b981")

        self.srt_textbox.delete("1.0", "end")
        self.srt_textbox.insert("1.0", res["srt_content"])

        vid_path = res.get("video_output_path") or res.get("burned_video_path") or res.get("softsub_video_path")
        if vid_path and os.path.isfile(vid_path):
            msg = (
                f"สร้างซับไทยและนำซับใส่คลิปเสร็จเรียบร้อยแล้ว!\n\n"
                f"🎬 ไฟล์วิดีโอ: {os.path.basename(vid_path)}\n"
                f"📁 ที่อยู่ไฟล์: {os.path.dirname(vid_path)}\n\n"
                f"ต้องการเปิดโฟลเดอร์ดูไฟล์ทันทีเลยหรือไม่?"
            )
            if messagebox.askyesno("สำเร็จ", msg):
                self.open_output_folder()
        else:
            messagebox.showinfo("สำเร็จ", f"สร้างซับไทยเสร็จแล้ว! ตรวจพบภาษา: {res['detected_language']} ({len(res['segments'])} ท่อน)")

    def open_output_folder(self):
        target_dir = getattr(self, "last_output_dir", self.output_dir)
        if not os.path.isdir(target_dir):
            target_dir = self.output_dir
        if sys.platform == "win32":
            os.startfile(target_dir)
        else:
            subprocess.Popen(["xdg-open", target_dir])

    def open_web_mode(self):
        try:
            from app import start_server_in_background
            import webbrowser
            port = start_server_in_background(port=5000)
            url = f"http://127.0.0.1:{port}"
            webbrowser.open(url)
            self.status_lbl.configure(
                text=f"🌐 เปิด Web App บนเบราว์เซอร์ที่ {url} เรียบร้อยแล้ว",
                text_color="#38bdf8",
            )
        except Exception as e:
            messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเปิด Web App ได้: {e}")

    def _on_error(self, err_msg):
        self.start_btn.configure(state="normal")
        self.progress_bar.set(0.0)
        self.status_lbl.configure(text=f"❌ เกิดข้อผิดพลาด: {err_msg}", text_color="#ef4444")
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
        self.status_lbl.configure(text=f"ปรับเลื่อนเวลาซับ {offset_seconds:+.1f} วินาทีเรียบร้อย", text_color="#38bdf8")

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

        # Write current editor content back to srt before burning
        import time
        current_srt = self.srt_textbox.get("1.0", "end").strip()
        temp_srt = os.path.join(self.output_dir, f"temp_burn_{int(time.time() * 1000)}.srt")
        with open(temp_srt, "w", encoding="utf-8") as f:
            f.write(current_srt)

        self.burn_btn.configure(state="disabled")
        self.status_lbl.configure(text="กำลังฝังซับไตเติลลงวิดีโอด้วย FFmpeg...", text_color="#38bdf8")

        def burn_worker():
            try:
                burn_subtitles_to_video(
                    video_path=self.video_path,
                    srt_path=temp_srt,
                    output_video_path=save_video_path,
                )
                self.after(0, lambda: messagebox.showinfo("สำเร็จ", f"ฝังซับและบันทึกวิดีโอเรียบร้อยแล้วที่:\n{save_video_path}"))
                self.after(0, lambda: self.status_lbl.configure(text="✅ ฝังซับลงวิดีโอเรียบร้อย!", text_color="#10b981"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", f"การฝังซับล้มเหลว:\n{str(e)}"))
                self.after(0, lambda: self.status_lbl.configure(text=f"❌ ฝังซับล้มเหลว: {str(e)}", text_color="#ef4444"))
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
