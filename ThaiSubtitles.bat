@echo off
if exist "%~dp0dist\SubFynn\SubFynn.exe" (
    start "" "%~dp0dist\SubFynn\SubFynn.exe" %*
    exit /b
)
if exist "%~dp0dist\ThaiSubtitles\ThaiSubtitles.exe" (
    start "" "%~dp0dist\ThaiSubtitles\ThaiSubtitles.exe" %*
    exit /b
)
python main.py %*
