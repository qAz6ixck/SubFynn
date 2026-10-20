"""
SubFynn Release Build Orchestrator
Compiles React frontend, builds standalone Tauri desktop executable, and generates portable release package.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_TAURI = PROJECT_ROOT / "src-tauri"


def run_cmd(cmd, cwd=PROJECT_ROOT, env=None):
    cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd
    print(f"\n>>> Running: {cmd_str} (in {cwd})")
    full_env = os.environ.copy()
    # Ensure Cargo / Rustup bin directory is in PATH
    cargo_bin = str(Path.home() / ".cargo" / "bin")
    if cargo_bin not in full_env.get("PATH", ""):
        full_env["PATH"] = f"{cargo_bin};{full_env.get('PATH', '')}"
    if env:
        full_env.update(env)

    res = subprocess.run(cmd, cwd=cwd, env=full_env, shell=isinstance(cmd, str))
    if res.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {res.returncode}: {cmd_str}")
    return res


def build():
    print("=" * 60)
    print("SubFynn Standalone Release Build Orchestration")
    print("=" * 60)

    # 1. Build React + Vite Frontend
    print("\n[Step 1/3] Building React + Vite Frontend (pnpm build) ...")
    run_cmd(["pnpm", "build"])

    # 2. Build Tauri v2 Release Binary
    print("\n[Step 2/3] Building Standalone Tauri Desktop Executable ...")
    run_cmd(["npx", "--yes", "@tauri-apps/cli", "build", "--no-bundle"])

    # Verify release binary exists
    release_dir = SRC_TAURI / "target" / "release"
    canonical_exe = release_dir / "SubFynn.exe"
    lowercase_exe = release_dir / "subfynn.exe"

    if lowercase_exe.is_file() and not canonical_exe.is_file():
        print(f"Renaming/Copying {lowercase_exe.name} -> {canonical_exe.name}")
        shutil.copy2(lowercase_exe, canonical_exe)

    if not canonical_exe.is_file():
        raise FileNotFoundError(f"Expected release binary not found at {canonical_exe}")

    print(f"Verified release binary: {canonical_exe} ({canonical_exe.stat().st_size:,} bytes)")

    # 3. Package Portable Release ZIP
    print("\n[Step 3/3] Packaging Standalone Portable Release ZIP ...")
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    import package_portable
    zip_path = package_portable.package_portable()

    print("\n" + "=" * 60)
    print("ALL RELEASE ARTIFACTS BUILT AND PACKAGED SUCCESSFULLY")
    print(f"Binary:   {canonical_exe}")
    print(f"Package:  {zip_path}")
    print("=" * 60)


if __name__ == "__main__":
    build()
