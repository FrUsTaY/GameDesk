@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   GameDesk PC - Developer Run Script
echo ================================================
echo.

cd /d "%~dp0"

REM 1. Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    pause
    exit /b 1
)

REM 2. Check and Create Virtual Environment
set VENV_DIR=venv
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [INFO] Creating virtual environment in '%VENV_DIR%'...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Virtual environment found.
)

REM 3. Activate Virtual Environment
echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

REM 4. Install Dependencies
echo [INFO] Checking and installing dependencies from requirements.txt...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [INFO] Dependencies installed successfully.
echo.

REM 5. Run Application
echo [INFO] Starting GameDesk in background...
start "" pythonw main.py

echo.
echo [INFO] Application started! Look for the icon in your System Tray.
echo [INFO] You can safely close this window now.
timeout /t 5 >nul
