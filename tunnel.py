#!/usr/bin/env python3
"""
SubFynn Studio - Cloudflare Tunnel Launcher.
Exposes the local SubFynn Web App (port 5000) to a public HTTPS URL via Cloudflare Tunnel,
enabling multi-gigabyte (2 GB - 5 GB+) video uploads from anywhere with full local GPU acceleration.
"""

import os
import sys
import time
import re
import subprocess
import webbrowser
import socket
import urllib.request

os.environ["PYTHONUNBUFFERED"] = "1"

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def log(msg=""):
    print(msg, flush=True)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED_BIN = os.path.join(BASE_DIR, "cloudflared.exe")


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def copy_to_clipboard(text: str):
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["clip"],
                input=text.encode("utf-8"),
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
    except Exception:
        pass


def ensure_web_server(port: int = 5000) -> subprocess.Popen:
    if is_port_in_use(port):
        log(f"[*] ตรวจพบ Web App รันอยู่ที่พอร์ต {port} เรียบร้อยแล้ว")
        return None

    log(f"[*] กำลังเริ่มต้น Web App ท้องถิ่นบนพอร์ต {port}...")
    app_py = os.path.join(BASE_DIR, "app.py")
    server_proc = subprocess.Popen(
        [sys.executable, app_py, "--port", str(port), "--no-browser"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait until port 5000 is open
    for _ in range(20):
        if is_port_in_use(port):
            log(f"[+] Web App เริ่มต้นสำเร็จ (http://127.0.0.1:{port})")
            return server_proc
        time.sleep(0.5)

    return server_proc


def main():
    if not os.path.isfile(CLOUDFLARED_BIN):
        log(f"[!] ไม่พบไฟล์ {CLOUDFLARED_BIN}")
        log("    กำลังดาวน์โหลด cloudflared.exe จาก Cloudflare Official...")
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            urllib.request.urlretrieve(download_url, CLOUDFLARED_BIN)
            log("[+] ดาวน์โหลด cloudflared.exe สำเร็จ!")
        except Exception as e:
            log(f"[X] ไม่สามารถดาวน์โหลด cloudflared ได้: {e}")
            sys.exit(1)

    port = 5000
    server_proc = ensure_web_server(port)

    log("[*] กำลังเชื่อมต่อ Cloudflare Tunnel เพื่อสร้าง URL สาธารณะ...")
    tunnel_cmd = [
        CLOUDFLARED_BIN,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
    ]

    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    tunnel_url = None
    start_time = time.time()

    for line in iter(tunnel_proc.stdout.readline, ""):
        m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if m:
            tunnel_url = m.group(0)
            break
        if time.time() - start_time > 30:
            break

    if not tunnel_url:
        log("[X] ไม่สามารถดึง URL จาก Cloudflare Tunnel ได้ กรุณาลองใหม่อีกครั้ง")
        if tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
        sys.exit(1)

    copy_to_clipboard(tunnel_url)

    border = "=" * 72
    log()
    log(border)
    log("  SubFynn Studio - Cloudflare Tunnel (เข้าถึงได้จากทุกที่ทั่วโลก)")
    log(border)
    log("  [+] ลิงก์ Web App สาธารณะของคุณ (HTTPS):")
    log(f"      -> {tunnel_url}")
    log(border)
    log("  * รองรับการอัปโหลดไฟล์วิดีโอขนาดใหญ่ (2 GB - 5 GB+) ผ่านเน็ตได้ทันที")
    log("  * แชร์ลิงก์นี้ให้เพื่อน หรือเปิดจากมือถือ/แท็บเล็ต/คอมเครื่องอื่นได้เลย")
    log("  * ลิงก์ถูกคัดลอกลง Clipboard แล้ว และกำลังเปิดเบราว์เซอร์อัตโนมัติ")
    log("  * กด Ctrl+C ในหน้าต่างนี้เมื่อต้องการปิดการแชร์ Tunnel")
    log(border)
    log()

    try:
        webbrowser.open(tunnel_url)
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            if tunnel_proc.poll() is not None:
                log("[!] Cloudflare Tunnel หยุดทำงาน")
                break
    except KeyboardInterrupt:
        log("\n[*] กำลังปิด Cloudflare Tunnel และ Web App...")
    finally:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
        log("[+] ปิดเรียบร้อยแล้ว ขอบคุณที่ใช้งาน SubFynn Studio ครับ")


if __name__ == "__main__":
    main()
