@echo off
REM Actuator Controller - Run Script

REM Check if venv exists
if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate venv and run application
call venv\Scripts\activate.bat
python actuator_controller.py
