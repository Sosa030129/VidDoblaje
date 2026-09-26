"""Tests de integración."""
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
    src.write_bytes(b"\x00" * 100)
    project = Project.create(name="err", source_video=src, base_dir=settings.projects_dir)
    try:
        raise RuntimeError("simulated")
    except Exception as e:
        project.set_error(str(e))
    assert project.meta.status == ProjectStatus.FAILED.value
