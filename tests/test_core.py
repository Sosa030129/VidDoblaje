"""Tests unitarios de infraestructura."""
from __future__ import annotations
from pathlib import Path
import pytest


def test_settings_singleton(settings):
    from viddoblaje.config import get_settings
    assert settings is get_settings()


def test_settings_dirs_created(settings):
    assert settings.user_dir.exists()
    assert settings.projects_dir.exists()
    assert settings.models_dir.exists()


def test_project_create(settings, tmp_path):
    from viddoblaje.core.project import Project, PROJECT_SUBDIRS
    src = tmp_path / "src.mp4"
    src.write_bytes(b"\x00" * 100)
    proj = Project.create(name="Test", source_video=src, base_dir=settings.projects_dir)
    assert proj.root.exists()
    for sub in PROJECT_SUBDIRS:
        assert (proj.root / sub).exists()
    proj2 = Project.load(proj.root)
    assert proj2.meta.id == proj.meta.id


def test_checkpoint_manager(settings, tmp_path):
    from viddoblaje.core.checkpoint import CheckpointManager
    mgr = CheckpointManager(tmp_path / "cp")
    assert not mgr.exists("analysis")
    mgr.save("analysis", 0, {}, {})
    assert mgr.exists("analysis")
    mgr.invalidate("analysis")
    assert not mgr.exists("analysis")


def test_hardware_detection():
    from viddoblaje.core.hardware import detect_hardware, HardwareProfile
    info = detect_hardware()
    assert info.cpu_cores_physical >= 1
    assert info.ram_total_mb > 0
    assert info.recommend_profile() in HardwareProfile


def test_model_manager_known_models(settings):
    from viddoblaje.core.model_manager import ModelManager, KNOWN_MODELS
    mgr = ModelManager(settings.models_dir)
    assert "whisper-base" in KNOWN_MODELS
    assert "opus-mt-en-es" in KNOWN_MODELS
    assert "piper-es_ES-davefx-medium" in KNOWN_MODELS
    assert "speechbrain-ecapa" in KNOWN_MODELS
    required = mgr.list_required_for_pipeline()
    assert "whisper-base" in required
    assert "speechbrain-ecapa" in required


def test_speechbrain_no_token_required():
    from viddoblaje.core.model_manager import KNOWN_MODELS
    sb = KNOWN_MODELS["speechbrain-ecapa"]
    assert not sb.requires_hf_token
    assert not sb.requires_license_acceptance
    assert sb.license == "Apache-2.0"


def test_xtts_requires_license():
    from viddoblaje.core.model_manager import KNOWN_MODELS
    xtts = KNOWN_MODELS["xtts-v2"]
    assert xtts.non_commercial_only
    assert xtts.requires_license_acceptance


def test_base_required_models():
    import re
    content = open("src/viddoblaje/ui/first_run.py").read()
    match = re.search(r'BASE_REQUIRED_MODELS\s*=\s*\[(.*?)\]', content, re.DOTALL)
    ids = re.findall(r'"([^"]+)"', match.group(1))
    assert "whisper-base" in ids
    assert "opus-mt-en-es" in ids
    assert "piper-es_ES-davefx-medium" in ids
    assert "speechbrain-ecapa" in ids
    assert "pyannote-3.1" not in ids
    assert "xtts-v2" not in ids


def test_segments_and_speakers():
    from viddoblaje.core.project import Segment, Speaker
    s = Segment(index=0, start_sec=0.0, end_sec=2.0, speaker_id="SPEAKER_001", text_original="Hello", text_spanish="Hola")
    d = s.to_dict()
    s2 = Segment.from_dict(d)
    assert s2.text_spanish == "Hola"
