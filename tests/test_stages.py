"""Tests de stages."""
from __future__ import annotations
from pathlib import Path
import pytest


def test_subtitles_generation(settings, tmp_path):
    from viddoblaje.core.project import Project, Segment, Speaker
    src = tmp_path / "v.mp4"
    src.write_bytes(b"\x00" * 100)
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
