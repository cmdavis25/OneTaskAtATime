# OneTaskAtATime Installation Guide

This guide provides step-by-step instructions for installing OneTaskAtATime v1.0.0 on Windows.

## Table of Contents

- [System Requirements](#system-requirements)
- [Method 1: Windows Installer (Recommended)](#method-1-windows-installer-recommended)
- [Method 2: Portable Executable](#method-2-portable-executable)
- [Method 3: From Source (Developers)](#method-3-from-source-developers)
- [First Launch](#first-launch)
- [Upgrading from Previous Versions](#upgrading-from-previous-versions)
- [Uninstallation](#uninstallation)
- [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 11 (recommended)
  - Windows 10 may work but has not been formally tested
- **RAM**: 2 GB (4 GB recommended)
- **Disk Space**: 150 MB for application + additional space for database
- **Display**: 1280x720 minimum resolution (1920x1080 recommended)
- **Other**: .NET Framework 4.7+ (usually pre-installed on Windows 10/11)

### Tested Platforms
- Windows 11 Home/Pro 64-bit
- Windows 11 Enterprise 64-bit

### Untested but Expected to Work
- Windows 10 version 1909 or later
- Windows Server 2019/2022

### Not Supported
- Windows 8.1 or earlier
- Windows 7
- Linux (planned for future release)
- macOS (planned for future release)

---

## Method 1: Windows Installer (Recommended)

The Windows installer provides the easiest installation experience with automatic shortcuts and integration with Windows.

### Step 1: Download the Installer

1. Visit the [GitHub Releases page](https://github.com/cdavis/OneTaskAtATime/releases)
2. Find the latest release (v1.0.0)
3. Download `OneTaskAtATime-1.0.0-Setup.exe`
4. Save the file to your Downloads folder

### Step 2: Run the Installer

1. Locate the downloaded `OneTaskAtATime-1.0.0-Setup.exe` file
2. Double-click to run the installer
3. If Windows SmartScreen appears:
   - Click "More info"
   - Click "Run anyway"
   - (This appears because the app is not signed with a code-signing certificate)

### Step 3: Follow Installation Wizard

1. **Welcome Screen**: Click "Next"
2. **License Agreement**: Read and accept the CC BY-NC 4.0 license, click "Next"
3. **Installation Location**:
   - Default: `C:\Program Files\OneTaskAtATime`
   - Change if desired, click "Next"
4. **Select Components**:
   - ☑ Desktop shortcut (optional)
   - ☑ Start Menu shortcut (recommended)
   - Click "Next"
5. **Ready to Install**: Review settings, click "Install"
6. **Installation Progress**: Wait for files to be copied (30-60 seconds)
7. **Completing Setup**:
   - ☑ Launch OneTaskAtATime (optional)
   - Click "Finish"

### Step 4: Verify Installation

1. Check for desktop shortcut (if selected)
2. Open Start Menu and search for "OneTaskAtATime"
3. Click the icon to launch the application

### What Gets Installed
- Application files: `C:\Program Files\OneTaskAtATime\`
- Start Menu shortcut: `Start Menu → OneTaskAtATime`
- Desktop shortcut (if selected): `Desktop\OneTaskAtATime`
- Uninstaller: `C:\Program Files\OneTaskAtATime\unins000.exe`

### What Does NOT Get Installed
- Your database file is stored in: `%APPDATA%\OneTaskAtATime\onetaskattime.db`
- Settings file: `%APPDATA%\OneTaskAtATime\settings.json`
- Themes: `%APPDATA%\OneTaskAtATime\themes\`

---

## Method 2: Portable Executable

The portable version requires no installation and can run from a USB drive or any folder.

### Step 1: Download Portable ZIP

1. Visit the [GitHub Releases page](https://github.com/cdavis/OneTaskAtATime/releases)
2. Find the latest release (v1.0.0)
3. Download `OneTaskAtATime-1.0.0-Portable.zip`

### Step 2: Extract Files

1. Right-click the downloaded ZIP file
2. Select "Extract All..."
3. Choose destination folder (e.g., `C:\OneTaskAtATime` or USB drive)
4. Click "Extract"

### Step 3: Run the Application

1. Open the extracted folder
2. Double-click `OneTaskAtATime.exe`
3. If Windows SmartScreen appears:
   - Click "More info"
   - Click "Run anyway"

### Portable Mode Behavior
- Database and settings are stored in the same folder as the executable
- No Start Menu or Desktop shortcuts created
- No registry entries created
- Can be run from USB drive for portability
- To "uninstall", simply delete the folder

---

## Method 3: From Source (Developers)

For developers who want to run from source code or contribute to the project.

### Prerequisites

- Python 3.10 or later
- Git (optional, for cloning repository)

### Step 1: Get Source Code

**Option A: Clone with Git**
```bash
git clone https://github.com/cdavis/OneTaskAtATime.git
cd OneTaskAtATime
```

**Option B: Download ZIP**
1. Visit https://github.com/cdavis/OneTaskAtATime
2. Click "Code" → "Download ZIP"
3. Extract to desired location
4. Open Command Prompt in extracted folder

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv onetask_env
onetask_env\Scripts\activate
```

**Verify activation** - your prompt should show `(onetask_env)` prefix.

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- PyQt5 (GUI framework)
- APScheduler (background task scheduling)
- winotify (Windows notifications)
- pytest (testing framework)
- Other dependencies

### Step 4: Initialize Database (Optional)

**Seed with sample data:**
```bash
python -m src.database.seed_data
```

This creates example tasks for testing. Skip this for production use.

### Step 5: Run the Application

```bash
python -m src.main
```

### Running Tests

```bash
python -m pytest tests/ -v
```

Expected result: 726 tests passing (100% pass rate)

### Building from Source

To create your own executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build using spec file
pyinstaller OneTaskAtATime.spec
```

Executable will be in `dist/OneTaskAtATime/` folder.

---

## First Launch

### What Happens on First Launch

1. **Database Creation**:
   - OneTaskAtATime creates `%APPDATA%\OneTaskAtATime\onetaskattime.db`
   - Empty database with schema v1.0
2. **Default Settings**:
   - Theme: Light
   - Font Size: Medium
   - Resurfacing intervals: 7 days (Someday), 1 day (Delegated)
3. **Welcome Wizard** (optional):
   - Introduction to core concepts
   - Quick tour of Focus Mode
   - Sample task creation

### First Steps

1. **Create Your First Task**:
   - Press `Ctrl+N` or click "New Task"
   - Fill in Title (required), Description (optional)
   - Set Priority: High, Medium, or Low
   - Add Due Date (optional)
   - Click "Save"

2. **Enter Focus Mode**:
   - Press `Alt+F` or click "Focus Mode" tab
   - Your highest-priority task will be displayed
   - Use action buttons to complete, defer, or delegate

3. **Explore Settings**:
   - Press `Ctrl+,` or click File → Settings
   - Try different themes (Light, Dark, System)
   - Adjust font size for readability
   - Configure notification preferences

4. **Read Help**:
   - Press `F1` or click Help → Help Contents
   - Search for specific topics
   - Review keyboard shortcuts with `Ctrl+?`

---

## Upgrading from Previous Versions

### From Beta/Pre-release to v1.0.0

1. **Export Your Data**:
   - In old version: File → Export Data
   - Save JSON file to safe location
   - This is a backup in case of issues

2. **Uninstall Old Version**:
   - Control Panel → Programs → Uninstall
   - Select "OneTaskAtATime (Beta)"
   - Click "Uninstall"
   - **Important**: Check "Keep my database and settings" if prompted

3. **Install v1.0.0**:
   - Follow [Method 1: Windows Installer](#method-1-windows-installer-recommended)

4. **Verify Data Migration**:
   - Launch v1.0.0
   - Check that all tasks are present
   - If tasks are missing, use File → Import Data to restore from backup

### Database Schema Upgrades

OneTaskAtATime automatically migrates your database to the latest schema on first launch. You'll see a progress message if migration is needed.

**Migration is automatic and irreversible. Always export your data before upgrading.**

### From v1.0.0 to Future Versions

1. Export data as backup (recommended)
2. Download new installer
3. Run installer (will detect existing installation)
4. Choose "Upgrade" when prompted
5. Launch and verify data migrated successfully

---

## Uninstallation

### Uninstalling Windows Installer Version

1. Open **Control Panel**
2. Click **Programs** → **Programs and Features**
3. Find **OneTaskAtATime** in the list
4. Click **Uninstall**
5. Confirm when prompted

**What Gets Removed:**
- Application files in `C:\Program Files\OneTaskAtATime\`
- Start Menu shortcuts
- Desktop shortcut (if created)
- Registry entries

**What Gets Kept:**
- Your database: `%APPDATA%\OneTaskAtATime\onetaskattime.db`
- Settings: `%APPDATA%\OneTaskAtATime\settings.json`
- Exported data files (if any)

### To Completely Remove All Data

After uninstalling, manually delete:

```
%APPDATA%\OneTaskAtATime\
```

**Warning**: This permanently deletes all your tasks. Export data first if you might want it later.

### Uninstalling Portable Version

Simply delete the folder containing `OneTaskAtATime.exe`. All data is in that folder.

---

## Troubleshooting

### Installation Issues

**Problem**: "Windows protected your PC" SmartScreen warning

**Solution**:
- Click "More info"
- Click "Run anyway"
- This happens because the app is not code-signed (costs $300+/year for certificate)

---

**Problem**: "The setup files are corrupted"

**Solution**:
- Re-download the installer
- Disable antivirus temporarily
- Download from GitHub Releases (official source only)

---

**Problem**: "Installation failed - not enough disk space"

**Solution**:
- Free up at least 200 MB disk space
- Install to different drive (click "Browse" during installation)

---

**Problem**: Installer runs but nothing happens

**Solution**:
- Check Task Manager for OneTaskAtATime processes
- Kill any running processes
- Restart computer
- Run installer as Administrator (right-click → "Run as administrator")

---

### First Launch Issues

**Problem**: Application won't start, no error message

**Solution**:
- Check if `%APPDATA%\OneTaskAtATime\` folder exists
- If not, create it manually
- Run as Administrator once to create database
- Check Event Viewer (Windows Logs → Application) for errors

---

**Problem**: "Database is locked" error

**Solution**:
- Close any other instances of OneTaskAtATime
- Check Task Manager for zombie processes
- Restart computer
- If persists, delete `%APPDATA%\OneTaskAtATime\onetaskattime.db-wal` file

---

**Problem**: Application starts but shows blank screen

**Solution**:
- Try different theme: Settings → Theme → Light/Dark
- Reset window geometry: Settings → Reset Window Geometry
- Update graphics drivers
- Run with `--safe-mode` flag (if available)

---

### Getting Help

If you encounter issues not covered here:

1. Check **TROUBLESHOOTING.md** for common problems
2. Search [GitHub Issues](https://github.com/cdavis/OneTaskAtATime/issues)
3. Create new issue with:
   - Windows version
   - Installation method used
   - Error message (if any)
   - Steps to reproduce

---

## Next Steps

After successful installation, see:

- **USER_GUIDE.md** - Comprehensive user manual
- **TROUBLESHOOTING.md** - Solutions to common problems
- **CHANGELOG.md** - What's new in v1.0.0
- **README.md** - Project overview

Press `F1` in the application for built-in help.
