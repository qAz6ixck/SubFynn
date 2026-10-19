@echo off
chcp 65001 > nul
echo ==================================================
echo   SubFynn Studio (AI Thai Subtitle Generator)
echo   กำลังเริ่มต้น Web App และเปิดเบราว์เซอร์...
echo ==================================================

:: ปิดโปรเซส SubFynn เดิมที่อาจค้างอยู่ในระบบ เพื่อป้องกันพอร์ตชนหรือจำ UI เก่า
taskkill /F /IM SubFynn.exe >nul 2>nul

:: 1. รัน app.py โดยตรงเพื่อให้ได้โค้ดและหน้าเว็บเวอร์ชันล่าสุดเสมอ
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python "%~dp0app.py" %*
    exit /b
)

:: 2. หากไม่มี Python ในเครื่อง ให้เรียกผ่านไฟล์ .exe สำเร็จรูป
if exist "%~dp0dist\SubFynn\SubFynn.exe" (
    "%~dp0dist\SubFynn\SubFynn.exe" --web %*
    exit /b
)

python "%~dp0app.py" %*
pause
