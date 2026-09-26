#!/usr/bin/env python3
"""Genera build scripts, NSIS, PyInstaller spec, GitHub workflow, docs."""
from pathlib import Path
import os
import textwrap

BASE = Path("/home/z/my-project/viddoblaje")

def write(rel_path, content):
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  {rel_path}")

# === viddoblaje.spec ===
write("viddoblaje.spec", '''# -*- mode: python ; coding: utf-8 -*-
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
''')

# === NSIS script ===
write("scripts/viddoblaje.nsi", r'''; VidDoblaje NSIS Installer
!define MyAppName "VidDoblaje"
!define MyAppVersion "1.0.0"
!define MyAppPublisher "VidDoblaje"
!define MyAppExeName "VidDoblaje.exe"
!define MyAppAssocExt ".viddoblaje"
!define MyAppAssocKey "VidDoblaje.Project"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "${MyAppName}"
OutFile "..\dist\Output\VidDoblajeSetup.exe"
InstallDir "$LOCALAPPDATA\${MyAppName}"
InstallDirRegKey HKCU "Software\${MyAppName}" "InstallDir"
RequestExecutionLevel user
Unicode true
ShowInstDetails show
ShowUnInstDetails show

VIAddVersionKey "ProductName" "${MyAppName}"
VIAddVersionKey "CompanyName" "${MyAppPublisher}"
VIAddVersionKey "FileDescription" "VidDoblaje Setup"
VIAddVersionKey "FileVersion" "${MyAppVersion}"
VIProductVersion "1.0.0.0"
VIFileVersion "1.0.0.0"

SetCompressor /SOLID zlib

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\icon.ico"
!define MUI_UNICON "..\assets\icon.ico"
!define MUI_WELCOMEPAGE_TITLE "Bienvenido al instalador de ${MyAppName}"
!define MUI_WELCOMEPAGE_TEXT "VidDoblaje traduce y dobla automáticamente tus vídeos al español, de forma 100% local.$\r$\n$\r$\nHaz clic en Siguiente para continuar."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_RESERVEFILE_LANGDLL

Section "Icono en escritorio" SecDesktop
    SectionIn 1
SectionEnd

Section "Asociar archivos .viddoblaje" SecAssoc
    SectionIn 1
SectionEnd

Section "VidDoblaje (requerido)" SecCore
    SectionIn RO
    SetOutPath "$INSTDIR"

    ; FFmpeg bundled
    SetOutPath "$INSTDIR\bin"
    File /nonfatal "..\build\ffmpeg\ffmpeg.exe"
    File /nonfatal "..\build\ffmpeg\ffprobe.exe"
    File /nonfatal "..\build\ffmpeg\avcodec-63.dll"
    File /nonfatal "..\build\ffmpeg\avdevice-63.dll"
    File /nonfatal "..\build\ffmpeg\avfilter-12.dll"
    File /nonfatal "..\build\ffmpeg\avformat-63.dll"
    File /nonfatal "..\build\ffmpeg\avutil-61.dll"
    File /nonfatal "..\build\ffmpeg\swresample-7.dll"
    File /nonfatal "..\build\ffmpeg\swscale-10.dll"
    SetOutPath "$INSTDIR"

    ; PyInstaller dist (if exists)
    File /nonfatal /r "..\dist\VidDoblaje\*"

    ; Source code
    SetOutPath "$INSTDIR\src"
    File /nonfatal /r "..\src\*"
    SetOutPath "$INSTDIR"

    ; Docs
    SetOutPath "$INSTDIR\docs"
    File /nonfatal "..\LICENSE.txt"
    File /nonfatal "..\README.md"
    File /nonfatal "..\requirements.txt"
    SetOutPath "$INSTDIR"

    WriteRegStr HKCU "Software\${MyAppName}" "InstallDir" "$INSTDIR"
    WriteUninstaller "$INSTDIR\uninstall.exe"

    CreateDirectory "$SMPROGRAMS\${MyAppName}"
    ${If} ${FileExists} "$INSTDIR\${MyAppExeName}"
        CreateShortcut "$SMPROGRAMS\${MyAppName}\${MyAppName}.lnk" "$INSTDIR\${MyAppExeName}"
    ${EndIf}
    CreateShortcut "$SMPROGRAMS\${MyAppName}\Desinstalar ${MyAppName}.lnk" "$INSTDIR\uninstall.exe"

    SectionGetFlags ${SecDesktop} $0
    IntOp $0 $0 & ${SF_SELECTED}
    ${If} $0 <> 0
        ${If} ${FileExists} "$INSTDIR\${MyAppExeName}"
            CreateShortcut "$DESKTOP\${MyAppName}.lnk" "$INSTDIR\${MyAppExeName}"
        ${EndIf}
    ${EndIf}

    SectionGetFlags ${SecAssoc} $0
    IntOp $0 $0 & ${SF_SELECTED}
    ${If} $0 <> 0
        WriteRegStr HKCU "Software\Classes\${MyAppAssocExt}" "" "${MyAppAssocKey}"
        WriteRegStr HKCU "Software\Classes\${MyAppAssocKey}" "" "VidDoblaje Project"
        WriteRegStr HKCU "Software\Classes\${MyAppAssocKey}\DefaultIcon" "" "$INSTDIR\${MyAppExeName},0"
        WriteRegStr HKCU "Software\Classes\${MyAppAssocKey}\shell\open\command" "" '"$INSTDIR\${MyAppExeName}" "%1"'
    ${EndIf}

    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "DisplayName" "${MyAppName}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "DisplayVersion" "${MyAppVersion}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "Publisher" "${MyAppPublisher}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "NoRepair" 1

SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Crea un acceso directo en el escritorio"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecAssoc} "Abre archivos .viddoblaje con VidDoblaje"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Componentes principales (incluye FFmpeg LGPL)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Function .onInit
    SectionGetFlags ${SecDesktop} $0
    IntOp $0 $0 | ${SF_SELECTED}
    SectionSetFlags ${SecDesktop} $0
    SectionGetFlags ${SecAssoc} $0
    IntOp $0 $0 | ${SF_SELECTED}
    SectionSetFlags ${SecAssoc} $0
FunctionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    RMDir /r "$SMPROGRAMS\${MyAppName}"
    Delete "$DESKTOP\${MyAppName}.lnk"
    DeleteRegKey HKCU "Software\Classes\${MyAppAssocKey}"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}"
    DeleteRegKey HKCU "Software\${MyAppName}"
    MessageBox MB_YESNO|MB_ICONQUESTION "¿Eliminar también tus proyectos de VidDoblaje?$\r$\n$\r$\nEsta acción NO se puede deshacer." /SD IDNO IDNO skip
        RMDir /r "$PROFILE\Documents\VidDoblajeProjects"
    skip:
SectionEnd
''')

# === build.sh ===
write("scripts/build.sh", '''#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "=== VidDoblaje Build ==="
[ -d .venv ] && source .venv/bin/activate 2>/dev/null || true
pip install --quiet -r requirements.txt 2>&1 | tail -3 || true
pip install --quiet pyinstaller 2>&1 | tail -3
echo "[1/3] PyInstaller..."
rm -rf build/viddoblaje dist/VidDoblaje
pyinstaller viddoblaje.spec --noconfirm 2>&1 | tail -3
echo "[2/3] NSIS..."
mkdir -p dist/Output
if command -v makensis &>/dev/null; then
    makensis scripts/viddoblaje.nsi 2>&1 | tail -5
elif [ -d /tmp/nsis-portable/usr/bin ]; then
    export NSISDIR=/tmp/nsis-portable/usr/share/nsis
    PATH=$PATH:/tmp/nsis-portable/usr/bin makensis scripts/viddoblaje.nsi 2>&1 | tail -5
else
    echo "NSIS no encontrado"
fi
echo "[3/3] Done."
ls -la dist/Output/ 2>/dev/null || echo "No installer generated"
''')
os.chmod(BASE / "scripts/build.sh", 0o755)

# === GitHub Actions workflow ===
write(".github/workflows/windows-ci.yml", '''name: Windows CI - Build & Test

on:
  push:
    branches: [main, master]
    tags: ['v*']
  pull_request:
    branches: [main, master]
  workflow_dispatch:

jobs:
  build-and-test-windows:
    runs-on: windows-latest
    timeout-minutes: 90

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~\\AppData\\Local\\pip\\Cache
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        shell: pwsh
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller pefile

      - name: Install NSIS
        shell: pwsh
        run: |
          choco install nsis -y --no-progress
          echo "C:\\Program Files (x86)\\NSIS" >> $env:GITHUB_PATH

      - name: Download FFmpeg (Windows LGPL)
        shell: pwsh
        run: |
          mkdir -p build/ffmpeg
          curl -L -o build/ffmpeg/ffmpeg.zip https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl-shared.zip
          cd build/ffmpeg
          unzip -q ffmpeg.zip
          $dir = Get-ChildItem -Directory -Filter "ffmpeg-*" | Select-Object -First 1
          Move-Item "$($dir.FullName)\\bin\\*" .
          Remove-Item -Recurse -Force $dir, ffmpeg.zip

      - name: Generate app icon
        shell: pwsh
        run: |
          pip install pillow
          python -c "
          from PIL import Image, ImageDraw, ImageFont
          img = Image.new('RGBA', (256, 256), (0,0,0,0))
          draw = ImageDraw.Draw(img)
          draw.rounded_rectangle([20,20,236,236], radius=40, fill=(74,127,255,255))
          try:
              font = ImageFont.truetype('C:\\Windows\\Fonts\\arialbd.ttf', 130)
          except: font = ImageFont.load_default()
          text = 'VD'
          bbox = draw.textbbox((0,0), text, font=font)
          tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
          draw.text(((256-tw)/2, (256-th)/2-15), text, fill='white', font=font)
          img.save('assets/icon.ico', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
          print('Icon generated')
          "

      - name: Run quick tests
        shell: pwsh
        run: |
          $env:PYTHONPATH = "src;."
          python -m pytest tests/test_core.py tests/test_stages.py -v --tb=short -m "not needs_models and not gpu"

      - name: Build VidDoblaje.exe
        shell: pwsh
        run: |
          pyinstaller viddoblaje.spec --noconfirm
          if (-not (Test-Path "dist\\VidDoblaje\\VidDoblaje.exe")) { throw "VidDoblaje.exe not found" }
          Write-Host "✓ VidDoblaje.exe built"

      - name: Verify VidDoblaje.exe is PE32
        shell: pwsh
        run: |
          $exe = "dist\\VidDoblaje\\VidDoblaje.exe"
          $bytes = [System.IO.File]::ReadAllBytes($exe)[0..1]
          $magic = [System.Text.Encoding]::ASCII.GetString($bytes)
          if ($magic -ne "MZ") { throw "Not a valid PE32" }
          $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
          Write-Host "✓ VidDoblaje.exe is valid PE32 ($size MB)"

      - name: Run VidDoblaje.exe smoke test
        shell: pwsh
        run: |
          $env:HOME = $env:LOCALAPPDATA
          & "dist\\VidDoblaje\\VidDoblaje.exe" --cli --list-models 2>&1 | Tee-Object -Variable output
          if ($LASTEXITCODE -ne 0) { throw "VidDoblaje.exe failed" }
          if (-not ($output -match "whisper-base")) { throw "Output missing expected content" }
          Write-Host "✓ VidDoblaje.exe runs correctly"

      - name: Build VidDoblajeSetup.exe
        shell: pwsh
        run: |
          mkdir -p dist/Output
          & "C:\\Program Files (x86)\\NSIS\\makensis.exe" scripts/viddoblaje.nsi
          if (-not (Test-Path "dist\\Output\\VidDoblajeSetup.exe")) { throw "Installer not built" }
          Write-Host "✓ VidDoblajeSetup.exe built"

      - name: Install VidDoblaje (silent)
        shell: pwsh
        run: |
          Start-Process -FilePath "dist\\Output\\VidDoblajeSetup.exe" -ArgumentList "/S" -Wait
          Write-Host "✓ Installation completed"

      - name: Verify installation
        shell: pwsh
        run: |
          $dir = "$env:LOCALAPPDATA\\VidDoblaje"
          if (-not (Test-Path "$dir\\VidDoblaje.exe")) { throw "VidDoblaje.exe not found after install" }
          if (-not (Test-Path "$dir\\uninstall.exe")) { throw "Uninstaller not found" }
          Write-Host "✓ Installation verified"

      - name: Run installed VidDoblaje.exe
        shell: pwsh
        run: |
          $env:HOME = $env:LOCALAPPDATA
          & "$env:LOCALAPPDATA\\VidDoblaje\\VidDoblaje.exe" --cli --list-models 2>&1 | Tee-Object -Variable output
          if ($LASTEXITCODE -ne 0) { throw "Installed VidDoblaje failed" }
          if (-not ($output -match "whisper-base")) { throw "Output missing expected content" }
          Write-Host "✓ Installed VidDoblaje.exe runs"

      - name: Uninstall VidDoblaje
        shell: pwsh
        run: |
          Start-Process -FilePath "$env:LOCALAPPDATA\\VidDoblaje\\uninstall.exe" -ArgumentList "/S" -Wait
          Write-Host "✓ Uninstallation completed"

      - name: Verify uninstallation
        shell: pwsh
        run: |
          if (Test-Path "$env:LOCALAPPDATA\\VidDoblaje\\VidDoblaje.exe") { throw "VidDoblaje.exe still exists" }
          Write-Host "✓ Uninstallation verified: no residue"

      - name: Upload VidDoblajeSetup.exe
        uses: actions/upload-artifact@v4
        with:
          name: VidDoblajeSetup-windows
          path: dist/Output/VidDoblajeSetup.exe
          retention-days: 30

      - name: Upload VidDoblaje.exe
        uses: actions/upload-artifact@v4
        with:
          name: VidDoblaje-windows
          path: dist/VidDoblaje/
          retention-days: 30
''')

# === LICENSE.txt ===
write("LICENSE.txt", """MIT License

Copyright (c) 2025 VidDoblaje

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

---

This installer bundles:
- Python runtime (PSF License)
- PySide6 / Qt6 (LGPLv3)
- faster-whisper (MIT)
- transformers (Apache 2.0)
- Piper TTS (MIT)
- SpeechBrain (Apache 2.0)
- FFmpeg (LGPL 2.1+)
""")

# === README.md ===
write("README.md", '''# VidDoblaje

**Traducción y doblaje automático de vídeos al español — 100% local**

## Instalación

1. Descarga `VidDoblajeSetup.exe`
2. Doble clic para instalar (no requiere admin)
3. Abre VidDoblaje desde el menú inicio
4. Pulsa **TRADUCIR Y DOBLAR AL ESPAÑOL**
5. Agrega un vídeo (drag & drop)
6. Espera el procesamiento
7. Obtén el vídeo final

## Características

- **Pipeline completo**: análisis → transcripción → diarización → traducción → TTS → sincronización → subtítulos → mezcla → exportación
- **100% local**: sin APIs en la nube
- **CPU y GPU**: detección automática
- **Diarización sin HF token**: speechbrain (Apache 2.0)
- **Auto-descarga de modelos**: First Run Wizard
- **Checkpoints**: reanuda desde el último punto
- **Temas**: oscuro / claro / auto
- **Formatos**: MP4, MKV entrada; MP4, MKV salida

## Modelos base (auto-descargados)

| Modelo | Función | Licencia |
|--------|---------|----------|
| whisper-base | ASR | MIT |
| opus-mt-en-es | Traducción | CC-BY-4.0 |
| piper-es_ES-davefx-medium | TTS | MIT |
| speechbrain-ecapa | Diarización | Apache-2.0 |

## Build

```bash
./scripts/build.sh
```

## Licencia

MIT — ver [LICENSE.txt](LICENSE.txt)
''')

# === Docs ===
write("docs/architecture.md", '''# Arquitectura

VidDoblaje sigue un patrón de pipeline con checkpoints. Cada stage puede fallar y reanudarse independientemente.

## Estructura

```
src/viddoblaje/
├── __main__.py          # Entry point
├── cli.py               # CLI mode
├── config.py            # Settings
├── pipeline.py          # Orquestador
├── core/
│   ├── hardware.py      # Detección HW
│   ├── project.py       # Modelo de datos
│   ├── checkpoint.py    # Checkpoints
│   ├── queue_manager.py # Cola
│   └── model_manager.py # Modelos IA
├── stages/
│   ├── analysis.py
│   ├── audio_extraction.py
│   ├── asr.py           # Whisper
│   ├── diarization.py   # speechbrain
│   ├── translation.py   # MarianMT
│   ├── tts.py           # Piper
│   ├── sync.py
│   ├── subtitles.py
│   ├── mix.py
│   └── export.py
├── ui/
│   ├── app.py
│   ├── main_window.py
│   ├── processor.py
│   ├── first_run.py     # Wizard
│   ├── model_manager_ui.py
│   ├── settings.py
│   └── translation_editor.py
└── utils/
    └── ffmpeg.py
```

## Pipeline

10 stages en orden: analysis → audio_extraction → transcription → diarization → translation → voice_generation → sync → subtitles → mix → export

Cada stage guarda un checkpoint. Si falla, reanuda desde el último válido.

## Diarización

Usa **speechbrain** (Apache 2.0) por defecto, sin requerir HF token.
pyannote 3.1 es opcional (mejor calidad pero requiere licencia HF).
''')

write("docs/licenses.md", '''# Licencias

| Componente | Licencia | Comercial |
|-----------|----------|-----------|
| VidDoblaje | MIT | ✅ |
| Python | PSF | ✅ |
| PySide6/Qt6 | LGPLv3 | ✅ |
| FFmpeg | LGPL 2.1+ | ✅ |
| faster-whisper | MIT | ✅ |
| transformers | Apache 2.0 | ✅ |
| Piper TTS | MIT | ✅ |
| SpeechBrain | Apache 2.0 | ✅ |
| Whisper modelos | MIT | ✅ |
| opus-mt modelos | CC-BY-4.0 | ✅ |
| pyannote 3.1 | CC-BY-NC-SA | ❌ No comercial |
| XTTS-v2 | CPML | ❌ No comercial |

pyannote y XTTS-v2 son **optativos** y requieren aceptación de licencia.
''')

write("docs/windows_ci.md", '''# Windows CI

GitHub Actions workflow en `.github/workflows/windows-ci.yml`.

## Pasos del workflow

1. Checkout code
2. Setup Python 3.11
3. Install dependencies
4. Install NSIS
5. Download FFmpeg (Windows LGPL)
6. Generate app icon
7. Run quick tests
8. Build VidDoblaje.exe (PyInstaller)
9. Verify PE32
10. Run smoke test
11. Build VidDoblajeSetup.exe (NSIS)
12. Install (silent /S)
13. Verify installation
14. Run installed VidDoblaje.exe
15. Uninstall (silent /S)
16. Verify no residue
17. Upload artifacts

## Activación

El workflow se ejecuta automáticamente al hacer push a `main`.
''')

print("Build scripts, NSIS, spec, workflow y docs creados.")
