"""Tests del flujo de modelos."""
from __future__ import annotations
import os, sys, re
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_base_required_models_list():
    content = open(str(Path(__file__).parent.parent / "src" / "viddoblaje" / "ui" / "first_run.py")).read()
    match = re.search(r'BASE_REQUIRED_MODELS\s*=\s*\[(.*?)\]', content, re.DOTALL)
    ids = re.findall(r'"([^"]+)"', match.group(1))
    assert "whisper-base" in ids
    assert "opus-mt-en-es" in ids
    assert "piper-es_ES-davefx-medium" in ids
    assert "speechbrain-ecapa" in ids
    assert "pyannote-3.1" not in ids
    assert "xtts-v2" not in ids


def test_no_hf_token_required():
    content = open(str(Path(__file__).parent.parent / "src" / "viddoblaje" / "config.py")).read()
    assert 'hf_token: str = ""' in content


def test_diarization_uses_speechbrain_first():
    content = open(str(Path(__file__).parent.parent / "src" / "viddoblaje" / "stages" / "diarization.py")).read()
    assert "_try_speechbrain" in content
    assert 'prefer_method' in content
