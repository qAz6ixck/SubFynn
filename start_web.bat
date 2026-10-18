@echo off
chcp 65001 > nul
echo ==================================================
echo   AI Thai Subtitle Generator (Web App)
echo   กำลังเริ่มต้นโปรแกรมและเปิดเบราว์เซอร์...
echo ==================================================
if exist "%~dp0dist\SubFynn\SubFynn.exe" (
    "%~dp0dist\SubFynn\SubFynn.exe" --web %*
    exit /b
)
if exist "%~dp0dist\SubFynn\SubFynn-Web.exe" (
    "%~dp0dist\SubFynn\SubFynn-Web.exe" %*
    exit /b
)
if exist "%~dp0dist\ThaiSubtitles\ThaiSubtitles-Web.exe" (
    "%~dp0dist\ThaiSubtitles\ThaiSubtitles-Web.exe" %*
    exit /b
)
python app.py %*
pause
