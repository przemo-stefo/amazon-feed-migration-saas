@echo off
echo ================================
echo Starting Amazon Feed Migration Tool
echo ================================
echo.
echo Opening web interface...
echo Do NOT close this window while using the tool.
echo.

REM Start the web server
start "Browser" http://localhost:8000
python simple_app.py

echo.
echo Tool has stopped. You can close this window.
pause