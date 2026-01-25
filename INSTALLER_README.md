# Windows Installer Quick Reference

This document provides a quick reference for building the OneTaskAtATime Windows installer.

## Files Overview

- **`installer.iss`** - Inno Setup script that defines the installer configuration
- **`build_installer.bat`** - Automated build script (Windows batch file)
- **`BUILD_INSTALLER.md`** - Comprehensive documentation for building and customizing the installer
- **`OneTaskAtATime.spec`** - PyInstaller configuration for building the executable
- **`version_info.txt`** - Windows version metadata embedded in the executable

## Quick Build

```bash
# Automated build (recommended)
build_installer.bat
```

Output: `Output\OneTaskAtATime-1.0.0-Setup.exe`

## Manual Build

```bash
# 1. Activate virtual environment
onetask_env\Scripts\activate

# 2. Build executable
pyinstaller OneTaskAtATime.spec

# 3. Compile installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## Prerequisites

1. Python 3.10+ with virtual environment setup
2. All dependencies installed: `pip install -r requirements.txt`
3. PyInstaller installed: `pip install pyinstaller`
4. Inno Setup 6.x installed from https://jrsoftware.org/isdl.php

## Testing the Installer

```bash
# Install
Output\OneTaskAtATime-1.0.0-Setup.exe

# Test the installed application
# Default location: C:\Program Files\OneTaskAtATime\OneTaskAtATime.exe

# Uninstall
# Control Panel → Programs and Features → OneTaskAtATime → Uninstall
```

## What Gets Installed

**Application Files** (`C:\Program Files\OneTaskAtATime\`):
- `OneTaskAtATime.exe` - Main executable
- `_internal\` - Python runtime and libraries
- `resources\` - Icons and themes
- Documentation files (README, USER_GUIDE, etc.)

**Shortcuts**:
- Start Menu: `Start → OneTaskAtATime`
- Desktop: Optional during installation

**User Data** (NOT in Program Files):
- Database: `%APPDATA%\OneTaskAtATime\onetaskattime.db`
- Settings: `%APPDATA%\OneTaskAtATime\settings.json`

## Common Issues

**Problem**: PyInstaller fails
```bash
# Clear cache and rebuild
pyinstaller --clean OneTaskAtATime.spec
```

**Problem**: Inno Setup not found
- Install from: https://jrsoftware.org/isdl.php
- Default location: `C:\Program Files (x86)\Inno Setup 6\`

**Problem**: Executable works but installer fails
- Verify `dist\OneTaskAtATime\OneTaskAtATime.exe` exists
- Check paths in `installer.iss` [Files] section

**Problem**: Antivirus flags installer
- This is normal for unsigned executables
- Users can choose "Run anyway" or add exception

## Versioning

When releasing a new version:

1. Update `src\__init__.py`:
   ```python
   __version__ = "1.1.0"
   ```

2. Update `version_info.txt` (two places):
   ```
   filevers=(1, 1, 0, 0)
   FileVersion: "1.1.0.0"
   ```

3. Update `installer.iss`:
   ```ini
   #define MyAppVersion "1.1.0"
   ```

4. Update `CHANGELOG.md` with release notes

5. Rebuild: `build_installer.bat`

## Architecture

**Installer Type**: Inno Setup 6.x
**Target Platform**: Windows 10/11 (64-bit)
**Installation Type**: System-wide (requires admin)
**Uninstall**: Full uninstall support, preserves user data

## Size Expectations

- **Executable folder** (`dist\OneTaskAtATime\`): ~100-150 MB
- **Compressed installer**: ~50-80 MB
- **Installed size**: ~100-150 MB
- **User data**: 1-50 MB (grows with task count)

## Support

For detailed instructions, see:
- **BUILD_INSTALLER.md** - Complete build and troubleshooting guide
- **INSTALLATION_GUIDE.md** - End-user installation instructions
- **PHASE10_STATUS.md** - Release infrastructure documentation

For issues:
- Check build logs for error messages
- Search GitHub issues
- Create new issue with build output and system info
