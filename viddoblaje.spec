# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para VidDoblaje."""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
from pathlib import Path
import os
import os

block_cipher = None
datas = []
binaries = []
hiddenimports = []

datas += collect_data_files("PySide6")
hiddenimports += collect_submodules("PySide6")

datas += [
    ("src/viddoblaje/ui/themes", "viddoblaje/ui/themes"),
]
hiddenimports += ["viddoblaje.stages.analysis", "viddoblaje.stages.audio_extraction"]

def _safe_copy_metadata(pkg):
    try:
        return copy_metadata(pkg)
    except Exception:
        return []

hiddenimports += collect_submodules("faster_whisper")
datas += _safe_copy_metadata("faster-whisper")
try:
    import faster_whisper
    fw_dir = Path(faster_whisper.__file__).parent / "assets"
    if fw_dir.exists():
        datas.append((str(fw_dir), "faster_whisper/assets"))
except Exception:
    pass

try:
    hiddenimports += collect_submodules("transformers")
    datas += _safe_copy_metadata("transformers")
except Exception:
    pass

try:
    hiddenimports += collect_submodules("torch")
except Exception:
    pass

try:
    hiddenimports += collect_submodules("piper")
    datas += collect_data_files("piper")
except Exception:
    pass

try:
    hiddenimports += collect_submodules("speechbrain")
except Exception:
    pass

try:
    hiddenimports += collect_submodules("soundfile")
except Exception:
    pass

hiddenimports += ["ctypes"]

ffmpeg_dir = Path("build/ffmpeg")
if ffmpeg_dir.exists():
    for f in ffmpeg_dir.iterdir():
        if f.is_file():
            binaries.append((str(f), "."))

a = Analysis(
    ["src/viddoblaje/__main__.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "IPython", "jupyter", "tkinter", "PyQt5", "PyQt6"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="VidDoblaje",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/icon.ico" if Path("assets/icon.ico").exists() else None,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[], name="VidDoblaje",
)
