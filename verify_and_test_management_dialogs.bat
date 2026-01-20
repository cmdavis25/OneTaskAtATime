@echo off
REM Verification and test script for Management Dialog fixes
REM This script:
REM 1. Activates the virtual environment
REM 2. Runs attribute verification script
REM 3. Runs pytest on management dialog tests

echo ======================================================================
echo Management Dialogs - Verification and Test Suite
echo ======================================================================
echo.

REM Activate virtual environment
call onetask_env\Scripts\activate.bat

echo Step 1: Running attribute verification...
echo ----------------------------------------------------------------------
python verify_management_dialogs.py
set VERIFY_EXIT=%ERRORLEVEL%

echo.
echo.
echo Step 2: Running pytest on management dialog tests...
echo ----------------------------------------------------------------------
python -m pytest tests\ui\test_management_dialogs.py -v --tb=short

echo.
echo.
echo ======================================================================
echo Results Summary
echo ======================================================================
if %VERIFY_EXIT%==0 (
    echo Attribute Verification: PASSED
) else (
    echo Attribute Verification: FAILED
)
echo.
echo See pytest output above for detailed test results.
echo ======================================================================

pause
