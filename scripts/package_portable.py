"""
SubFynn Standalone Portable Release Packaging Script
Milestone 6: Standalone Packaging, Icon Embedding & FFmpeg Bundling

Packages:
- SubFynn.exe (Tauri v2 Desktop Host with embedded icon)
- ffmpeg.exe and ffprobe.exe (Bundled media processors)
- engine_sidecar.py and engine.py (Python processing sidecar)
- requirements.txt and requirements-local.txt (Sidecar dependencies)
- assets/ (Icons, splashscreen logos, preview assets)
into dist/SubFynn-Windows-Portable.zip.
"""

import os
import sys
import shutil
import zipfile
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
STAGING_DIR = DIST_DIR / "SubFynn-Portable"
ZIP_OUTPUT = DIST_DIR / "SubFynn-Windows-Portable.zip"


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def find_subfynn_binary() -> Path:
    release_dir = PROJECT_ROOT / "src-tauri" / "target" / "release"
    candidates = [
        release_dir / "SubFynn.exe",
        release_dir / "subfynn.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            # If subfynn.exe found but SubFynn.exe doesn't exist, create SubFynn.exe
            subfynn_canonical = release_dir / "SubFynn.exe"
            if candidate != subfynn_canonical and not subfynn_canonical.is_file():
                shutil.copy2(candidate, subfynn_canonical)
            return subfynn_canonical
    raise FileNotFoundError(
        f"Could not find compiled SubFynn binary in {release_dir}. "
        "Run 'npx @tauri-apps/cli build --no-bundle' first."
    )


def package_portable():
    print("=" * 60)
    print("SubFynn Standalone Portable Release Packager")
    print("=" * 60)

    # 1. Ensure dist directory exists
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Clean and create staging directory
    if STAGING_DIR.exists():
        print(f"Cleaning previous staging directory: {STAGING_DIR}")
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Locate compiled SubFynn.exe
    subfynn_exe = find_subfynn_binary()
    print(f"[1/5] Located desktop binary: {subfynn_exe} ({subfynn_exe.stat().st_size:,} bytes)")
    dest_exe = STAGING_DIR / "SubFynn.exe"
    shutil.copy2(subfynn_exe, dest_exe)

    # 4. Copy FFmpeg binaries
    ffmpeg_exe = PROJECT_ROOT / "ffmpeg.exe"
    ffprobe_exe = PROJECT_ROOT / "ffprobe.exe"

    if not ffmpeg_exe.is_file():
        raise FileNotFoundError(f"Missing ffmpeg.exe at {ffmpeg_exe}")
    if not ffprobe_exe.is_file():
        raise FileNotFoundError(f"Missing ffprobe.exe at {ffprobe_exe}")

    print(f"[2/5] Copying ffmpeg.exe ({ffmpeg_exe.stat().st_size:,} bytes) ...")
    shutil.copy2(ffmpeg_exe, STAGING_DIR / "ffmpeg.exe")

    print(f"[2/5] Copying ffprobe.exe ({ffprobe_exe.stat().st_size:,} bytes) ...")
    shutil.copy2(ffprobe_exe, STAGING_DIR / "ffprobe.exe")

    # 5. Copy Python sidecar engine and requirements
    print("[3/5] Copying Python sidecar and dependencies ...")
    for filename in ["engine_sidecar.py", "engine.py", "requirements.txt", "requirements-local.txt", "README.md"]:
        src = PROJECT_ROOT / filename
        if src.is_file():
            shutil.copy2(src, STAGING_DIR / filename)
            print(f"      + {filename}")

    # 6. Copy assets folder
    print("[4/5] Copying assets/ ...")
    assets_src = PROJECT_ROOT / "assets"
    assets_dest = STAGING_DIR / "assets"
    if assets_src.is_dir():
        shutil.copytree(assets_src, assets_dest)
        print(f"      Copied {len(list(assets_dest.glob('*')))} asset files.")

    # 7. Create ZIP archive
    print(f"[5/5] Compressing into {ZIP_OUTPUT.name} ...")
    if ZIP_OUTPUT.exists():
        ZIP_OUTPUT.unlink()

    # Create zip with SubFynn/ root folder or flat portable folder
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(STAGING_DIR):
            for file in files:
                full_path = Path(root) / file
                archive_relpath = full_path.relative_to(STAGING_DIR)
                # Prefix with SubFynn/ in the zip archive for clean extraction
                zip_entry_path = Path("SubFynn") / archive_relpath
                zf.write(full_path, zip_entry_path.as_posix())

    zip_size_bytes = ZIP_OUTPUT.stat().st_size
    zip_size_mb = zip_size_bytes / (1024 * 1024)
    zip_sha = calculate_sha256(ZIP_OUTPUT)

    print("=" * 60)
    print("PORTABLE RELEASE PACKAGE CREATED SUCCESSFULLY")
    print(f"Output File: {ZIP_OUTPUT}")
    print(f"Package Size: {zip_size_mb:.2f} MB ({zip_size_bytes:,} bytes)")
    print(f"SHA-256:      {zip_sha}")
    print("=" * 60)
    print("Archive Contents:")
    with zipfile.ZipFile(ZIP_OUTPUT, "r") as zf:
        for info in zf.infolist()[:20]:
            print(f"  - {info.filename} ({info.file_size:,} bytes)")
        if len(zf.infolist()) > 20:
            print(f"  ... and {len(zf.infolist()) - 20} more files.")
    print("=" * 60)
    # Clean up staging directory so dist/ remains lean and does not bloat Tauri frontendDist
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        print("Cleaned up staging directory.")
    return str(ZIP_OUTPUT)


if __name__ == "__main__":
    package_portable()
