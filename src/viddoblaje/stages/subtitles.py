"""Stage: generación de subtítulos SRT y VTT."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger

log = get_logger(__name__)


def _format_srt(sec):
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = int(sec % 60); ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_vtt(sec):
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = int(sec % 60); ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def write_srt(project, out_path, use_spanish=True):
    lines = []
    for i, seg in enumerate(project.meta.segments, start=1):
        text = seg.text_spanish if use_spanish else seg.text_original
        if not text.strip():
            continue
        lines.append(str(i))
        lines.append(f"{_format_srt(seg.start_sec)} --> {_format_srt(seg.end_sec)}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_vtt(project, out_path, use_spanish=True):
    lines = ["WEBVTT", ""]
    for seg in project.meta.segments:
        text = seg.text_spanish if use_spanish else seg.text_original
        if not text.strip():
            continue
        lines.append(f"{_format_vtt(seg.start_sec)} --> {_format_vtt(seg.end_sec)}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def run(project, formats=None):
    log.info("Stage: subtítulos")
    if formats is None:
        formats = ["srt", "vtt"]
    outputs = []
    for fmt in formats:
        if fmt == "srt":
            out = project.subtitles_dir / "subtitles.srt"
            write_srt(project, out)
        elif fmt == "vtt":
            out = project.subtitles_dir / "subtitles.vtt"
            write_vtt(project, out)
        else:
            continue
        outputs.append(str(out.relative_to(project.root)))
    return {"formats": formats, "outputs": outputs, "num_entries": len(project.meta.segments)}
