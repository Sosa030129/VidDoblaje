#!/bin/bash
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
