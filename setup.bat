@echo off
REM OneTaskAtATime - Setup Script for Windows

echo ========================================
echo OneTaskAtATime - Environment Setup
echo ========================================
echo.

REM Check Python version
python --version 2>NUL
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv onetask_env

echo.
echo Activating virtual environment...
call onetask_env\Scripts\activate.bat

echo.
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To activate the virtual environment in the future, run:
echo   onetask_env\Scripts\activate.bat
echo.
echo To run the application:
echo   python src\main.py
echo.
pause
