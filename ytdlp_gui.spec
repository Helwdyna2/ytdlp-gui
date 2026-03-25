# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for yt-dlp GUI.

Build commands:
    Windows: pyinstaller ytdlp_gui.spec
    macOS: pyinstaller ytdlp_gui.spec
    Linux: pyinstaller ytdlp_gui.spec

For folder distribution (recommended for first build):
    pyinstaller --onedir ytdlp_gui.spec

For single file distribution:
    pyinstaller --onefile ytdlp_gui.spec
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect yt-dlp data files and submodules
yt_dlp_datas = collect_data_files('yt_dlp')
yt_dlp_hiddenimports = collect_submodules('yt_dlp')

# Platform-specific settings
if sys.platform == 'win32':
    icon_path = 'resources/icons/app_icon.ico'
    icon = icon_path if os.path.exists(icon_path) else None
    name = 'yt-dlp-gui'
    console = False
elif sys.platform == 'darwin':
    icon_path = 'resources/icons/app_icon.icns'
    icon = icon_path if os.path.exists(icon_path) else None
    name = 'yt-dlp-gui'
    console = False
else:
    icon_path = 'resources/icons/app_icon.png'
    icon = icon_path if os.path.exists(icon_path) else None
    name = 'yt-dlp-gui'
    console = False

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=yt_dlp_datas,
    hiddenimports=yt_dlp_hiddenimports + [
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'scipy',
    ],
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
    name=name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=name,
)

# macOS bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='yt-dlp GUI.app',
        icon=icon,
        bundle_identifier='com.ytdlpgui.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleName': 'yt-dlp GUI',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )
