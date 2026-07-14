@echo off
echo Starting main.py...
python main.py
if %errorlevel% neq 0 (
    echo Error! Return code: %errorlevel%
    pause
    exit /b %errorlevel%
)
echo Successfully completed.
pause