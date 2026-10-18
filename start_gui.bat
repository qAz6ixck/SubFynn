@echo off
chcp 65001 > nul
echo ==================================================
echo   AI Thai Subtitle Generator (Desktop GUI)
echo   กำลังเปิดหน้าต่างโปรแกรม...
echo ==================================================
if exist "%~dp0dist\ThaiSubtitles\ThaiSubtitles.exe" (
    start "" "%~dp0dist\ThaiSubtitles\ThaiSubtitles.exe" %*
    exit /b
)
python gui.py %*
pause
