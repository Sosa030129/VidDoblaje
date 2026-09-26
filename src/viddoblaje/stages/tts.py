"""Stage: generación de voz con Piper TTS."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger

log = get_logger(__name__)


def _resolve_piper_model(model_id: str, models_dir: Path) -> tuple:
    model_dir = models_dir / model_id
    if model_dir.exists() and model_dir.is_dir():
        onnx_files = list(model_dir.glob("*.onnx"))
        if onnx_files:
            onnx = onnx_files[0]
            json_cfg = onnx.with_suffix(onnx.suffix + ".json")
            if not json_cfg.exists():
                json_cfg = onnx.with_suffix(".json")
            if not json_cfg.exists():
                json_cfg = model_dir / f"{model_id}.json"
            return onnx, json_cfg
    onnx = models_dir / f"{model_id}.onnx"
    json_cfg = models_dir / f"{model_id}.onnx.json"
    if not json_cfg.exists():
        json_cfg = models_dir / f"{model_id}.json"
    return onnx, json_cfg


def _synthesize_piper(text: str, out_wav: Path, onnx_path: Path, json_path: Path, length_scale: float = 1.0) -> None:
    from piper import PiperVoice
    from piper.config import SynthesisConfig
    import wave
    voice = PiperVoice.load(str(onnx_path), config_path=str(json_path))
    syn_config = SynthesisConfig(length_scale=length_scale)
    chunks = voice.synthesize(text, syn_config=syn_config)
    with wave.open(str(out_wav), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(voice.config.sample_rate)
        for chunk in chunks:
            wav_file.writeframes(chunk.audio_int16_bytes)


def _estimate_length_scale(text: str, target_duration_sec: float) -> float:
    if target_duration_sec <= 0:
        return 1.0
    estimated_sec = max(1.0, len(text) / 14.0)
    scale = estimated_sec / target_duration_sec
    return max(0.7, min(1.4, scale))


def run(project: Project, voice_model_id: str = "piper-es_ES-davefx-medium", speaker_to_voice: Optional[dict] = None) -> dict:
    log.info("Stage: generación de voz (TTS={})", voice_model_id)
    if not project.meta.segments:
        raise RuntimeError("No hay segmentos para generar voz")
    from viddoblaje.config import get_settings
    settings = get_settings()
    if speaker_to_voice is None:
        available_voices = ["piper-es_ES-davefx-medium", "piper-es_ES-mls_9972-medium", "piper-es_ES-carlfm-x_low"]
        speaker_to_voice = {}
        for i, sp in enumerate(project.meta.speakers):
            speaker_to_voice[sp.id] = available_voices[i % len(available_voices)]
            sp.voice_profile = speaker_to_voice[sp.id]
    loaded_voices = {}
    for seg in project.meta.segments:
        voice_id = speaker_to_voice.get(seg.speaker_id, voice_model_id)
        if voice_id not in loaded_voices:
            onnx, json_cfg = _resolve_piper_model(voice_id, settings.models_dir)
            if not onnx.exists():
                raise FileNotFoundError(f"Modelo Piper no encontrado: {onnx}")
            loaded_voices[voice_id] = (onnx, json_cfg)
        onnx, json_cfg = loaded_voices[voice_id]
        out_wav = project.voice_dir(seg.speaker_id) / f"segment_{seg.index:04d}.wav"
        text = seg.text_spanish or seg.text_original
        if not text.strip():
            seg.voice_path = ""
            seg.status = "voiced"
            continue
        target_dur = seg.end_sec - seg.start_sec
        length_scale = _estimate_length_scale(text, target_dur)
        _synthesize_piper(text, out_wav, onnx, json_cfg, length_scale=length_scale)
        seg.voice_path = str(out_wav.relative_to(project.root))
        seg.status = "voiced"
    project.save()
    return {"method": "piper", "voice_model": voice_model_id, "num_segments": len(project.meta.segments)}
