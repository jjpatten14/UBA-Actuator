@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Actuator Controller Setup
echo ============================================
echo.

REM ============================================
REM Check 1: Python installed?
REM ============================================
echo [1/5] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo To fix this:
    echo   1. Download Python from https://www.python.org/downloads/
    echo   2. Run the installer
    echo   3. IMPORTANT: Check "Add Python to PATH" at the bottom of the installer
    echo   4. Re-run this setup script
    echo.
    pause
    exit /b 1
)
echo        Python found!

REM ============================================
REM Check 2: Python version >= 3.6?
REM ============================================
echo [2/5] Checking Python version...
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PYMAJOR=%%a
    set PYMINOR=%%b
)

if !PYMAJOR! LSS 3 (
    echo.
    echo ERROR: Python 3.6 or higher is required
    echo        You have Python !PYVER!
    echo.
    echo To fix this:
    echo   1. Download Python 3.x from https://www.python.org/downloads/
    echo   2. Install it ^(can be alongside Python 2^)
    echo   3. Make sure Python 3 is in your PATH
    echo.
    pause
    exit /b 1
)

if !PYMAJOR! EQU 3 if !PYMINOR! LSS 6 (
    echo.
    echo ERROR: Python 3.6 or higher is required
    echo        You have Python !PYVER!
    echo.
    echo To fix this:
    echo   1. Download a newer Python from https://www.python.org/downloads/
    echo   2. Install and ensure it's in your PATH
    echo.
    pause
    exit /b 1
)
echo        Python !PYVER! - OK

REM ============================================
REM Check 3: tkinter available?
REM ============================================
echo [3/5] Checking for tkinter...
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: tkinter is not available
    echo.
    echo tkinter is required for the graphical interface.
    echo.
    echo To fix this:
    echo   1. Re-run the Python installer
    echo   2. Choose "Modify"
    echo   3. Ensure "tcl/tk and IDLE" is checked
    echo   4. Complete the installation
    echo   5. Re-run this setup script
    echo.
    pause
    exit /b 1
)
echo        tkinter - OK

REM ============================================
REM Step 4: Create virtual environment
REM ============================================
echo [4/5] Setting up virtual environment...
if exist venv (
    echo        Virtual environment already exists
) else (
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment
        echo.
        echo Try running: python -m pip install --upgrade virtualenv
        echo Then re-run this setup script
        echo.
        pause
        exit /b 1
    )
    echo        Virtual environment created
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip silently
python -m pip install --upgrade pip >nul 2>&1

REM Install requirements
echo        Installing dependencies...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    echo.
    echo Try running manually:
    echo   venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo        Dependencies installed

REM ============================================
REM Step 5: Verify all imports work
REM ============================================
echo [5/5] Verifying installation...

python -c "import serial; import tkinter; import customtkinter; print('OK')" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Verification failed - some imports are not working
    echo.
    echo Try deleting the venv folder and running setup again:
    echo   rmdir /s /q venv
    echo   setup.bat
    echo.
    pause
    exit /b 1
)
echo        All imports verified!

echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo  Python Version: !PYVER!
echo  Virtual Env:    venv\
echo  Dependencies:   pyserial, customtkinter
echo.
echo  To run the application: run.bat
echo.
echo ============================================
pause
