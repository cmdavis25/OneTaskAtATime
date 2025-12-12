@echo off
REM OneTaskAtATime - Run Script for Windows

echo Starting OneTaskAtATime...
echo.

REM Activate virtual environment
call onetask_env\Scripts\activate.bat

REM Run the application
python src\main.py

REM Keep window open if there's an error
if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%
    pause
)
