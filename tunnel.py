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
import threading
import webbrowser
import socket
import urllib.request

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
        print(f"[*] ตรวจพบ Web App รันอยู่ที่พอร์ต {port} เรียบร้อยแล้ว")
        return None

    print(f"[*] กำลังเริ่มต้น Web App ท้องถิ่นบนพอร์ต {port}...")
    app_py = os.path.join(BASE_DIR, "app.py")
    server_proc = subprocess.Popen(
        [sys.executable, app_py, "--port", str(port), "--no-browser"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait until port 5000 is open
    for _ in range(20):
        if is_port_in_use(port):
            print(f"[+] Web App เริ่มต้นสำเร็จ (http://127.0.0.1:{port})")
            return server_proc
        time.sleep(0.5)

    return server_proc


def main():
    if not os.path.isfile(CLOUDFLARED_BIN):
        print(f"[!] ไม่พบไฟล์ {CLOUDFLARED_BIN}")
        print("    กำลังดาวน์โหลด cloudflared.exe จาก Cloudflare Official...")
        download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            urllib.request.urlretrieve(download_url, CLOUDFLARED_BIN)
            print("[+] ดาวน์โหลด cloudflared.exe สำเร็จ!")
        except Exception as e:
            print(f"[X] ไม่สามารถดาวน์โหลด cloudflared ได้: {e}")
            sys.exit(1)

    port = 5000
    server_proc = ensure_web_server(port)

    print("[*] กำลังเชื่อมต่อ Cloudflare Tunnel เพื่อสร้าง URL สาธารณะ...")
    tunnel_cmd = [
        CLOUDFLARED_BIN,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{port}",
    ]

    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    tunnel_url = None
    start_time = time.time()

    def read_output(stream):
        nonlocal tunnel_url
        for line in stream:
            # Match https://xxxx.trycloudflare.com
            m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if m and not tunnel_url:
                tunnel_url = m.group(0)

    t1 = threading.Thread(target=read_output, args=(tunnel_proc.stdout,), daemon=True)
    t2 = threading.Thread(target=read_output, args=(tunnel_proc.stderr,), daemon=True)
    t1.start()
    t2.start()

    while not tunnel_url and time.time() - start_time < 30:
        if tunnel_proc.poll() is not None:
            break
        time.sleep(0.2)

    if not tunnel_url:
        print("[X] ไม่สามารถดึง URL จาก Cloudflare Tunnel ได้ กรุณาลองใหม่อีกครั้ง")
        if tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
        sys.exit(1)

    copy_to_clipboard(tunnel_url)

    border = "=" * 72
    print()
    print(border)
    print("  SubFynn Studio — Cloudflare Tunnel (เข้าถึงได้จากทุกที่ทั่วโลก)")
    print(border)
    print("  🌐 ลิงก์ Web App สาธารณะของคุณ (HTTPS):")
    print(f"     👉  {tunnel_url}")
    print(border)
    print("  ✨ รองรับการอัปโหลดไฟล์วิดีโอขนาดใหญ่ (2 GB - 5 GB+) ผ่านเน็ตได้ทันที")
    print("  ✨ แชร์ลิงก์นี้ให้เพื่อน หรือเปิดจากมือถือ/แท็บเล็ต/คอมเครื่องอื่นได้เลย")
    print("  📋 ลิงก์ถูกคัดลอกลง Clipboard แล้ว และกำลังเปิดเบราว์เซอร์อัตโนมัติ")
    print("  💡 กด Ctrl+C ในหน้าต่างนี้เมื่อต้องการปิดการแชร์ Tunnel")
    print(border)
    print()

    try:
        webbrowser.open(tunnel_url)
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
            if tunnel_proc.poll() is not None:
                print("[!] Cloudflare Tunnel หยุดทำงาน")
                break
    except KeyboardInterrupt:
        print("\n[*] กำลังปิด Cloudflare Tunnel และ Web App...")
    finally:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if server_proc and server_proc.poll() is None:
            server_proc.terminate()
        print("[+] ปิดเรียบร้อยแล้ว ขอบคุณที่ใช้งาน SubFynn Studio ครับ")


if __name__ == "__main__":
    main()
