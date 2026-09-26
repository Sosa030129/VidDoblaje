"""Stage: exportación final."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import run_ffmpeg

log = get_logger(__name__)


def run(project, output_format="mp4", video_codec="libx264", audio_codec="aac",
        burn_subtitles=False, subtitles_file=None, crf=20, preset="medium"):
    log.info("Stage: exportación final")
    source_video = Path(project.meta.source_video)
    final_mix = project.audio_dir / "final_mix.wav"
    if not final_mix.exists():
        raise FileNotFoundError(f"Mezcla final no encontrada: {final_mix}")
    if output_format not in ("mp4", "mkv"):
        raise ValueError(f"Formato no soportado: {output_format}")
    out_name = Path(source_video).stem + f"_ES.{output_format}"
    out_path = project.renders_dir / out_name
    args = ["-y", "-i", str(source_video), "-i", str(final_mix), "-map", "0:v:0", "-map", "1:a:0"]
    vf_filters = []
    if burn_subtitles:
        if subtitles_file is None:
            subtitles_file = project.subtitles_dir / "subtitles.srt"
        if subtitles_file.exists():
            sub_path_escaped = str(subtitles_file.absolute()).replace("\\", "/").replace(":", "\\:")
            vf_filters.append(f"subtitles='{sub_path_escaped}'")
    if vf_filters:
        args += ["-vf", ",".join(vf_filters)]
    args += ["-c:v", video_codec, "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p",
             "-c:a", audio_codec, "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-metadata", "title=VidDoblaje", "-metadata", "language=spa"]
    if output_format == "mp4":
        args += ["-movflags", "+faststart"]
    args.append(str(out_path))
    run_ffmpeg(args)
    project.meta.output_video = str(out_path.relative_to(project.root))
    project.save()
    return {"output": str(out_path.relative_to(project.root)), "format": output_format}
