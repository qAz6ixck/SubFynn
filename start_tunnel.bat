@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title SubFynn Studio - Cloudflare Tunnel

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%~dp0tunnel.py" %*
    if errorlevel 1 pause
    exit /b
)

echo [!] Python was not found in your system PATH.
pause
