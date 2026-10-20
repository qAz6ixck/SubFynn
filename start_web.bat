@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title SubFynn Studio - AI Thai Subtitle Generator

taskkill /F /IM SubFynn.exe >nul 2>nul

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%~dp0app.py" %*
    if errorlevel 1 pause
    exit /b
)

if exist "%~dp0dist\SubFynn\SubFynn.exe" (
    "%~dp0dist\SubFynn\SubFynn.exe" --web %*
    exit /b
)

python "%~dp0app.py" %*
pause
