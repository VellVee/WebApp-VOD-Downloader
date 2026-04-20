@echo off
setlocal
title YT-DLP Web Downloader Rewrite

echo ========================================
echo YT-DLP Web Downloader - Startup
echo ========================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo [CHECK] Updating pip...
python -m pip install --upgrade pip -q

echo [CHECK] Installing/Updating requirements (including yt-dlp)...
python -m pip install -U -r requirements.txt -q

echo [OK] Dependencies ready.
echo.
echo ========================================
echo Starting production server on http://0.0.0.0:5000
echo Using Waitress WSGI server
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python -c "from waitress import serve; from app import app; serve(app, host='0.0.0.0', port=5000, threads=6)"
pause
