@echo off
setlocal enabledelayedexpansion

echo ================================================
echo   GameDesk PC - Build GameDesk.exe (PyInstaller)
echo ================================================
echo.

REM Switch to the folder where this .bat file lives (project folder)
cd /d "%~dp0"

REM ------------------------------------------------------------------
REM 0. Config: where the built app should end up, and what the DLL
REM    subfolder next to the .exe should be called.
REM
REM NOTE: the DLL folder is named "LibreHardwareMonitor" on purpose --
REM telemetry.py already searches for LibreHardwareMonitorLib.dll in a
REM subfolder with exactly this name (APP_DIR\LibreHardwareMonitor),
REM so no code changes are needed for it to be found there.
REM ------------------------------------------------------------------
set APP_NAME=GameDesk
set DIST_DIR=dist\%APP_NAME%
set DLL_SUBDIR=%DIST_DIR%\LibreHardwareMonitor

REM ------------------------------------------------------------------
REM 1. Check that Python is available in PATH
REM ------------------------------------------------------------------
python --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Install Python 3.10+ from https://python.org and make sure to
    echo check "Add python.exe to PATH" during install, then run this
    echo .bat file again.
    pause
    exit /b 1
)

echo [1/7] Found Python:
python --version
echo.

REM ------------------------------------------------------------------
REM 2. Check and Activate Virtual Environment
REM ------------------------------------------------------------------
set VENV_DIR=venv
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [2/7] Creating virtual environment in '%VENV_DIR%'...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/7] Virtual environment found.
)
echo Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"
echo.

REM ------------------------------------------------------------------
REM 3. Install runtime dependencies & PyInstaller in VENV
REM ------------------------------------------------------------------
echo [3/7] Installing dependencies and PyInstaller...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies or PyInstaller in venv.
    pause
    exit /b 1
)
echo.

REM ------------------------------------------------------------------
REM 4. Clean previous build output
REM
REM This is what makes the script safe to re-run: every run starts
REM from a clean slate, so old files never linger or get mixed up
REM with a new build after a code change.
REM ------------------------------------------------------------------
echo [4/7] Cleaning previous build (build/, dist/, %APP_NAME%.spec)...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"
echo.

REM ------------------------------------------------------------------
REM 5. Build (folder mode --onedir, more reliable for pythonnet/CLR
REM    than a single-file --onefile build). Runs on a target PC with
REM    NO Python installed -- PyInstaller bundles its own Python
REM    runtime into the output folder.
REM ------------------------------------------------------------------
set ICON_ARG=
if exist "icon.ico" (
    echo [5/7] Building %APP_NAME%.exe with icon.ico ^(this can take a couple of minutes^)...
    set ICON_ARG=--icon=icon.ico
) else (
    echo [5/7] icon.ico not found next to main.py - building without a custom icon...
    echo [5/7] Building %APP_NAME%.exe ^(this can take a couple of minutes^)...
)

python -m PyInstaller --noconfirm --onedir --windowed --name %APP_NAME% %ICON_ARG% ^
    --collect-all pythonnet ^
    --collect-all clr_loader ^
    --collect-all pystray ^
    --hidden-import clr ^
    --hidden-import serial.tools.list_ports_windows ^
    --hidden-import psutil ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed - see the output above for details.
    pause
    exit /b 1
)
echo.

REM ------------------------------------------------------------------
REM 6. Move DLLs into their own subfolder next to GameDesk.exe
REM
REM NOTE: LibreHardwareMonitorLib.dll and its dependencies (System.Memory.dll,
REM HidSharp.dll, etc.) are loaded DYNAMICALLY via clr.AddReference(), not
REM via a normal Python "import" - PyInstaller cannot see this dependency
REM by static analysis, so it will not copy these files automatically.
REM We copy every .dll from the project folder into "LibreHardwareMonitor"
REM subfolder ourselves. This subfolder is separate from PyInstaller's own
REM "_internal" folder (which holds the bundled Python runtime itself and
REM must be left alone).
REM ------------------------------------------------------------------
echo [6/7] Copying DLLs into "%DLL_SUBDIR%"...

if not exist "%DLL_SUBDIR%" mkdir "%DLL_SUBDIR%"

set DLL_COUNT=0
for %%F in (*.dll) do (
    copy /y "%%F" "%DLL_SUBDIR%\" >nul
    set /a DLL_COUNT+=1
)
echo   DLL files copied: !DLL_COUNT!

if !DLL_COUNT! EQU 0 (
    echo   [WARNING] No .dll files found in the project folder.
    echo   LibreHardwareMonitorLib.dll and its dependencies must be placed
    echo   manually into "%DLL_SUBDIR%" - otherwise CPU/GPU/RAM will fall
    echo   back to HWiNFO only ^(fine if HWiNFO is running, otherwise "--"^).
)
echo.

REM ------------------------------------------------------------------
REM 7. Copy the two JSON files and icon.ico next to GameDesk.exe (not inside the DLL
REM    folder, not inside _internal - directly next to the .exe, as
REM    requested). If they already exist from earlier runs/testing,
REM    carry them over so accumulated stats / the edited game list
REM    survive a rebuild. If not, GameDesk.exe will create games.json
REM    and games_list.json itself on first run (see config.py).
REM ------------------------------------------------------------------
echo [7/7] Copying games.json / games_list.json and icon.ico next to %APP_NAME%.exe...

if exist "icon.ico" (
    copy /y "icon.ico" "%DIST_DIR%\" >nul
)

if exist "games_list.json" (
    copy /y "games_list.json" "%DIST_DIR%\" >nul
    echo   games_list.json copied
) else (
    echo   games_list.json not found in project folder - will be created
    echo   automatically on first run of %APP_NAME%.exe
)

if exist "games.json" (
    copy /y "games.json" "%DIST_DIR%\" >nul
    echo   games.json copied
) else (
    echo   games.json not found in project folder - will be created
    echo   automatically on first run of %APP_NAME%.exe
)

if exist "README_games_list.txt" (
    copy /y "README_games_list.txt" "%DIST_DIR%\" >nul
)

echo.
echo ================================================
echo   Done!
echo ================================================
echo.
echo   Final folder layout:
echo     %DIST_DIR%\%APP_NAME%.exe
echo     %DIST_DIR%\games.json
echo     %DIST_DIR%\games_list.json
echo     %DIST_DIR%\LibreHardwareMonitor\   (all the .dll files)
echo     %DIST_DIR%\_internal\              (PyInstaller's own runtime files -
echo                                          required for %APP_NAME%.exe to start,
echo                                          do not move, rename or delete it)
echo.
echo   Copy the ENTIRE "%DIST_DIR%" folder to the target PC (including
echo   _internal and LibreHardwareMonitor) - it does not need Python
echo   or any dependencies installed on that PC.
echo.
echo   To add a game: open %DIST_DIR%\games_list.json in a text editor,
echo   see README_games_list.txt for the exact format.
echo.
echo   This .bat is safe to re-run any time after code changes - it
echo   always rebuilds from a clean state and replaces everything above.
echo.
pause
