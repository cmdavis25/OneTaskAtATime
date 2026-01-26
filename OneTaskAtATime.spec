# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for OneTaskAtATime application.

This file defines how PyInstaller should build the Windows executable,
including what files to bundle, hidden imports, and executable metadata.
"""

block_cipher = None

a = Analysis(
    ['src\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources\\themes\\*.qss', 'resources\\themes'),
        ('resources\\icon.ico', 'resources'),
        ('resources\\Logo.png', 'resources'),
    ],
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'apscheduler',
        'apscheduler.schedulers',
        'apscheduler.schedulers.background',
        'apscheduler.triggers',
        'apscheduler.triggers.interval',
        'winotify',
        'dateutil',
        'dateutil.parser',
        'dateutil.relativedelta',
        'sqlite3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OneTaskAtATime',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI application - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources\\icon.ico',
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OneTaskAtATime',
)
