"""
Build script to compile SubFynn into Windows .exe executable using PyInstaller.
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
    print("Building SubFynn.exe with PyInstaller")
    print("==================================================")

    # 1. Ensure local ffmpeg.exe exists in project root
    local_ffmpeg = os.path.join(PROJECT_DIR, "ffmpeg.exe")
    if not os.path.isfile(local_ffmpeg):
        from engine import find_ffmpeg
        system_ffmpeg = find_ffmpeg()
        print(f"Copying FFmpeg from {system_ffmpeg} ...")
        shutil.copyfile(system_ffmpeg, local_ffmpeg)

    # 2. Run PyInstaller
    spec_file = os.path.join(PROJECT_DIR, "subfynn.spec")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", spec_file]
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_DIR)
    if result.returncode != 0:
        print("[ERROR] PyInstaller compilation failed!")
        sys.exit(result.returncode)

    # 3. Copy ffmpeg.exe & ffprobe.exe directly into dist folder as well
    dist_ffmpeg = os.path.join(DIST_DIR, "ffmpeg.exe")
    if os.path.isfile(local_ffmpeg):
        if not os.path.isfile(dist_ffmpeg) or os.path.getsize(dist_ffmpeg) != os.path.getsize(local_ffmpeg):
            print(f"Copying ffmpeg.exe to {dist_ffmpeg}")
            shutil.copyfile(local_ffmpeg, dist_ffmpeg)

    local_ffprobe = os.path.join(PROJECT_DIR, "ffprobe.exe")
    dist_ffprobe = os.path.join(DIST_DIR, "ffprobe.exe")
    if os.path.isfile(local_ffprobe):
        if not os.path.isfile(dist_ffprobe) or os.path.getsize(dist_ffprobe) != os.path.getsize(local_ffprobe):
            print(f"Copying ffprobe.exe to {dist_ffprobe}")
            shutil.copyfile(local_ffprobe, dist_ffprobe)

    # Copy assets to dist if not present
    dist_assets = os.path.join(DIST_DIR, "assets")
    local_assets = os.path.join(PROJECT_DIR, "assets")
    if os.path.isdir(local_assets) and not os.path.isdir(dist_assets):
        shutil.copytree(local_assets, dist_assets)

    # 4. Create portable ZIP package
    zip_output_base = os.path.join(PROJECT_DIR, "dist", "SubFynn-Windows-Portable")
    print(f"Creating portable package {zip_output_base}.zip ...")
    shutil.make_archive(zip_output_base, "zip", DIST_DIR)
    zip_size_mb = os.path.getsize(f"{zip_output_base}.zip") / (1024 * 1024)
    print(f"Saved portable archive: {zip_output_base}.zip ({zip_size_mb:.1f} MB)")

    print("==================================================")
    print("Build complete!")
    print(f"Output directory: {DIST_DIR}")
    print("   - SubFynn.exe           (Desktop GUI in #23212C theme)")
    print("   - ffmpeg.exe            (FFmpeg Media Processing Engine)")
    print(f"Portable Zip: {zip_output_base}.zip")
    print("==================================================")


if __name__ == "__main__":
    build()
