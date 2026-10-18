# AI Thai Subtitle Generator (โปรแกรมสร้างซับไทยอัตโนมัติ) 🎬🇹🇭

โปรแกรมสร้างคำบรรยายภาษาไทย (ซับไทย) อัตโนมัติสำหรับวิดีโอที่คุณดาวน์โหลดมาจากข้างนอก เพียงแค่อัปโหลดไฟล์วิดีโอ ระบบจะทำการแยกเสียง ถอดเสียงด้วย AI (Whisper) แปลงเป็นภาษาไทยที่สละสลวย และสร้างไฟล์ซับไตเติล (.SRT, .VTT) หรือฝังซับลงในวิดีโอ (Burn-in MP4) ให้ทันที

---

## ✨ จุดเด่นของโปรแกรม

1. **ใช้งานง่าย มี 2 รูปแบบให้เลือกตามความถนัด**:
   - **Web App (แนะนำ)**: เปิดในเว็บเบราว์เซอร์ ลากและวางไฟล์ (Drag & Drop) พร้อมแถบแสดงเปอร์เซ็นต์อัปโหลด มี Video Player เล่นวิดีโอพร้อมซิงก์ไฮไลท์ซับไทยตามเสียงพูดแบบเรียลไทม์ และแก้ไขข้อความซับไตเติลในตารางได้ทันที
   - **Desktop GUI**: หน้าต่างโปรแกรม Windows สวยงาม สไตล์ Dark Mode พัฒนาด้วย CustomTkinter
   - **CLI**: รองรับการสั่งงานผ่าน Command Line สำหรับผู้ที่ต้องการประมวลผลวิดีโอแบบแบทช์
2. **ระบบถอดเสียง AI ระดับโลก**:
   - ใช้โมเดล **faster-whisper** ทำงานบนเครื่องของคุณโดยตรง (ออฟไลน์) ประมวลผลรวดเร็ว ไม่กินแรม
   - รองรับขนาดโมเดล: `tiny` (เร็วที่สุด), `base` (แนะนำทั่วไป), `small` (แม่นยำปานกลาง), `medium` (แม่นยำสูง แนะนำสำหรับ JAV/ญี่ปุ่น), `large-v3` (แม่นยำสูงสุด ถอดเสียงกระซิบ/เสียงครางชัดเจน)
   - แสดงความคืบหน้าการถอดเสียงแบบเรียลไทม์ (วินาทีต่อวินาที)
3. **ระบบแปลภาษาไทย และโหมดแปล JAV / หนังผู้ใหญ่ 18+ แบบได้อารมณ์ขั้นสุด**:
   - **🔞 โหมด JAV / 18+ (แปลได้อารมณ์ เร่าร้อน เสียว เป็นธรรมชาติ)**: แก้ปัญหาซับไตเติลแปลตรงตัวทื่อๆ ปรับคำพูดและเสียงครวญครางให้อินเนอร์มาเต็ม (เช่น แปล `気持ちいい` เป็น `เสียวจัง/เสียวมาก`, แปล `いく` เป็น `จะเสร็จแล้ว/จะแตกแล้ว`, แปล `ダメ` เป็น `อย่านะ`, แปล `奥まで` เป็น `ลึกจัง/มิดด้าม`, แปล `中に出して` เป็น `แตกในเลย`)
   - **💥 โหมดแปลสายดุดัน / หยาบคายได้เต็มที่ (Raw & Vulgar Dirty Talk)**: สไตล์ `jav_dirty`, `jav_hardcore`, `jav_vulgar` ปลดปล่อยถ้อยคำลามก ดิบ เถื่อน ถึงพริกถึงขิง แบบไม่มีการเซนเซอร์ (ควย, หี, รูร่าน, เย็ด, ซอยยับ, แตกใน, น้ำเงี่ยน, เสียวชิบหาย)
   - **ระบบป้องกันเสียงครางวนซ้ำ (Anti-Hallucination Moan Filter)**: ปรับแต่ง Repetition Penalty และ Silence Threshold ป้องกันไม่ให้ AI วนลูปเสียงครางเดิมซ้ำๆ
   - **โหมดแปลฟรี (ไม่ต้องใช้ API Key)**: ใช้งาน JAV Slang & Erotic Lexicon Engine ช่วยปรับแก้สำนวนแปลอัตโนมัติให้ได้อารมณ์ทันที
   - **โหมด Gemini AI เวอร์ชันล่าสุด (Gemini 2.5 Pro / Flash / Flash-Lite / 2.0)**: รองรับโมเดลเรือธง `gemini-2.5-pro` (วิเคราะห์และแปลภาษา 18+ ได้สมจริงลึกซึ้งขั้นสุด), `gemini-2.5-flash` (เร็วและแม่นยำ), `gemini-2.5-flash-lite` (ความเร็วสูงสุด) พร้อมปิดกั้นตัวกรอง (`BLOCK_NONE` ทุกหมวดหมู่) แปลได้อย่างอิสระไม่ถูกบล็อก
4. **เครื่องมือปรับแต่งเวลาซับ (Subtitle Time Shift)**:
   - ปรับเลื่อนเวลาซับไตเติลเร็วขึ้นหรือช้าลงได้ง่ายๆ (`-0.5s`, `+0.5s` หรือกำหนดเอง) ทั้งบน Web UI, Desktop GUI และ CLI
5. **ระบบส่งออกและเอาซับใส่คลิปให้อัตโนมัติ (Auto-Embed Subtitle to Video)**:
   - **⚡ Fast Softsub (`soft`)**: นำซับไตเติลไปฝังลงในคอนเทนเนอร์วิดีโอทันที ใช้เวลาเพียง 1-2 วินาที ด้วย FFmpeg stream copy (`mov_text` / `srt`) ไม่เสียคุณภาพวิดีโอ เปิด-ปิดซับไตเติลได้
   - **🎬 Hardsub Burn-in (`burn`)**: ฝังซับติดภาพถาวร ฟอนต์ Leelawadee UI คมชัด อ่านง่าย สีขาวขอบดำ
   - ดาวน์โหลดไฟล์ `.SRT` และ `.VTT` ได้โดยตรง
   - วิดีโอพร้อมซับจะถูกสร้างและส่งออกพร้อมให้รับชมได้ทันทีโดยไม่ต้องไปแปลงไฟล์เองซ้ำซ้อน

---

## 📦 ใช้งานแบบไฟล์ .EXE (ไม่ต้องติดตั้ง Python)

โปรแกรมได้รับการคอมไพล์เป็นไฟล์ Windows `.exe` แบบ Standalone สำเร็จรูป อยู่ในโฟลเดอร์ `dist/ThaiSubtitles/` และแพ็กเกจพกพา `dist/ThaiSubtitles-Windows-Portable.zip`:

### 1. โหมด Desktop GUI (แนะนำสำหรับผู้ใช้ทั่วไป):
ดับเบิลคลิกไฟล์:
```
dist\ThaiSubtitles\ThaiSubtitles.exe
```
หรือดับเบิลคลิกไฟล์ `ThaiSubtitles.bat` / `start_gui.bat` ที่โฟลเดอร์หลัก
> - หน้าต่างโปรแกรมแบบ Dark Mode จะเปิดขึ้นมาทันที
> - **รองรับ Drag & Drop**: สามารถลากไฟล์วิดีโอจาก Windows Explorer มาปล่อยใส่ไอคอน `ThaiSubtitles.exe` เพื่อเปิดโปรแกรมพร้อมโหลดไฟล์วิดีโอนั้นทันที
> - รองรับการเลือกโมเดล AI (`tiny`, `base`, `small`) ถอดเสียง และแปลเป็นภาษาไทย
> - มีปุ่ม **"🌐 เปิดโหมด Web App"** ที่มุมขวาบนเพื่อสลับไปใช้ในเบราว์เซอร์ พร้อมระบบสแกนพอร์ตอัตโนมัติป้องกันพอร์ตชน

### 2. โหมด Web App (สำหรับผู้ที่ต้องการ Video Player + Subtitle Editor ในเว็บ):
ดับเบิลคลิกไฟล์:
```
dist\ThaiSubtitles\ThaiSubtitles-Web.exe
```
หรือดับเบิลคลิก `start_web.bat`
> ระบบจะเปิดหน้าต่างคอนโซลแสดงสถานะเซิร์ฟเวอร์ และเปิดเว็บเบราว์เซอร์ไปที่ `http://127.0.0.1:5000` โดยอัตโนมัติ (หากพอร์ต 5000 ถูกใช้งานอยู่ ระบบจะสลับไปพอร์ตถัดไปโดยอัตโนมัติ)

### 3. โหมด Command-Line (CLI):
```bash
dist\ThaiSubtitles\ThaiSubtitles-CLI.exe video.mp4 --burn
```

### 🔨 วิธีบิลด์ไฟล์ .EXE ใหม่ด้วยตัวเอง
หากมีการแก้ไขโค้ด สามารถรันคำสั่งบิลด์ใหม่และสร้างไฟล์ Zip พกพาได้ทันทีด้วย:
```bash
python build_exe.py
```

---

## 🚀 วิธีเปิดใช้งานโปรแกรม (ผ่าน Python Source Code)

### วิธีที่ 1: เปิดใช้งาน Web App (แนะนำ)
ดับเบิลคลิกไฟล์:
```
start_web.bat
```
หรือรันผ่าน Terminal:
```bash
python app.py
```
> ระบบจะเปิดเว็บเบราว์เซอร์ขึ้นมาที่ `http://127.0.0.1:5000` โดยอัตโนมัติ

---

### วิธีที่ 2: เปิดใช้งาน Desktop GUI
ดับเบิลคลิกไฟล์:
```
start_gui.bat
```
หรือรันผ่าน Terminal:
```bash
python gui.py
```

---

### วิธีที่ 3: ใช้งานผ่าน Command-line (CLI)
```bash
# สร้างซับไทยสำหรับวิดีโอทั่วไป
python cli.py video.mp4

# แปล JAV / หนังผู้ใหญ่ 18+ (ใช้โมเดล medium ถอดเสียงญี่ปุ่นคมชัด พร้อมแปลได้อารมณ์)
python cli.py jav_video.mp4 --style jav --lang ja --model medium

# แปล JAV สไตล์ดุดัน (Dirty Talk) หรือสไตล์หวานอ้อน (Sweet)
python cli.py jav_video.mp4 --style jav_dirty --lang ja --model medium
python cli.py jav_video.mp4 --style jav_sweet --lang ja --model medium

# แปล JAV ด้วยโมเดล large-v3 และฝังซับลงวิดีโอทันที
python cli.py jav_video.mp4 --style jav --lang ja --model large-v3 --burn

# แปล JAV ด้วย Gemini AI 18+ ขั้นสุด (โมเดล gemini-2.5-pro หรือ gemini-2.5-flash ปลดล็อกตัวกรองผู้ใหญ่)
python cli.py jav_video.mp4 --style jav_dirty --gemini-model gemini-2.5-pro --gemini-key "YOUR_GEMINI_KEY"
```

---

## 🛠 โครงสร้างโปรเจกต์

```
d:\MyProject\subdev\
├── engine.py           # แกนกลางประมวลผล (FFmpeg Audio Extraction, Whisper STT, Thai Translation, Burn-in)
├── app.py              # เซิร์ฟเวอร์ Web Application พร้อม Video Player และ Subtitle Editor
├── gui.py              # หน้าต่าง Desktop Application (CustomTkinter)
├── cli.py              # คำสั่ง CLI สำหรับการประมวลผล
├── test_engine.py      # ชุดทดสอบอัตโนมัติสำหรับโมดูล engine (Unit & Integration Tests)
├── test_app.py         # ชุดทดสอบอัตโนมัติสำหรับ Web API & Streaming
├── test_gui_and_main.py # ชุดทดสอบอัตโนมัติสำหรับ GUI และ Routing
├── ThaiSubtitles.bat   # ทางลัดเปิด Desktop GUI แบบรัน Exe ทันที
├── start_web.bat       # ทางลัดเปิด Web App ในคลิกเดียว
├── start_gui.bat       # ทางลัดเปิด Desktop GUI ในคลิกเดียว
└── data/               # โฟลเดอร์เก็บไฟล์วิดีโอที่อัปโหลดและผลลัพธ์
```

---

## 🧪 การทดสอบระบบ (Verification)

สามารถรันชุดทดสอบความถูกต้องทั้งหมด (41 รายการ) ได้ด้วยคำสั่ง:
```bash
python -m unittest discover -v
```
ครอบคลุมการทดสอบ:
- การแปลงเวลา Timestamp (HH:MM:SS,mmm และ HH:MM:SS.mmm)
- การตรวจจับภาษาไทย
- การสร้างรูปแบบ .SRT และ .VTT
- การปรับเลื่อนเวลาซับไตเติล (Subtitle Timestamp Shifting)
- การแปลภาษาไทยแบบกลุ่มและป้องกันคำบรรยายสลับบรรทัด (Multiline Translation Alignment)
- การตรวจสอบแทร็กเสียงในวิดีโอ (Audio Stream Detection)
- การแยกเสียง (Audio Extraction) และการจัดการวิดีโอที่ไม่มีเสียง
- การฝังซับไตเติลลงวิดีโอ (Hardsub Burn-in) รวมถึงกรณีชื่อไฟล์มีช่องว่าง วงเล็บ และภาษาไทย
- ระบบถอดเสียงและทดสอบความปลอดภัย CUDA GPU Auto-Probe (ตรวจจับการขาดหายของ DLL บน Windows แล้วสลับใช้ CPU อย่างปลอดภัยโดยไม่ค้าง)
- ระบบแปลภาษา JAV แฟนซับ (Standard, Dirty Talk, Sweet) การแทนที่สำนวนลามก และการคงความหมายปฏิเสธ (Negation Preservation)
- ระบบแปลด้วย Gemini AI Structured JSON, Safety Block Bypass (`BLOCK_NONE`) และ Automatic Fallback Chain
- การทำงานของ Web Endpoints (Upload streaming, Process, Progress polling, Range requests, Shift subtitles, Dynamic Port Fallback)
- การทำงานของ Desktop GUI และ Routing (การเปิด GUI ด้วยการ Drag & Drop ไฟล์วิดีโอ, การสลับโหมด CLI/Web)
