@echo off
setlocal

cd /d "%~dp0electron"

if not exist node_modules (
    echo Installing Electron dependencies for the first time - this may take a few minutes...
    call npm install
    if errorlevel 1 (
        echo.
        echo npm install failed. Make sure Node.js is installed and on PATH.
        pause
        exit /b 1
    )
)

echo Starting AROS...
call npm start

if errorlevel 1 (
    echo.
    echo AROS exited with an error. Common causes:
    echo   - Python dependencies not installed: pip install -r aros_backend\requirements.txt
    echo   - pos-system\pos_system.db is missing or empty
    echo See instructions.txt for full setup steps.
    pause
)
