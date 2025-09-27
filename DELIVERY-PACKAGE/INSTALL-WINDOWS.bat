@echo off
echo ================================
echo Amazon Feed Migration Tool Setup
echo ================================
echo.
echo Installing Python and dependencies...
echo This may take 5-10 minutes.
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel%==0 (
    echo ✅ Python is already installed
) else (
    echo ❌ Python not found. Please install Python from https://python.org/downloads
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo.
echo Installing required packages...
pip install fastapi uvicorn pandas openpyxl pyxlsb python-multipart jinja2

if %errorlevel%==0 (
    echo.
    echo ✅ Installation complete!
    echo.
    echo To start the tool, double-click START-WINDOWS.bat
    echo.
    pause
) else (
    echo.
    echo ❌ Installation failed. Please check your internet connection and try again.
    echo If you still have issues, email me with a screenshot of this window.
    echo.
    pause
)