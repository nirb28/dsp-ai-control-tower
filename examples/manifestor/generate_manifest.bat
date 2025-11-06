@echo off
REM Manifest Generator Launcher for Windows

echo.
echo ====================================================================
echo   Control Tower Manifest Generator
echo ====================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Check if colorama is installed (optional but recommended)
python -c "import colorama" >nul 2>&1
if errorlevel 1 (
    echo.
    echo NOTE: colorama is not installed. The tool will work but without colors.
    echo To install: pip install colorama
    echo.
    timeout /t 3 >nul
)

REM Run the manifest generator
python manifest_generator.py

if errorlevel 1 (
    echo.
    echo ERROR: Manifest generator encountered an error
    pause
    exit /b 1
)

exit /b 0
