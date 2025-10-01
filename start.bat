@echo off
setlocal enabledelayedexpansion
title YT-DLP Web Downloader

echo ========================================
echo YT-DLP Web Downloader - Startup
echo ========================================
echo.

:: Check if git is installed
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Git not found. Auto-update disabled.
    echo.
    goto skip_update
)

:: Check if we're in a git repository
if not exist ".git" (
    echo [INFO] Not a git repository. Skipping update check.
    echo.
    goto skip_update
)

:: Check for updates
echo [INFO] Checking for updates...
git fetch origin main >nul 2>&1
git rev-parse HEAD > current_commit.tmp
git rev-parse origin/main > remote_commit.tmp

fc current_commit.tmp remote_commit.tmp >nul 2>&1
if %errorlevel% neq 0 (
    echo [UPDATE AVAILABLE] New version found on GitHub!
    echo.
    set /p update="Would you like to update? (y/n): "
    if /i "!update!"=="y" (
        echo [INFO] Updating from GitHub...
        git pull origin main
        if %errorlevel% equ 0 (
            echo [SUCCESS] Updated successfully!
            echo.
        ) else (
            echo [ERROR] Update failed. Continuing with current version.
            echo.
        )
    ) else (
        echo [INFO] Skipping update.
        echo.
    )
) else (
    echo [OK] Already up to date.
    echo.
)

del current_commit.tmp remote_commit.tmp >nul 2>&1

:skip_update

:: Check Python
echo [CHECK] Verifying Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo.

:: Check pip
echo [CHECK] Verifying pip...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip not found. Please reinstall Python with pip.
    pause
    exit /b 1
)
echo [OK] pip is installed.
echo.

:: Check and install requirements
echo [CHECK] Checking Python dependencies...
if exist requirements.txt (
    echo [INFO] Installing/updating requirements...
    python -m pip install -q -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install requirements.
        pause
        exit /b 1
    )
    echo [OK] Python dependencies installed.
) else (
    echo [WARNING] requirements.txt not found.
)
echo.

:: Check yt-dlp
echo [CHECK] Verifying yt-dlp...
python -m yt_dlp --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] yt-dlp not found. Installing...
    python -m pip install -q yt-dlp
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install yt-dlp.
        pause
        exit /b 1
    )
    echo [OK] yt-dlp installed.
) else (
    python -m yt_dlp --version
    echo [OK] yt-dlp is installed.
)
echo.

:: Check aria2c
echo [CHECK] Verifying aria2c...
where aria2c >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] aria2c not found in PATH.
    echo [INFO] aria2c is optional but recommended for faster downloads.
    echo [INFO] Download from: https://github.com/aria2/aria2/releases
    echo.
) else (
    aria2c --version | findstr /C:"aria2 version"
    echo [OK] aria2c is installed.
    echo.
)

:: Check Flask
echo [CHECK] Verifying Flask...
python -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Flask not found. Installing...
    python -m pip install -q flask
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install Flask.
        pause
        exit /b 1
    )
    echo [OK] Flask installed.
) else (
    echo [OK] Flask is installed.
)
echo.

echo ========================================
echo All checks passed!
echo Starting server on http://localhost:5000
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python app.py
pause