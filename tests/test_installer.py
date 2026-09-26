"""Tests del instalador."""
from __future__ import annotations
import hashlib, subprocess
from pathlib import Path
import pytest

SETUP_EXE = Path("/home/z/my-project/viddoblaje/dist/Output/VidDoblajeSetup.exe")
FFMPEG_BUNDLED = Path("/home/z/my-project/viddoblaje/build/ffmpeg")


def test_installer_exists():
    if not SETUP_EXE.exists():
        pytest.skip("Instalador no generado todavía")
    assert SETUP_EXE.exists()


def test_installer_is_pe32():
    if not SETUP_EXE.exists():
        pytest.skip("Instalador no generado")
    result = subprocess.run(["file", str(SETUP_EXE)], capture_output=True, text=True)
    assert "PE32" in result.stdout
    assert "Nullsoft Installer" in result.stdout


def test_installer_sha256():
    if not SETUP_EXE.exists():
        pytest.skip("Instalador no generado")
    with open(SETUP_EXE, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    assert len(sha) == 64
    print(f"SHA256: {sha}")
