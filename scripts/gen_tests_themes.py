#!/usr/bin/env python3
"""Genera themes, tests, scripts, docs, GitHub workflow."""
from pathlib import Path
import os

BASE = Path("/home/z/my-project/viddoblaje")

def write(rel_path, content):
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  {rel_path}")

# === Themes ===
write("src/viddoblaje/ui/themes/dark.qss", """/* Tema oscuro */
QWidget { background-color: #1a1a1a; color: #e8eaed; font-family: "Segoe UI", sans-serif; font-size: 10pt; }
QMainWindow, QDialog { background-color: #1a1a1a; }
QMenuBar { background-color: #222; border-bottom: 1px solid #333; }
QMenuBar::item { padding: 6px 12px; }
QMenuBar::item:selected { background-color: #3a3a3a; border-radius: 4px; }
QMenu { background-color: #2a2a2a; border: 1px solid #444; padding: 4px; }
QMenu::item { padding: 6px 24px 6px 16px; border-radius: 4px; }
QMenu::item:selected { background-color: #4a7fff; color: white; }
QPushButton { background-color: #2a2a2a; color: #e8eaed; border: 1px solid #444; padding: 8px 16px; border-radius: 6px; min-height: 20px; }
QPushButton:hover { background-color: #3a3a3a; border-color: #5a5a5a; }
QPushButton:pressed { background-color: #1f1f1f; }
QPushButton:disabled { color: #666; background-color: #1f1f1f; }
QPushButton#primaryButton { background-color: #4a7fff; color: white; border: none; font-weight: 600; font-size: 11pt; padding: 12px 24px; }
QPushButton#primaryButton:hover { background-color: #5a8fff; }
QPushButton#primaryButton:pressed { background-color: #3a6fef; }
QPushButton#primaryButton:disabled { background-color: #2a3a5a; color: #666; }
QLineEdit, QTextEdit, QComboBox, QSpinBox { background-color: #2a2a2a; color: #e8eaed; border: 1px solid #444; padding: 6px 8px; border-radius: 4px; selection-background-color: #4a7fff; }
QTableWidget { background-color: #1f1f1f; alternate-background-color: #252525; gridline-color: #333; border: 1px solid #333; selection-background-color: #4a7fff; }
QHeaderView::section { background-color: #2a2a2a; padding: 6px 8px; border: none; border-right: 1px solid #333; border-bottom: 1px solid #333; font-weight: 600; }
QProgressBar { background-color: #2a2a2a; border: 1px solid #444; border-radius: 4px; text-align: center; height: 22px; }
QProgressBar::chunk { background-color: #4a7fff; border-radius: 3px; }
QLabel#titleLabel { font-size: 18pt; font-weight: 700; }
QLabel#subtitleLabel { font-size: 10pt; color: #999; }
QLabel#hintLabel { color: #777; font-size: 9pt; }
QFrame#dropZone { border: 2px dashed #555; border-radius: 12px; background-color: #1f1f1f; }
QFrame#dropZone[dragActive="true"] { border-color: #4a7fff; background-color: #1f2a3a; }
QStatusBar { background-color: #222; border-top: 1px solid #333; }
QToolBar { background-color: #222; border-bottom: 1px solid #333; spacing: 4px; padding: 4px; }
QListWidget { background-color: #1f1f1f; border: 1px solid #333; border-radius: 4px; }
QListWidget::item { padding: 8px 12px; }
QListWidget::item:selected { background-color: #4a7fff; color: white; }
""")

write("src/viddoblaje/ui/themes/light.qss", """/* Tema claro */
QWidget { background-color: #f5f5f5; color: #1a1a1a; font-family: "Segoe UI", sans-serif; font-size: 10pt; }
QMainWindow, QDialog { background-color: #f5f5f5; }
QMenuBar { background-color: #e8e8e8; border-bottom: 1px solid #ccc; }
QMenu { background-color: #fff; border: 1px solid #ccc; padding: 4px; }
QMenu::item:selected { background-color: #4a7fff; color: white; }
QPushButton { background-color: #fff; color: #1a1a1a; border: 1px solid #bbb; padding: 8px 16px; border-radius: 6px; }
QPushButton:hover { background-color: #eaeaea; }
QPushButton#primaryButton { background-color: #4a7fff; color: white; border: none; font-weight: 600; font-size: 11pt; padding: 12px 24px; }
QPushButton#primaryButton:hover { background-color: #3a6fef; }
QLineEdit, QComboBox, QSpinBox { background-color: white; color: #1a1a1a; border: 1px solid #bbb; padding: 6px 8px; border-radius: 4px; }
QTableWidget { background-color: white; alternate-background-color: #f9f9f9; gridline-color: #ddd; border: 1px solid #ccc; selection-background-color: #4a7fff; }
QHeaderView::section { background-color: #eaeaea; padding: 6px 8px; border: none; border-right: 1px solid #ccc; border-bottom: 1px solid #ccc; font-weight: 600; }
QProgressBar { background-color: #eaeaea; border: 1px solid #bbb; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background-color: #4a7fff; }
QLabel#titleLabel { font-size: 18pt; font-weight: 700; }
QLabel#subtitleLabel { font-size: 10pt; color: #666; }
QLabel#hintLabel { color: #888; font-size: 9pt; }
QFrame#dropZone { border: 2px dashed #888; border-radius: 12px; background-color: white; }
QFrame#dropZone[dragActive="true"] { border-color: #4a7fff; background-color: #eaf1ff; }
QStatusBar { background-color: #e8e8e8; border-top: 1px solid #ccc; }
QToolBar { background-color: #e8e8e8; border-bottom: 1px solid #ccc; spacing: 4px; padding: 4px; }
""")

# === Tests ===
write("tests/__init__.py", "")
write("tests/conftest.py", '''"""Fixtures para tests."""
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
''')

write("tests/test_core.py", '''"""Tests unitarios de infraestructura."""
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
    src.write_bytes(b"\\x00" * 100)
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
    match = re.search(r'BASE_REQUIRED_MODELS\\s*=\\s*\\[(.*?)\\]', content, re.DOTALL)
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
''')

write("tests/test_stages.py", '''"""Tests de stages."""
from __future__ import annotations
from pathlib import Path
import pytest


def test_subtitles_generation(settings, tmp_path):
    from viddoblaje.core.project import Project, Segment, Speaker
    src = tmp_path / "v.mp4"
    src.write_bytes(b"\\x00" * 100)
    project = Project.create(name="sub_test", source_video=src, base_dir=settings.projects_dir)
    project.meta.segments = [
        Segment(index=0, start_sec=0.0, end_sec=2.5, speaker_id="SPEAKER_001", text_original="Hello", text_spanish="Hola"),
        Segment(index=1, start_sec=2.5, end_sec=5.0, speaker_id="SPEAKER_002", text_original="Bye", text_spanish="Adiós"),
    ]
    project.meta.speakers = [Speaker(id="SPEAKER_001"), Speaker(id="SPEAKER_002")]
    project.save()
    from viddoblaje.stages.subtitles import write_srt, write_vtt
    srt = project.subtitles_dir / "test.srt"
    write_srt(project, srt)
    assert srt.exists()
    content = srt.read_text(encoding="utf-8")
    assert "Hola" in content
    assert "Adiós" in content


def test_translation_model_pick():
    from viddoblaje.stages.translation import pick_translation_model
    assert pick_translation_model("en") == "opus-mt-en-es"
    assert pick_translation_model("fr") == "opus-mt-fr-es"
    assert pick_translation_model("es") == ""


def test_pipeline_options():
    from viddoblaje.pipeline import PipelineOptions
    opts = PipelineOptions(asr_model="whisper-small", output_format="mkv", burn_subtitles=True)
    d = opts.to_dict()
    assert d["asr_model"] == "whisper-small"
    assert d["output_format"] == "mkv"
    assert d["burn_subtitles"] is True
''')

write("tests/test_integration.py", '''"""Tests de integración."""
from __future__ import annotations
import pytest


@pytest.mark.integration
@pytest.mark.needs_models
def test_pipeline_end_to_end(ffmpeg_available, settings, tmp_path):
    """Pipeline completo con modelos reales."""
    if not ffmpeg_available:
        pytest.skip("FFmpeg no disponible")
    import os
    shared = os.environ.get("VIDDOBLAJE_TEST_MODELS_DIR")
    if shared and os.path.isdir(shared):
        import shutil
        os.makedirs(os.path.dirname(settings.models_dir), exist_ok=True)
        if not settings.models_dir.exists():
            try:
                shutil.copytree(shared, settings.models_dir, symlinks=False)
            except FileExistsError:
                pass
    from viddoblaje.core.model_manager import ModelManager
    mgr = ModelManager(settings.models_dir)
    required = ["whisper-base", "opus-mt-en-es", "piper-es_ES-davefx-medium"]
    missing = [m for m in required if not mgr.is_installed(m)]
    if missing:
        pytest.skip(f"Faltan modelos: {missing}")
    from scripts.make_test_video import make_speech_like_video
    video = tmp_path / "test.mp4"
    make_speech_like_video(video, duration_sec=6.0)
    from viddoblaje.core.project import Project
    project = Project.create(name="e2e_test", source_video=video, base_dir=settings.projects_dir)
    from viddoblaje.pipeline import PipelineOptions, run as run_pipeline
    options = PipelineOptions(asr_model="whisper-base", tts_voice="piper-es_ES-davefx-medium")
    project = run_pipeline(project, options)
    assert project.meta.status == "completed"
    assert project.meta.output_video
    output = project.root / project.meta.output_video
    assert output.exists()
    assert output.stat().st_size > 0


@pytest.mark.integration
def test_checkpoints_persist(ffmpeg_available, settings, tmp_path):
    if not ffmpeg_available:
        pytest.skip("FFmpeg no disponible")
    from scripts.make_test_video import make_sine_video
    video = tmp_path / "test.mp4"
    make_sine_video(video, duration_sec=3.0)
    from viddoblaje.core.project import Project
    project = Project.create(name="cp_test", source_video=video, base_dir=settings.projects_dir)
    from viddoblaje.stages.analysis import run as analysis_run
    from viddoblaje.core.checkpoint import CheckpointManager
    import time
    cp_mgr = CheckpointManager(project.checkpoints_dir)
    t0 = time.time()
    result = analysis_run(project)
    cp_mgr.save("analysis", t0, {}, {"duration_sec": result.duration_sec})
    assert cp_mgr.exists("analysis")
    assert cp_mgr.last_completed() == "analysis"


def test_error_recovery(settings, tmp_path):
    from viddoblaje.core.project import Project, ProjectStatus
    from viddoblaje.core.checkpoint import CheckpointManager
    src = tmp_path / "v.mp4"
    src.write_bytes(b"\\x00" * 100)
    project = Project.create(name="err", source_video=src, base_dir=settings.projects_dir)
    try:
        raise RuntimeError("simulated")
    except Exception as e:
        project.set_error(str(e))
    assert project.meta.status == ProjectStatus.FAILED.value
''')

write("tests/test_installer.py", '''"""Tests del instalador."""
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
''')

write("tests/test_model_flow.py", '''"""Tests del flujo de modelos."""
from __future__ import annotations
import os, sys, re
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_base_required_models_list():
    content = open(str(Path(__file__).parent.parent / "src" / "viddoblaje" / "ui" / "first_run.py")).read()
    match = re.search(r'BASE_REQUIRED_MODELS\\s*=\\s*\\[(.*?)\\]', content, re.DOTALL)
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
''')

# === make_test_video.py ===
write("scripts/make_test_video.py", '''"""Genera vídeos sintéticos para tests."""
from __future__ import annotations
import argparse
from pathlib import Path
from viddoblaje.utils.ffmpeg import run_ffmpeg


def make_sine_video(out_path, duration_sec=5.0, freq=440.0, color="blue"):
    run_ffmpeg(["-y", "-f", "lavfi", "-i", f"color=c={color}:s=640x360:d={duration_sec}:r=25",
                "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration_sec}:sample_rate=16000",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_path)])


def make_speech_like_video(out_path, duration_sec=8.0):
    import subprocess
    audio = out_path.parent / "_speech_audio.wav"
    filter_complex = f"sine=frequency=200:duration={duration_sec}:sample_rate=16000,volume='0.5+0.5*sin(2*PI*3*t)':eval=frame"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", filter_complex, "-t", str(duration_sec), str(audio)],
                   check=True, capture_output=True)
    run_ffmpeg(["-y", "-f", "lavfi", "-i", f"color=c=red:s=640x360:d={duration_sec}:r=25",
                "-i", str(audio), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
                "-c:a", "aac", "-b:a", "128k", "-shortest", str(out_path)])
    audio.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Genera vídeos de prueba")
    parser.add_argument("--out-dir", default="tests/fixtures")
    parser.add_argument("--speech", action="store_true")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.speech:
        p = out_dir / "test_speech.mp4"
        make_speech_like_video(p, duration_sec=6.0)
        print(f"OK: {p}")
    else:
        p = out_dir / "test_short.mp4"
        make_sine_video(p, duration_sec=5.0)
        print(f"OK: {p}")


if __name__ == "__main__":
    main()
''')

print("Themes, tests y scripts creados.")
