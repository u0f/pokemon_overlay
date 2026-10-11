@echo off
cd /d "%~dp0"
if exist "PokeStream.exe" (
    start "" "PokeStream.exe"
    exit /b
)
if not exist ".venv\Scripts\pythonw.exe" (
    echo Ejecuta primero Instalar.cmd
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "launcher.py"
