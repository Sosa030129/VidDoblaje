"""Stage opcional: separación de audio con Demucs."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import run_ffmpeg

log = get_logger(__name__)


def run(project, model_name="htdemucs"):
    log.info("Stage opcional: separación de audio (Demucs - {})", model_name)
    audio_in = project.audio_dir / "audio_48k_stereo.wav"
    if not audio_in.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_in}")
    output_dir = project.cache_dir / "demucs"
    output_dir.mkdir(parents=True, exist_ok=True)
    import torch
    from demucs.separate import separate
    from demucs.pretrained import get_model
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = get_model(model_name)
    model.to(device)
    separate(model=model, input=str(audio_in), output=str(output_dir), device=device, verbose=False)
    audio_name = audio_in.stem
    stem_dir = output_dir / audio_name
    if not stem_dir.exists():
        raise RuntimeError(f"Salida de Demucs no encontrada: {stem_dir}")
    vocals_path = stem_dir / "vocals.wav"
    no_vocals_path = project.audio_dir / "no_vocals.wav"
    drums = stem_dir / "drums.wav"
    bass = stem_dir / "bass.wav"
    other = stem_dir / "other.wav"
    inputs = []
    for p in (drums, bass, other):
        if p.exists():
            inputs += ["-i", str(p)]
    if not inputs:
        raise RuntimeError("Stems no encontrados")
    filter_parts = []
    idx = 0
    for i, p in enumerate((drums, bass, other)):
        if p.exists():
            filter_parts.append(f"[{i}:a]")
            idx += 1
    filter_complex = "".join(filter_parts) + f"amix=inputs={idx}:duration=longest[a]"
    run_ffmpeg(["-y", *inputs, "-filter_complex", filter_complex, "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(no_vocals_path)])
    return {"vocals_path": str(vocals_path.relative_to(project.root)) if vocals_path.exists() else "",
            "no_vocals_path": str(no_vocals_path.relative_to(project.root))}
