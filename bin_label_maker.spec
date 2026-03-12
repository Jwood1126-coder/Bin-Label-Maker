# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Bin Label Maker
# Build with: pyinstaller bin_label_maker.spec
# Produces a SINGLE .exe file (no folder)

import os

# Collect data files, skipping missing directories
datas = []
if os.path.isdir('assets'):
    datas.append(('assets', 'assets'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'reportlab',
        'reportlab.lib',
        'reportlab.pdfgen',
        'reportlab.pdfbase',
        'reportlab.pdfbase._fontdata',
        'qrcode',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Use icon only if it exists
icon_path = 'assets/app_icon.ico'
icon_arg = [icon_path] if os.path.isfile(icon_path) else []

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BinLabelMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
