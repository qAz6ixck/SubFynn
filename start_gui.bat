@echo off
chcp 65001 > nul
if exist "%~dp0dist\SubFynn\SubFynn.exe" (
    start "" "%~dp0dist\SubFynn\SubFynn.exe" %*
    exit /b
)
python main.py %*
