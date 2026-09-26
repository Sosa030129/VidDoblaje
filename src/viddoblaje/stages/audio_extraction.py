"""Stage: extracción de audio."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import run_ffmpeg

log = get_logger(__name__)

def run(project: Project) -> dict:
    log.info("Stage: extracción de audio")
    source = Path(project.meta.source_video)
    wav_16k = project.audio_dir / "audio_16k_mono.wav"
    wav_48k = project.audio_dir / "audio_48k_stereo.wav"
    if not wav_16k.exists():
        run_ffmpeg(["-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav_16k)])
    if not wav_48k.exists():
        run_ffmpeg(["-y", "-i", str(source), "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(wav_48k)])
    return {"audio_16k": str(wav_16k.relative_to(project.root)), "audio_48k": str(wav_48k.relative_to(project.root))}
