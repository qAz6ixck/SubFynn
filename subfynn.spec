# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [
    ('assets', 'assets'),
]
if os.path.isdir('data'):
    datas.append(('data', 'data'))

binaries = []
if os.path.isfile('ffmpeg.exe'):
    binaries.append(('ffmpeg.exe', '.'))
if os.path.isfile('ffprobe.exe'):
    binaries.append(('ffprobe.exe', '.'))

hiddenimports = [
    'pywinstyles',
    'gui',
    'main',
    'engine',
    'customtkinter',
    'ctranslate2',
    'faster_whisper',
    'onnxruntime',
    'av',
    'tokenizers',
    'huggingface_hub',
    'google',
    'google.genai',
    'requests',
    'urllib.request',
    'urllib.parse',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'tkinter.ttk',
    'wave',
    'numpy',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
]

packages_to_collect = [
    'customtkinter',
    'pywinstyles',
    'ctranslate2',
    'faster_whisper',
    'onnxruntime',
    'av',
    'tokenizers',
    'huggingface_hub',
    'google.genai',
    'PIL',
]

for pkg in packages_to_collect:
    d, b, h = collect_all(pkg)
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests', 'google.genai.tests'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# SubFynn Desktop GUI Exe (Windowed) with custom icon
icon_path = os.path.abspath('assets/app_icon.ico') if os.path.isfile('assets/app_icon.ico') else None

exe_gui = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SubFynn',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe_gui,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SubFynn',
)
