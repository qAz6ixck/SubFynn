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
# Liquid Glassmorphism Palette (Deep Obsidian & Glowing Accents)
# ==========================================
COLOR_BG = "#0C0B1C"
COLOR_GLASS_CARD = "#211D4A"
COLOR_GLASS_BORDER = "#514C85"
COLOR_GLASS_BORDER_TOP = "#766FC0"
COLOR_INPUT_BG = "#14152E"
COLOR_DROPDOWN_BG = "#28264D"
COLOR_DROPDOWN_HOVER = "#39366E"
COLOR_TEXT_WHITE = "#F8FAFC"          # Crisp bright white text
COLOR_TEXT_MUTED = "#B4B2D2"
COLOR_TEXT_DIM = "#9290B7"
COLOR_ACCENT_INDIGO = "#6B65F1"
COLOR_ACCENT_INDIGO_HOVER = "#807AF8"
COLOR_ACCENT_PINK = "#C45FC1"
COLOR_ACCENT_PINK_HOVER = "#D975D4"
COLOR_ACCENT_CYAN = "#52CDE7"
COLOR_ACCENT_CYAN_BG = "#172F53"
COLOR_ACCENT_EMERALD = "#35C9A2"
COLOR_ACCENT_EMERALD_BG = "#173B4B"

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
            pywinstyles.change_border_color(self, COLOR_GLASS_BORDER)
            pywinstyles.change_header_color(self, COLOR_BG)
            pywinstyles.change_title_color(self, COLOR_TEXT_WHITE)
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
        self.geometry("1080x900")
        self.minsize(900, 760)

        page = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLOR_GLASS_BORDER,
            scrollbar_button_hover_color=COLOR_GLASS_BORDER_TOP,
        )
        page.pack(fill="both", expand=True, padx=6, pady=6)

        def make_card(parent=page):
            return ctk.CTkFrame(
                parent,
                corner_radius=22,
                fg_color=COLOR_GLASS_CARD,
                border_width=1,
                border_color=COLOR_GLASS_BORDER,
            )

        # Header mirrors the Web App's brand and status row.
        header = make_card()
        header.pack(fill="x", padx=14, pady=(12, 10))
        header_row = ctk.CTkFrame(header, fg_color="transparent")
        header_row.pack(fill="x", padx=22, pady=(18, 4))

        brand = ctk.CTkFrame(header_row, fg_color="transparent")
        brand.pack(side="left", fill="x", expand=True)
        brand_mark = ctk.CTkLabel(
            brand,
            text="SF",
            width=48,
            height=48,
            corner_radius=15,
            fg_color="#7055C8",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=17, weight="bold"),
        )
        brand_mark.pack(side="left", padx=(0, 14))

        title_group = ctk.CTkFrame(brand, fg_color="transparent")
        title_group.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(
            title_group,
            text="SubFynn Studio",
            font=ctk.CTkFont(size=23, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_group,
            text="โปรแกรมสร้างซับไทยอัตโนมัติ (AI Thai Subtitle Generator)",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        header_tools = ctk.CTkFrame(header_row, fg_color="transparent")
        header_tools.pack(side="right", padx=(12, 0))
        ctk.CTkLabel(
            header_tools,
            text="● Engine Ready",
            corner_radius=16,
            fg_color="#173C3A",
            text_color="#65DDB4",
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=14,
            pady=7,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            header_tools,
            text="◆ Liquid Glass",
            corner_radius=16,
            fg_color="#25345A",
            text_color="#9FC9FF",
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=14,
            pady=7,
        ).pack(side="left")
        # File selection panel, styled after the Web App drop zone.
        file_card = make_card()
        file_card.pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(
            file_card,
            text="เพิ่มไฟล์วิดีโอ",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(anchor="w", padx=22, pady=(18, 12))

        drop_zone = ctk.CTkFrame(
            file_card,
            corner_radius=19,
            fg_color="#201F4A",
            border_width=1,
            border_color="#5F59A2",
        )
        drop_zone.pack(fill="x", padx=22, pady=(0, 14))
        ctk.CTkLabel(drop_zone, text="🎬", font=ctk.CTkFont(size=34)).pack(pady=(15, 2))
        ctk.CTkLabel(
            drop_zone,
            text="คลิกปุ่มด้านล่างเพื่อเลือกไฟล์วิดีโอ",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(pady=(0, 3))
        ctk.CTkLabel(
            drop_zone,
            text="รองรับ MP4, MKV, MOV, AVI, WEBM, FLV, TS (สูงสุด 2GB)",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED,
        ).pack(pady=(0, 14))

        file_row = ctk.CTkFrame(file_card, fg_color="transparent")
        file_row.pack(fill="x", padx=22, pady=(0, 18))
        self.file_entry = ctk.CTkEntry(
            file_row,
            placeholder_text="ยังไม่ได้เลือกไฟล์วิดีโอ",
            font=ctk.CTkFont(size=13),
            corner_radius=13,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            placeholder_text_color=COLOR_TEXT_DIM,
            height=42,
        )
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        browse_btn = ctk.CTkButton(
            file_row,
            text="📁 เลือกไฟล์...",
            width=142,
            height=42,
            corner_radius=13,
            fg_color="#3A3976",
            hover_color="#4D4B91",
            border_width=1,
            border_color="#7772C2",
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.browse_video,
        )
        browse_btn.pack(side="right")

        # Two-column options grid follows the same reading order as the Web App.
        options_card = make_card()
        options_card.pack(fill="x", padx=14, pady=10)
        options_grid = ctk.CTkFrame(options_card, fg_color="transparent")
        options_grid.pack(fill="x", padx=16, pady=(16, 8))
        options_grid.grid_columnconfigure(0, weight=1, uniform="option-columns")
        options_grid.grid_columnconfigure(1, weight=1, uniform="option-columns")

        self.model_var = ctk.StringVar(value="base")
        self.style_var = ctk.StringVar(value="jav (หนังผู้ใหญ่ 18+ มาตรฐานแฟนซับ)")
        self.gemini_model_var = ctk.StringVar(value="gemini-2.5-flash (แนะนำ เร็ว ฉลาด)")
        self.embed_mode_var = ctk.StringVar(value="burn (ฝังซับติดภาพถาวร)")
        self.lang_var = ctk.StringVar(value="ja (ญี่ปุ่น - แนะนำ JAV)")

        def add_option(row, column, label_text, values, variable):
            field = ctk.CTkFrame(options_grid, fg_color="transparent")
            field.grid(row=row, column=column, sticky="ew", padx=8, pady=9)
            ctk.CTkLabel(
                field,
                text=label_text,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLOR_TEXT_WHITE,
            ).pack(anchor="w", pady=(0, 7))
            menu = ctk.CTkOptionMenu(
                field,
                values=values,
                variable=variable,
                corner_radius=12,
                height=40,
                fg_color=COLOR_DROPDOWN_BG,
                button_color="#403E79",
                button_hover_color="#56539A",
                text_color=COLOR_TEXT_WHITE,
                dropdown_fg_color=COLOR_INPUT_BG,
                dropdown_text_color=COLOR_TEXT_WHITE,
                dropdown_hover_color="#3A376B",
                font=ctk.CTkFont(size=13),
                dropdown_font=ctk.CTkFont(size=13),
            )
            menu.pack(fill="x")
            return menu

        self.model_menu = add_option(0, 0, "ขนาดโมเดล Whisper (AI Speech-to-Text)", [
            "base (แนะนำทั่วไป)", "tiny (เร็วสุด)", "small (แม่นยำ)",
            "medium (แม่นยำสูง แนะนำ JAV/ญี่ปุ่น)", "large-v3 (แม่นยำสูงสุด สำหรับ JAV 18+)",
        ], self.model_var)
        # Keep the backend's expected model value while showing the friendly label.
        self.model_var.set("base")
        self.style_menu = add_option(0, 1, "สไตล์การแปลคำบรรยาย", [
            "jav (หนังผู้ใหญ่ 18+ มาตรฐานแฟนซับ)",
            "jav_dirty (หนังผู้ใหญ่ 18+ หยาบคายได้เต็มที่ / Dirty Talk)",
            "jav_hardcore (หนังผู้ใหญ่ 18+ Hardcore ดิบเถื่อน หยาบคายขั้นสุด)",
            "jav_sweet (หนังผู้ใหญ่ 18+ สายหวานอ้อน)", "general (ทั่วไป / ภาพยนตร์)",
            "anime (อนิเมะ / การ์ตูน)", "drama (ดราม่า / ซีรีส์)",
        ], self.style_var)
        self.gemini_model_menu = add_option(1, 0, "โมเดล AI แปลภาษา (Translation Model)", [
            "gemini-2.5-flash (แนะนำ เร็ว ฉลาด)",
            "gemini-2.5-pro (แปลได้อารมณ์ลึกซึ้งขั้นสุด)",
            "gemini-2.5-flash-lite (เร็วขั้นสุด ประหยัดโควตา)",
            "gemini-2.0-flash (เสถียร รวดเร็ว)", "gemini-2.0-flash-lite (เบา รวดเร็ว)",
            "gemini-1.5-flash (ประหยัดโควตา)", "gemini-1.5-pro (ละเอียด แม่นยำ)",
        ], self.gemini_model_var)
        self.embed_mode_menu = add_option(1, 1, "เอาซับใส่คลิปวิดีโอทันที (Auto-embed)", [
            "burn (ฝังซับติดภาพถาวร)", "soft (ฝังซับในไฟล์เร็ว 1 วิ)",
            "both (ทำทั้ง 2 แบบ)", "none (เฉพาะไฟล์ .SRT)",
        ], self.embed_mode_var)
        self.lang_menu = add_option(2, 0, "ภาษาเสียงพูดต้นฉบับ", [
            "ja (ญี่ปุ่น - แนะนำ JAV)", "auto (ตรวจจับอัตโนมัติ)", "en (อังกฤษ)",
            "zh (จีน)", "ko (เกาหลี)", "th (ไทย)",
        ], self.lang_var)

        api_field = ctk.CTkFrame(options_grid, fg_color="transparent")
        api_field.grid(row=2, column=1, sticky="ew", padx=8, pady=9)
        ctk.CTkLabel(
            api_field,
            text="Google Gemini API Key (ไม่บังคับ)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(anchor="w", pady=(0, 7))
        self.gemini_entry = ctk.CTkEntry(
            api_field,
            placeholder_text="วาง API Key หรือเว้นว่างเพื่อใช้ระบบแปลฟรี",
            show="*",
            corner_radius=12,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            placeholder_text_color=COLOR_TEXT_DIM,
            height=40,
            font=ctk.CTkFont(size=13),
        )
        self.gemini_entry.pack(fill="x")

        jav_notice = ctk.CTkFrame(
            options_card,
            corner_radius=14,
            fg_color="#30204A",
            border_width=1,
            border_color="#7953A5",
        )
        jav_notice.pack(fill="x", padx=24, pady=(8, 18))
        ctk.CTkLabel(
            jav_notice,
            text="🔞 โหมดแปล JAV / หนังผู้ใหญ่ 18+: แปลเป็นธรรมชาติ พร้อมตัดเสียงครางวนซ้ำ",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#E4B5FF",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=14, pady=10)

        # Primary action and progress status.
        action_card = make_card()
        action_card.pack(fill="x", padx=14, pady=10)
        self.start_btn = ctk.CTkButton(
            action_card,
            text="✨ เริ่มสร้างซับไทย (Generate Thai Subtitles)",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=52,
            corner_radius=15,
            fg_color="#6659E8",
            hover_color="#7A6CF2",
            text_color="#FFFFFF",
            border_width=1,
            border_color="#A59AFF",
            command=self.start_processing,
        )
        self.start_btn.pack(fill="x", padx=22, pady=(18, 10))
        self.progress_bar = ctk.CTkProgressBar(
            action_card,
            corner_radius=6,
            height=9,
            fg_color="#15182E",
            progress_color=COLOR_ACCENT_CYAN,
        )
        self.progress_bar.pack(fill="x", padx=22, pady=(0, 8))
        self.progress_bar.set(0)
        self.status_lbl = ctk.CTkLabel(
            action_card,
            text="พร้อมทำงาน กรุณาเลือกไฟล์วิดีโอแล้วกดเริ่มสร้างซับ",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED,
            wraplength=980,
        )
        self.status_lbl.pack(padx=18, pady=(0, 16))

        # Output editor and export actions.
        out_card = make_card()
        out_card.pack(fill="both", expand=True, padx=14, pady=(10, 16))
        out_header = ctk.CTkFrame(out_card, fg_color="transparent")
        out_header.pack(fill="x", padx=20, pady=(17, 10))
        ctk.CTkLabel(
            out_header,
            text="🎬 ตัวอย่างวิดีโอและคำบรรยายซับไทย (.SRT)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLOR_TEXT_WHITE,
        ).pack(side="left")
        self.shift_plus_btn = ctk.CTkButton(
            out_header,
            text="⏩ +0.5s",
            width=82,
            height=32,
            corner_radius=11,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2B3154",
            hover_color="#3D4774",
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            command=lambda: self.shift_time(0.5),
            state="disabled",
        )
        self.shift_plus_btn.pack(side="right", padx=(7, 0))
        self.shift_minus_btn = ctk.CTkButton(
            out_header,
            text="⏪ -0.5s",
            width=82,
            height=32,
            corner_radius=11,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2B3154",
            hover_color="#3D4774",
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            command=lambda: self.shift_time(-0.5),
            state="disabled",
        )
        self.shift_minus_btn.pack(side="right")
        self.srt_textbox = ctk.CTkTextbox(
            out_card,
            font=ctk.CTkFont(family="Consolas", size=14),
            corner_radius=15,
            fg_color=COLOR_INPUT_BG,
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
        )
        self.srt_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        export_row = ctk.CTkFrame(out_card, fg_color="transparent")
        export_row.pack(fill="x", padx=20, pady=(0, 18))
        self.save_srt_btn = ctk.CTkButton(
            export_row,
            text="💾 บันทึกไฟล์ซับ (.SRT)",
            command=self.save_srt,
            state="disabled",
            width=185,
            height=40,
            corner_radius=12,
            fg_color="#2B3154",
            hover_color="#3D4774",
            border_width=1,
            border_color=COLOR_GLASS_BORDER,
            text_color=COLOR_TEXT_WHITE,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.save_srt_btn.pack(side="left", padx=(0, 10))
        self.burn_btn = ctk.CTkButton(
            export_row,
            text="🎬 ฝังซับลงวิดีโอ (Burn-in MP4)",
            command=self.burn_video,
            state="disabled",
            fg_color=COLOR_ACCENT_PINK,
            hover_color=COLOR_ACCENT_PINK_HOVER,
            border_width=1,
            border_color="#D49BC7",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=230,
            height=40,
            corner_radius=12,
        )
        self.burn_btn.pack(side="left", padx=(0, 10))
        self.open_folder_btn = ctk.CTkButton(
            export_row,
            text="📂 เปิดโฟลเดอร์ผลลัพธ์",
            command=self.open_output_folder,
            state="disabled",
            fg_color=COLOR_ACCENT_EMERALD_BG,
            hover_color="#185744",
            border_width=1,
            border_color=COLOR_ACCENT_EMERALD,
            text_color="#76E4B9",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=190,
            height=40,
            corner_radius=12,
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
