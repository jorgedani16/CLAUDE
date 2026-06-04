@echo off
cd /d "%~dp0"

echo Setting up Content Team app...

python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Please install it from python.org
    pause
    exit /b
)

if not exist venv (
    echo First time setup - installing dependencies...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -q -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Starting app...
echo Open your browser at: http://localhost:5000
echo.
start "" http://localhost:5000
python app.py
pause
