@echo off
chcp 65001 > nul
echo ==================================================
echo   SubFynn - AI Thai Subtitle Generator (Desktop)
echo   Starting SubFynn...
echo ==================================================
if exist "%~dp0dist\SubFynn\SubFynn.exe" (
    start "" "%~dp0dist\SubFynn\SubFynn.exe" %*
    exit /b
)
python main.py %*
