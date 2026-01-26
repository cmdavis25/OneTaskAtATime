# Building the OneTaskAtATime Windows Installer

This guide explains how to build the Windows installer for OneTaskAtATime using Inno Setup.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Step-by-Step Manual Build](#step-by-step-manual-build)
- [What Gets Packaged](#what-gets-packaged)
- [Installer Configuration](#installer-configuration)
- [Testing the Installer](#testing-the-installer)
- [Troubleshooting](#troubleshooting)
- [Customizing the Installer](#customizing-the-installer)
- [Release Checklist](#release-checklist)

---

## Prerequisites

### Required Software

1. **Python 3.10 or later**
   - Download from: https://www.python.org/downloads/
   - Verify: `python --version`

2. **Inno Setup 6.x**
   - Download from: https://jrsoftware.org/isdl.php
   - Install to default location (C:\Program Files (x86)\Inno Setup 6\)
   - Recommended: Install with "Install Inno Setup Preprocessor" option

3. **Git** (optional, for version control)
   - Download from: https://git-scm.com/downloads

### Project Setup

1. **Clone or download the repository**
   ```bash
   git clone https://github.com/cdavis/OneTaskAtATime.git
   cd OneTaskAtATime
   ```

2. **Create virtual environment**
   ```bash
   python -m venv onetask_env
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   onetask_env\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```

---

## Quick Start

### Automated Build (Recommended)

The easiest way to build the installer is using the automated build script:

```bash
build_installer.bat
```

This script will:
1. Activate the virtual environment
2. Check/install PyInstaller
3. Clean previous build artifacts
4. Build the executable with PyInstaller
5. Compile the installer with Inno Setup
6. Create the final installer in `Output\` folder

**Expected output**: `Output\OneTaskAtATime-1.0.0-Setup.exe`

**Build time**: 2-5 minutes (depending on your system)

---

## Step-by-Step Manual Build

If the automated script fails or you prefer manual control:

### Step 1: Activate Virtual Environment

```bash
onetask_env\Scripts\activate
```

Verify activation - your prompt should show `(onetask_env)`.

### Step 2: Clean Previous Builds (Optional)

```bash
rmdir /s /q build
rmdir /s /q dist
rmdir /s /q Output
```

### Step 3: Build Executable with PyInstaller

```bash
pyinstaller OneTaskAtATime.spec
```

**What this does**:
- Analyzes dependencies
- Bundles Python interpreter
- Packages application code
- Includes resources (themes, icons)
- Creates standalone executable

**Output**: `dist\OneTaskAtATime\` folder containing:
- `OneTaskAtATime.exe` (main executable)
- `_internal\` folder with Python libraries
- `resources\` folder with themes and icons

**Expected time**: 1-3 minutes

**Expected size**: ~100-150 MB

### Step 4: Verify Executable

Before building installer, test the executable:

```bash
cd dist\OneTaskAtATime
OneTaskAtATime.exe
```

**Verify**:
- Application launches without errors
- UI displays correctly
- Can create/edit tasks
- Database is created
- No console window appears (GUI-only)

### Step 5: Compile Installer with Inno Setup

**Option A: Using Inno Setup Compiler GUI**

1. Open `installer.iss` in Inno Setup Compiler
2. Click **Build** → **Compile** (or press `Ctrl+F9`)
3. Watch the compilation log for errors
4. Installer will be created in `Output\` folder

**Option B: Using Command Line**

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

**Expected output**: `Output\OneTaskAtATime-1.0.0-Setup.exe`

**Expected time**: 10-30 seconds

**Expected size**: ~50-80 MB (compressed)

---

## What Gets Packaged

### Executable and Dependencies

From `dist\OneTaskAtATime\`:
- `OneTaskAtATime.exe` - Main executable
- `_internal\` - Python runtime and libraries
  - PyQt5 libraries
  - Python standard library
  - APScheduler
  - winotify
  - dateutil
  - SQLite DLL
- `resources\` - Application resources
  - `icon.ico` - Application icon
  - `themes\dark.qss` - Dark theme stylesheet
  - `themes\light.qss` - Light theme stylesheet

### Documentation Files

- `README.md` - Project overview
- `USER_GUIDE.md` - User manual
- `CHANGELOG.md` - Version history
- `INSTALLATION_GUIDE.md` - Installation instructions

### What Does NOT Get Packaged

**User data** (created on first run):
- `%APPDATA%\OneTaskAtATime\onetaskattime.db` - Task database
- `%APPDATA%\OneTaskAtATime\settings.json` - User settings
- `%APPDATA%\OneTaskAtATime\themes\` - Custom themes

**Development files**:
- Source code (.py files)
- Test files
- Virtual environment
- Git repository
- Development documentation

---

## Installer Configuration

### Key Settings in `installer.iss`

```ini
[Setup]
AppId={8F9A5B2C-4D3E-4F1A-9B7C-2E8D6F5A4C3B}  ; Unique GUID
AppName=OneTaskAtATime
AppVersion=1.0.0
DefaultDirName={autopf}\OneTaskAtATime  ; C:\Program Files\OneTaskAtATime
ArchitecturesAllowed=x64compatible      ; 64-bit Windows
MinVersion=10.0                         ; Windows 10 or later
PrivilegesRequired=admin                ; Requires admin for Program Files
```

### Installation Options

**User can choose**:
- Installation directory (default: `C:\Program Files\OneTaskAtATime`)
- Desktop shortcut (optional, unchecked by default)
- Quick Launch shortcut (optional, Windows 7 only)

**Always installed**:
- Start Menu shortcut
- Uninstaller
- Application files

### Uninstallation Behavior

**What gets removed**:
- Application files in Program Files
- Start Menu shortcuts
- Desktop shortcut (if created)
- Registry uninstall entry

**What is preserved**:
- User database (`%APPDATA%\OneTaskAtATime\`)
- User settings
- Exported data files

**Complete removal**: User must manually delete `%APPDATA%\OneTaskAtATime\`

---

## Testing the Installer

### Pre-Release Testing Checklist

#### 1. Fresh Installation Test

On a clean Windows machine (or VM):

- [ ] Download installer to Downloads folder
- [ ] Double-click installer
- [ ] Accept UAC prompt (if shown)
- [ ] Follow installation wizard
- [ ] Choose custom installation directory
- [ ] Select "Create desktop shortcut"
- [ ] Complete installation
- [ ] Verify Start Menu shortcut exists
- [ ] Verify Desktop shortcut exists (if selected)
- [ ] Launch application from Start Menu
- [ ] Verify application launches successfully
- [ ] Create a test task
- [ ] Close and reopen application
- [ ] Verify task persists

#### 2. Upgrade Installation Test

On a machine with previous version:

- [ ] Export existing data
- [ ] Run new installer
- [ ] Verify upgrade is detected
- [ ] Complete installation
- [ ] Launch application
- [ ] Verify all tasks are still present
- [ ] Verify settings are preserved

#### 3. Uninstallation Test

- [ ] Open Control Panel → Programs and Features
- [ ] Find "OneTaskAtATime"
- [ ] Click Uninstall
- [ ] Verify uninstall completes
- [ ] Verify shortcuts are removed
- [ ] Verify Program Files folder is removed
- [ ] Verify %APPDATA% folder still exists (data preserved)
- [ ] Manually delete %APPDATA%\OneTaskAtATime
- [ ] Verify complete removal

#### 4. Edge Case Testing

- [ ] Test installation with no internet connection
- [ ] Test installation with antivirus enabled
- [ ] Test installation to non-default directory (D:\Apps)
- [ ] Test installation without admin rights (should fail gracefully)
- [ ] Test running installer while app is running (should prompt to close)
- [ ] Test installation on Windows 10 and Windows 11
- [ ] Test on clean VM with minimal software installed

#### 5. Functionality Testing Post-Install

- [ ] Create, edit, delete tasks
- [ ] Change priority and verify Elo system works
- [ ] Test Focus Mode
- [ ] Test comparison dialog
- [ ] Test defer/delegate workflows
- [ ] Test settings (theme, font size)
- [ ] Test notifications
- [ ] Test export/import
- [ ] Test keyboard shortcuts
- [ ] Test window geometry persistence

---

## Troubleshooting

### Build Issues

**Problem**: PyInstaller fails with import errors

**Solution**:
```bash
# Ensure virtual environment is activated
onetask_env\Scripts\activate

# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Clear PyInstaller cache
pyinstaller --clean OneTaskAtATime.spec
```

---

**Problem**: Executable builds but crashes on launch

**Solution**:
1. Check `dist\OneTaskAtATime\` for missing DLLs
2. Review PyInstaller warnings in build log
3. Test executable directly: `dist\OneTaskAtATime\OneTaskAtATime.exe`
4. Check hidden imports in `OneTaskAtATime.spec`
5. Add missing modules to `hiddenimports` list

---

**Problem**: Resources (themes, icons) not found

**Solution**:
1. Verify resources exist: `resources\icon.ico`, `resources\themes\*.qss`
2. Check `datas` section in `OneTaskAtATime.spec`
3. Rebuild with: `pyinstaller --clean OneTaskAtATime.spec`

---

### Inno Setup Issues

**Problem**: Inno Setup compiler not found

**Solution**:
1. Install Inno Setup from https://jrsoftware.org/isdl.php
2. Verify installation: `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
3. Update path in `build_installer.bat` if installed elsewhere

---

**Problem**: Compilation fails with file not found errors

**Solution**:
1. Ensure PyInstaller build completed successfully
2. Verify `dist\OneTaskAtATime\OneTaskAtATime.exe` exists
3. Check paths in `installer.iss` [Files] section
4. Use absolute paths or verify working directory

---

**Problem**: Installer is too large (>150 MB)

**Solution**:
1. This is normal - includes Python runtime (~40MB) + Qt libraries (~60MB)
2. Compressed installer should be 50-80 MB
3. To reduce: remove unused Qt plugins, exclude unnecessary libraries
4. Inno Setup uses LZMA2 compression (very efficient)

---

### Runtime Issues

**Problem**: Installed app shows "Failed to execute script"

**Solution**:
1. Run executable from command line to see full error
2. Check Windows Event Viewer (Application logs)
3. Verify all hidden imports are included
4. Test on multiple Windows versions

---

**Problem**: Antivirus flags installer as malware

**Solution**:
1. This is common for unsigned executables
2. Submit false positive report to antivirus vendor
3. Consider code signing certificate ($300+/year)
4. Users can add exception or use "Run anyway"

---

## Customizing the Installer

### Changing Version Number

1. Update version in `src\__init__.py`:
   ```python
   __version__ = "1.1.0"
   ```

2. Update `version_info.txt`:
   ```
   filevers=(1, 1, 0, 0),
   prodvers=(1, 1, 0, 0),
   StringStruct(u'FileVersion', u'1.1.0.0'),
   StringStruct(u'ProductVersion', u'1.1.0.0')
   ```

3. Update `installer.iss`:
   ```ini
   #define MyAppVersion "1.1.0"
   ```

4. Rebuild everything:
   ```bash
   build_installer.bat
   ```

### Adding License Agreement

1. Create `LICENSE.txt` in root directory
2. Uncomment in `installer.iss`:
   ```ini
   LicenseFile=LICENSE.txt
   ```
3. Rebuild installer

### Customizing Install Location

Edit `installer.iss`:
```ini
DefaultDirName={localappdata}\OneTaskAtATime  ; User's AppData instead of Program Files
PrivilegesRequired=lowest                     ; No admin required
```

### Adding File Associations

Edit `installer.iss` [Registry] section:
```ini
[Registry]
Root: HKCR; Subkey: ".ota"; ValueType: string; ValueName: ""; ValueData: "OneTaskAtATimeFile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "OneTaskAtATimeFile"; ValueType: string; ValueName: ""; ValueData: "OneTaskAtATime Task File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "OneTaskAtATimeFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\OneTaskAtATime.exe,0"
Root: HKCR; Subkey: "OneTaskAtATimeFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OneTaskAtATime.exe"" ""%1"""
```

---

## Release Checklist

Before releasing the installer:

### Pre-Build

- [ ] All tests passing (100% pass rate)
- [ ] No critical bugs in issue tracker
- [ ] CHANGELOG.md updated with release notes
- [ ] Version numbers updated in all files
- [ ] Documentation reviewed and updated
- [ ] Code committed and tagged in Git

### Build Process

- [ ] Virtual environment activated
- [ ] Dependencies up to date
- [ ] PyInstaller build successful
- [ ] Executable tested manually
- [ ] Inno Setup compilation successful
- [ ] No warnings in build logs

### Testing

- [ ] Fresh install tested on clean VM
- [ ] Upgrade from previous version tested
- [ ] Uninstall tested
- [ ] Application functionality verified
- [ ] Tested on Windows 10 and 11
- [ ] SmartScreen warning behavior verified

### Documentation

- [ ] INSTALLATION_GUIDE.md reflects current process
- [ ] USER_GUIDE.md is up to date
- [ ] README.md updated
- [ ] BUILD_INSTALLER.md reviewed

### Release

- [ ] Create Git tag: `git tag v1.0.0`
- [ ] Push tag: `git push origin v1.0.0`
- [ ] Create GitHub Release
- [ ] Upload installer: `OneTaskAtATime-1.0.0-Setup.exe`
- [ ] Add release notes from CHANGELOG.md
- [ ] Mark as latest release
- [ ] Notify users of update

---

## Advanced Topics

### Code Signing

To remove SmartScreen warnings, sign the installer:

1. Purchase code signing certificate ($300-600/year)
2. Install certificate on build machine
3. Add to `installer.iss`:
   ```ini
   SignTool=signtool sign /f "path\to\cert.pfx" /p "password" /t http://timestamp.digicert.com $f
   SignedUninstaller=yes
   ```

### Auto-Update Integration

Future enhancement - add auto-update checking:

1. Host update manifest (JSON) on website
2. App checks for updates on launch
3. Downloads and verifies new installer
4. Prompts user to install update
5. Uses GUID from installer.iss to detect installed version

### Multi-Language Support

To add language options:

1. Create translated .isl files
2. Add to `installer.iss`:
   ```ini
   [Languages]
   Name: "english"; MessagesFile: "compiler:Default.isl"
   Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
   Name: "french"; MessagesFile: "compiler:Languages\French.isl"
   ```

---

## Getting Help

If you encounter issues not covered here:

1. Check Inno Setup documentation: https://jrsoftware.org/ishelp/
2. Search existing GitHub issues
3. Create new issue with:
   - Build log output
   - System information
   - Steps to reproduce
   - Error messages

---

## See Also

- **OneTaskAtATime.spec** - PyInstaller configuration
- **version_info.txt** - Windows version metadata
- **INSTALLATION_GUIDE.md** - User installation instructions
- **PHASE10_STATUS.md** - Release infrastructure documentation
