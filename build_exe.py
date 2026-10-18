"""
Build script to compile SubFynn into Windows .exe executables using PyInstaller.
Usage:
    python build_exe.py
"""

import os
import sys
import shutil
import subprocess

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

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist", "SubFynn")


def build():
    print("==================================================")
    print("🔨 เริ่มต้นการสร้างไฟล์ SubFynn.exe ด้วย PyInstaller")
    print("==================================================")

    # 1. Ensure local ffmpeg.exe exists in project root
    local_ffmpeg = os.path.join(PROJECT_DIR, "ffmpeg.exe")
    if not os.path.isfile(local_ffmpeg):
        from engine import find_ffmpeg
        system_ffmpeg = find_ffmpeg()
        print(f"📋 คัดลอก FFmpeg จาก {system_ffmpeg} ...")
        shutil.copyfile(system_ffmpeg, local_ffmpeg)

    # 2. Run PyInstaller
    spec_file = os.path.join(PROJECT_DIR, "subfynn.spec")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file]
    print(f"🚀 กำลังรันคำสั่ง: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print("❌ การคอมไพล์ล้มเหลว!")
        sys.exit(result.returncode)

    # 3. Copy ffmpeg.exe directly into dist folder as well
    dist_ffmpeg = os.path.join(DIST_DIR, "ffmpeg.exe")
    if os.path.isfile(local_ffmpeg):
        if not os.path.isfile(dist_ffmpeg) or os.path.getsize(dist_ffmpeg) != os.path.getsize(local_ffmpeg):
            print(f"📋 คัดลอก ffmpeg.exe ไปยัง {dist_ffmpeg}")
            shutil.copyfile(local_ffmpeg, dist_ffmpeg)

    # 4. Create portable ZIP package
    zip_output_base = os.path.join(PROJECT_DIR, "dist", "SubFynn-Windows-Portable")
    print(f"📦 กำลังสร้างแพ็กเกจพกพา {zip_output_base}.zip ...")
    shutil.make_archive(zip_output_base, "zip", DIST_DIR)
    zip_size_mb = os.path.getsize(f"{zip_output_base}.zip") / (1024 * 1024)
    print(f"✅ บันทึกแพ็กเกจพกพา: {zip_output_base}.zip ({zip_size_mb:.1f} MB)")

    print("==================================================")
    print("✅ การสร้างไฟล์ SubFynn.exe และแพ็กเกจเสร็จสมบูรณ์เรียบร้อย!")
    print(f"📁 โฟลเดอร์ผลลัพธ์: {DIST_DIR}")
    print("   - SubFynn.exe           (Desktop GUI สไตล์ Glassmorphism Dark)")
    print("   - ffmpeg.exe            (FFmpeg เครื่องมือประมวลผลวิดีโอ/เสียง)")
    print(f"📦 ไฟล์ Zip พกพา: {zip_output_base}.zip")
    print("==================================================")


if __name__ == "__main__":
    build()
