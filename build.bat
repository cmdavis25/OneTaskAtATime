@echo off
REM ====================================
REM OneTaskAtATime Build Script
REM ====================================
REM
REM This script automates the build process for creating a Windows executable
REM using PyInstaller. It activates the virtual environment, installs dependencies,
REM cleans previous builds, and packages the application.
REM

echo ====================================
echo Building OneTaskAtATime v1.0.0
echo ====================================
echo.

REM Activate virtual environment
echo Activating virtual environment...
call onetask_env\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment!
    echo Please ensure onetask_env exists and is properly configured.
    pause
    exit /b 1
)

REM Install PyInstaller if not present
echo Checking for PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller and Pillow...
    pip install -r requirements-dev.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
) else (
    echo PyInstaller is already installed.
)

REM Generate icon if it doesn't exist
if not exist "resources\icon.ico" (
    echo.
    echo Generating application icon...
    python scripts\create_icon.py
    if errorlevel 1 (
        echo ERROR: Failed to generate icon!
        pause
        exit /b 1
    )
) else (
    echo Application icon already exists.
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist build (
    echo Removing build directory...
    rmdir /s /q build
)
if exist dist (
    echo Removing dist directory...
    rmdir /s /q dist
)

REM Build executable
echo.
echo ====================================
echo Building executable with PyInstaller...
echo ====================================
pyinstaller OneTaskAtATime.spec

if errorlevel 1 (
    echo.
    echo ====================================
    echo ERROR: Build failed!
    echo ====================================
    echo Please check the error messages above.
    pause
    exit /b 1
)

REM Verify build succeeded
if not exist "dist\OneTaskAtATime\OneTaskAtATime.exe" (
    echo.
    echo ====================================
    echo ERROR: Executable was not created!
    echo ====================================
    pause
    exit /b 1
)

echo.
echo ====================================
echo Build complete!
echo ====================================
echo.
echo Executable location: dist\OneTaskAtATime\OneTaskAtATime.exe
echo.
echo To test the application, run:
echo   dist\OneTaskAtATime\OneTaskAtATime.exe
echo.
echo To create an installer, you can use Inno Setup with the installer script.
echo.
pause
