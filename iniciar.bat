@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao encontrado. Siga a instalacao no README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pokervision
if errorlevel 1 pause
