# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Locate rlottie DLL (ships inside the rlottie_python package)
try:
    import rlottie_python as _rl
    _rl_dir = Path(_rl.__file__).parent
    _rlottie_dll = str(_rl_dir / 'rlottie.dll')
    _rlottie_binaries = [(_rlottie_dll, '.')]
except Exception:
    _rlottie_binaries = []

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=_rlottie_binaries,
    datas=[
        ('assets', 'assets'),
        ('resources', 'resources'),
        ('app', 'app'),
        ('../assets', 'assets'),
    ],
    hiddenimports=[
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebChannel',
        'PySide6.QtSvg',
        'PySide6.QtMultimedia',
        'win32crypt',
        'win32api',
        'websocket',
        'cryptography',
        'rlottie_python',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'xmlrpc'],
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
    name='Orbit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources\\icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Orbit',
)
