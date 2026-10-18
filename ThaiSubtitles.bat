@echo off
if exist "%~dp0dist\ThaiSubtitles\ThaiSubtitles.exe" (
    start "" "%~dp0dist\ThaiSubtitles\ThaiSubtitles.exe" %*
    exit /b
)
python main.py %*
