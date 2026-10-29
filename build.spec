# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for YoloToJson.exe (Windows, no console).
Build: pyinstaller build.spec
Output: dist/YoloToJson.exe

Uses tkinter (built-in) — no external GUI dependencies.
Only Pillow is required (for image dimension reading).
"""

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'yolo_to_json',
        'settings_manager',
        'converter_worker',
        'lang',
        'image_cropper',
        'viewer_base',
        'cropper_window',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='YoloToJson',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    version='version_info.txt',
)
