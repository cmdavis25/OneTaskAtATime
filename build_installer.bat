@echo off
REM OneTaskAtATime - Windows Installer Build Script
REM This script automates the complete build process for creating a Windows installer
REM
REM Prerequisites:
REM 1. Python 3.10+ installed
REM 2. Virtual environment setup (onetask_env)
REM 3. Inno Setup 6.x installed (https://jrsoftware.org/isdl.php)
REM 4. All dependencies installed in virtual environment
REM
REM Usage: build_installer.bat

echo ========================================
echo OneTaskAtATime Installer Build Script
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "onetask_env\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please create it first with: python -m venv onetask_env
    echo Then install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

echo Step 1: Activating virtual environment...
call onetask_env\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Step 2: Checking PyInstaller installation...
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% neq 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install PyInstaller
        pause
        exit /b 1
    )
)

echo Step 3: Cleaning previous build artifacts...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
echo Previous builds cleaned.

echo Step 4: Building executable with PyInstaller...
pyinstaller OneTaskAtATime.spec
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed!
    pause
    exit /b 1
)

echo Step 5: Verifying executable was created...
if not exist "dist\OneTaskAtATime\OneTaskAtATime.exe" (
    echo ERROR: Executable not found in dist folder!
    pause
    exit /b 1
)
echo Executable created successfully.

echo Step 6: Checking for Inno Setup...
set INNO_SETUP_PATH=
for %%i in ("C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "C:\Program Files\Inno Setup 6\ISCC.exe") do (
    if exist %%i (
        set INNO_SETUP_PATH=%%~i
        goto :found_inno
    )
)

:not_found_inno
echo ERROR: Inno Setup not found!
echo Please install Inno Setup 6 from: https://jrsoftware.org/isdl.php
echo.
echo After installing, you can manually compile the installer by:
echo 1. Opening installer.iss in Inno Setup Compiler
echo 2. Clicking Build ^> Compile (or press Ctrl+F9)
pause
exit /b 1

:found_inno
echo Found Inno Setup at: %INNO_SETUP_PATH%

echo Step 7: Compiling installer with Inno Setup...
"%INNO_SETUP_PATH%" installer.iss
if %ERRORLEVEL% neq 0 (
    echo ERROR: Inno Setup compilation failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo Installer created: Output\OneTaskAtATime-1.0.0-Setup.exe
echo.
echo Next steps:
echo 1. Test the installer on a clean Windows machine
echo 2. Verify all shortcuts work correctly
echo 3. Test uninstallation
echo 4. Upload to GitHub Releases
echo.
pause
