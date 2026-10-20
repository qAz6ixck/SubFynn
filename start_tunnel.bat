@echo off
chcp 65001 > nul
title SubFynn Studio - Cloudflare Tunnel Launcher
echo ==================================================
echo   SubFynn Studio (Cloudflare Tunnel Mode)
echo   กำลังเริ่มต้น Web App และเปิด Cloudflare Tunnel...
echo ==================================================

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%~dp0tunnel.py" %*
    pause
    exit /b
)

echo [!] ไม่พบ Python บนเครื่องของคุณ กรุณาติดตั้ง Python ก่อนใช้งาน
pause
