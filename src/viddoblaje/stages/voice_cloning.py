"""Stage opcional: clonación de voz con XTTS v2 (CPML, no-comercial)."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger

log = get_logger(__name__)


def _extract_speaker_samples(project, speaker_id, min_duration_sec=6.0):
    import json
    speaker_dir = project.speaker_dir(speaker_id)
    samples_dir = speaker_dir / "samples"
    samples_dir.mkdir(exist_ok=True)
    audio_path = project.audio_dir / "audio_16k_mono.wav"
    if not audio_path.exists():
        return []
    dia_path = project.speakers_dir / "diarization.json"
    if not dia_path.exists():
        return []
    with open(dia_path, "r", encoding="utf-8") as f:
        diarization = json.load(f)
    turns = [t for t in diarization.get("turns", []) if t["speaker"] == speaker_id]
    if not turns:
        return []
    from viddoblaje.utils.ffmpeg import run_ffmpeg
    samples = []
    accumulated = 0.0
    for i, turn in enumerate(turns):
        dur = turn["end"] - turn["start"]
        if dur < 1.0:
            continue
        sample_path = samples_dir / f"sample_{i:03d}.wav"
        if not sample_path.exists():
            try:
                run_ffmpeg(["-y", "-i", str(audio_path), "-ss", str(turn["start"]), "-to", str(turn["end"]), "-c", "copy", str(sample_path)])
            except Exception:
                continue
        samples.append(sample_path)
        accumulated += dur
        if accumulated >= min_duration_sec:
            break
    return samples


def run(project, speaker_id=None, min_sample_duration_sec=6.0, language="es"):
    log.info("Stage opcional: clonación de voz XTTS v2")
    log.warning("XTTS-v2 es CPML — uso NO COMERCIAL únicamente.")
    from viddoblaje.config import get_settings
    settings = get_settings()
    xtts_path = settings.models_dir / "xtts-v2"
    if not xtts_path.exists() or not any(xtts_path.iterdir()):
        raise RuntimeError("Modelo XTTS-v2 no descargado.")
    import torch
    from TTS.api import TTS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("Cargando XTTS-v2 desde {} (device={})", xtts_path, device)
    tts = TTS(model_path=str(xtts_path), config_path=str(xtts_path / "config.json")).to(device)
    speakers = project.meta.speakers if speaker_id is None else [s for s in project.meta.speakers if s.id == speaker_id]
    results = {}
    for sp in speakers:
        samples = _extract_speaker_samples(project, sp.id, min_sample_duration_sec)
        if not samples:
            results[sp.id] = {"status": "fallback", "reason": "no_samples"}
            continue
        sp_dir = project.voice_dir(sp.id)
        cloned_count = 0
        for seg in project.meta.segments:
            if seg.speaker_id != sp.id:
                continue
            if not seg.text_spanish.strip():
                continue
            out_wav = sp_dir / f"cloned_{seg.index:04d}.wav"
            if not out_wav.exists():
                try:
                    tts.tts_to_file(text=seg.text_spanish, speaker_wav=str(samples[0]), language=language, file_path=str(out_wav))
                    cloned_count += 1
                except Exception as e:
                    log.error("Fallo clonando seg {} de {}: {}", seg.index, sp.id, e)
                    continue
            seg.voice_path = str(out_wav.relative_to(project.root))
            seg.status = "voiced_cloned"
        sp.voice_profile = "xtts-v2"
        results[sp.id] = {"status": "cloned", "segments": cloned_count}
    project.save()
    return {"speakers": results}
