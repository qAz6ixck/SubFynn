@echo off
cd /d "%~dp0"
echo Rendering Manim scene TitleIntro (High Quality 1080p)...
".venv\Scripts\manim.exe" -pqh demo.py TitleIntro
echo.
echo Video file saved in media/videos/demo/1080p60/
pause
