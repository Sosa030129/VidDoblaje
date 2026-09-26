"""Stage: análisis del vídeo fuente."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import probe_video, get_video_duration

log = get_logger(__name__)

@dataclass
class VideoAnalysis:
    duration_sec: float
    has_audio: bool
    has_video: bool
    video_codec: str = ""
    audio_codec: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    bitrate_kbps: int = 0
    estimated_extra_disk_mb: int = 0


def estimate_disk_required(duration_sec: float) -> int:
    minutes = duration_sec / 60
    return int(minutes * (1.5 + 0.1 + 2.0 + 30.0 + 5.0))


def check_disk_space(required_mb: int, target_dir: Path) -> tuple:
    try:
        import psutil
        du = psutil.disk_usage(str(target_dir))
        free_mb = du.free // (1024 * 1024)
        return free_mb >= required_mb, free_mb
    except Exception:
        return True, 0


def run(project: Project) -> VideoAnalysis:
    log.info("Stage: análisis de vídeo")
    source = Path(project.meta.source_video)
    if not source.exists():
        raise FileNotFoundError(f"Vídeo fuente no encontrado: {source}")
    info = probe_video(source)
    duration = get_video_duration(source)
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    fps = 0.0
    if "avg_frame_rate" in video_stream:
        try:
            num, den = video_stream["avg_frame_rate"].split("/")
            fps = float(num) / float(den) if float(den) else 0.0
        except Exception:
            pass
    analysis = VideoAnalysis(
        duration_sec=duration, has_video=bool(video_stream), has_audio=bool(audio_stream),
        video_codec=video_stream.get("codec_name", ""), audio_codec=audio_stream.get("codec_name", ""),
        width=int(video_stream.get("width", 0)), height=int(video_stream.get("height", 0)),
        fps=fps, bitrate_kbps=int(info.get("format", {}).get("bit_rate", 0)) // 1000,
        estimated_extra_disk_mb=estimate_disk_required(duration),
    )
    project.meta.duration_sec = duration
    if not analysis.has_audio:
        log.warning("El vídeo no tiene pista de audio.")
    required_mb = analysis.estimated_extra_disk_mb
    ok, free_mb = check_disk_space(required_mb, project.root)
    if not ok:
        raise RuntimeError(f"Espacio insuficiente. Necesarios ~{required_mb} MB, disponibles {free_mb} MB")
    return analysis
