#!/bin/bash
# Crea todos los archivos del proyecto VidDoblaje de una vez
set -e
cd /home/z/my-project/viddoblaje

echo "Creando archivos del proyecto VidDoblaje..."

# === pyproject.toml ===
cat > pyproject.toml <<'TOML'
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "viddoblaje"
version = "1.0.0"
description = "Traducción y doblaje automático de vídeos al español — 100% local"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [{name = "VidDoblaje"}]

dependencies = [
    "PySide6>=6.6.0",
    "pydantic>=2.5.0",
    "loguru>=0.7.0",
    "tomli>=2.0.1; python_version < '3.11'",
    "tomli-w>=1.0.0",
    "requests>=2.31.0",
    "tqdm>=4.66.0",
    "numpy>=1.24.0",
    "psutil>=5.9.0",
    "ffmpeg-python>=0.2.0",
    "faster-whisper>=1.0.0",
    "transformers>=4.40.0,<4.45.0",
    "torch>=2.1.0",
    "torchaudio>=2.1.0",
    "sentencepiece>=0.2.0",
    "piper-tts>=1.2.0",
    "speechbrain>=1.0.0",
    "scikit-learn>=1.3.0",
    "soundfile>=0.12.0",
    "scipy>=1.11.0",
    "huggingface_hub>=0.20.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.4.0", "pytest-qt>=4.2.0", "pyinstaller>=6.0", "pefile", "pillow"]
cloning = ["coqui-tts==0.25.1"]

[project.scripts]
viddoblaje = "viddoblaje.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
viddoblaje = ["ui/themes/*.qss", "assets/*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "slow: tests que tardan más de 5 segundos",
    "gpu: tests que requieren GPU",
    "integration: tests de integración end-to-end",
    "needs_models: tests que requieren modelos descargados",
]
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py310"
TOML

# === requirements.txt ===
cat > requirements.txt <<'REQ'
PySide6>=6.6.0
pydantic>=2.5.0
loguru>=0.7.0
tomli>=2.0.1; python_version < '3.11'
tomli-w>=1.0.0
requests>=2.31.0
tqdm>=4.66.0
numpy>=1.24.0
psutil>=5.9.0
ffmpeg-python>=0.2.0
faster-whisper>=1.0.0
transformers>=4.40.0,<4.45.0
torch>=2.1.0
torchaudio>=2.1.0
sentencepiece>=0.2.0
piper-tts>=1.2.0
speechbrain>=1.0.0
scikit-learn>=1.3.0
soundfile>=0.12.0
scipy>=1.11.0
huggingface_hub>=0.20.0
pyinstaller>=6.0
pefile
pillow
pytest>=7.4.0
REQ

# === .gitignore ===
cat > .gitignore <<'GIT'
__pycache__/
*.pyc
.venv/
dist/
build/viddoblaje/
*.egg-info/
.pytest_cache/
*.mp4
*.wav
*.onnx
!tests/fixtures/*.mp4
build/ffmpeg/*.exe
build/ffmpeg/*.dll
GIT

echo "Archivos de configuración creados."
