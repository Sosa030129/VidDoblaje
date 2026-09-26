"""Stage: ASR (transcripción) con faster-whisper."""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from viddoblaje.core.project import Project, Segment
from viddoblaje.utils import get_logger

log = get_logger(__name__)

@dataclass
class TranscriptionResult:
    language: str
    language_prob: float
    duration_sec: float
    segments: list


def _resolve_model_path(model_id: str, models_dir: Path) -> str:
    local = models_dir / model_id
    if local.exists() and any(local.iterdir()):
        return str(local)
    mapping = {"whisper-tiny": "Systran/faster-whisper-tiny", "whisper-base": "Systran/faster-whisper-base",
               "whisper-small": "Systran/faster-whisper-small", "whisper-medium": "Systran/faster-whisper-medium",
               "whisper-large-v3": "Systran/faster-whisper-large-v3"}
    return mapping.get(model_id, model_id)


def run(project: Project, model_id: str = "whisper-base", language: Optional[str] = None,
        device: str = "auto", compute_type: str = "auto") -> dict:
    log.info("Stage: transcripción ASR (model={})", model_id)
    from faster_whisper import WhisperModel
    from viddoblaje.config import get_settings
    settings = get_settings()
    audio_path = project.audio_dir / "audio_16k_mono.wav"
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")
    model_path = _resolve_model_path(model_id, settings.models_dir)
    if device == "auto":
        from viddoblaje.core.hardware import get_device
        device = get_device("auto")
    fw_device = "cuda" if device.startswith("cuda") else "cpu"
    if compute_type == "auto":
        compute_type = "float16" if fw_device == "cuda" else "int8"
    log.info("Cargando Whisper: device={}, compute_type={}", fw_device, compute_type)
    model = WhisperModel(model_path, device=fw_device, compute_type=compute_type)
    segments_iter, info = model.transcribe(str(audio_path), language=language, vad_filter=True,
                                           vad_parameters=dict(min_silence_duration_ms=500, threshold=0.5),
                                           beam_size=5, word_timestamps=False)
    segments_data = []
    for seg in segments_iter:
        segments_data.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
    out_path = project.transcription_dir / "transcription.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"model": model_id, "language": info.language, "language_prob": info.language_probability,
                   "duration_sec": info.duration, "segments": segments_data}, f, indent=2, ensure_ascii=False)
    project.meta.segments = [Segment(index=i, start_sec=s["start"], end_sec=s["end"],
                                    speaker_id="SPEAKER_000", text_original=s["text"])
                           for i, s in enumerate(segments_data)]
    project.meta.source_language = info.language
    project.save()
    return {"language": info.language, "language_prob": info.language_probability,
            "num_segments": len(segments_data), "output": str(out_path.relative_to(project.root))}
