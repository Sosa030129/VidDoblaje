"""Fixtures para tests."""
from __future__ import annotations
import os, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def tmp_user_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    import viddoblaje.config as cfg_mod
    cfg_mod._settings = None
    yield tmp_path
    cfg_mod._settings = None


@pytest.fixture
def settings(tmp_user_dir):
    from viddoblaje.config import get_settings
    return get_settings()


@pytest.fixture
def ffmpeg_available():
    from viddoblaje.utils.ffmpeg import get_ffmpeg
    try:
        get_ffmpeg()
        return True
    except Exception:
        return False
