#!/usr/bin/env python3
"""Genera todos los stages del pipeline."""
from pathlib import Path

BASE = Path("/home/z/my-project/viddoblaje")

def write(rel_path, content):
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  {rel_path}")

write("src/viddoblaje/stages/__init__.py", '"""Stages del pipeline VidDoblaje."""\n')

# analysis.py
write("src/viddoblaje/stages/analysis.py", '''"""Stage: análisis del vídeo fuente."""
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
''')

# audio_extraction.py
write("src/viddoblaje/stages/audio_extraction.py", '''"""Stage: extracción de audio."""
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
''')

# asr.py
write("src/viddoblaje/stages/asr.py", '''"""Stage: ASR (transcripción) con faster-whisper."""
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
''')

# diarization.py
write("src/viddoblaje/stages/diarization.py", '''"""Stage: diarización con speechbrain (sin HF token)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger

log = get_logger(__name__)


def _try_speechbrain(project: Project, audio_path: Path) -> Optional[dict]:
    try:
        import torch
        import numpy as np
        import soundfile as sf
        from speechbrain.inference.speaker import EncoderClassifier
        from sklearn.cluster import AgglomerativeClustering
        from viddoblaje.config import get_settings
        settings = get_settings()
        model_path = settings.models_dir / "speechbrain-ecapa"
        log.info("Cargando speechbrain ECAPA desde {}...", model_path)
        if model_path.exists() and any(model_path.iterdir()):
            classifier = EncoderClassifier.from_hparams(source=str(model_path), hparams_file="hyperparams.yaml", savedir=str(model_path))
        else:
            classifier = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir=str(model_path))
        wav_np, sr = sf.read(str(audio_path))
        wav = torch.from_numpy(wav_np).float()
        if wav.dim() == 1:
            wav = wav.unsqueeze(0)
        if sr != 16000:
            from scipy.signal import resample_poly
            wav_np = resample_poly(wav_np, 16000, sr)
            wav = torch.from_numpy(wav_np).float().unsqueeze(0)
            sr = 16000
        win_sec, hop_sec = 3.0, 1.5
        win_samples = int(win_sec * sr)
        hop_samples = int(hop_sec * sr)
        embeddings = []
        timestamps = []
        for start in range(0, max(1, wav.shape[1] - win_samples), hop_samples):
            chunk = wav[:, start:start + win_samples]
            if chunk.shape[1] < sr * 0.5:
                continue
            with torch.no_grad():
                emb = classifier.encode_batch(chunk)
            embeddings.append(emb.squeeze().cpu().numpy())
            timestamps.append((start / sr, (start + win_samples) / sr))
        if not embeddings:
            return None
        X = np.stack(embeddings)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        X = X / np.maximum(norms, 1e-8)
        best_k, best_score = 1, -1
        max_speakers = min(8, len(X) // 2)
        for k in range(2, max_speakers + 1):
            try:
                labels = AgglomerativeClustering(n_clusters=k).fit_predict(X)
                from sklearn.metrics import silhouette_score
                score = silhouette_score(X, labels)
                if score > best_score:
                    best_score, best_k = score, k
            except Exception:
                continue
        labels = AgglomerativeClustering(n_clusters=best_k).fit_predict(X)
        turns = [{"start": float(s), "end": float(e), "speaker": f"SPEAKER_{int(l)+1:03d}"}
                 for (s, e), l in zip(timestamps, labels)]
        turns = _merge_turns(turns)
        speakers = sorted({t["speaker"] for t in turns})
        log.info("speechbrain: {} clusters (silhouette={:.2f})", best_k, best_score)
        return {"method": "speechbrain-ecapa", "turns": turns, "speakers": speakers}
    except Exception as e:
        log.warning("speechbrain falló: {}", e)
        return None


def _merge_turns(turns: list) -> list:
    if not turns:
        return []
    merged = [turns[0].copy()]
    for t in turns[1:]:
        last = merged[-1]
        if t["speaker"] == last["speaker"] and t["start"] - last["end"] < 1.0:
            last["end"] = t["end"]
        else:
            merged.append(t.copy())
    return merged


def _fallback_single_speaker(project: Project) -> dict:
    log.warning("Sin diarización disponible. Usando un único hablante SPEAKER_001.")
    return {"method": "single-speaker", "turns": [{"start": 0.0, "end": project.meta.duration_sec, "speaker": "SPEAKER_001"}], "speakers": ["SPEAKER_001"]}


def run(project: Project, hf_token: str = "", prefer_method: str = "auto") -> dict:
    log.info("Stage: diarización (prefer_method={})", prefer_method)
    audio_path = project.audio_dir / "audio_16k_mono.wav"
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio no encontrado: {audio_path}")
    result = _try_speechbrain(project, audio_path)
    if result is None:
        result = _fallback_single_speaker(project)
    out_path = project.speakers_dir / "diarization.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    turns = result["turns"]
    for seg in project.meta.segments:
        best_speaker = "SPEAKER_001"
        best_overlap = 0
        for turn in turns:
            overlap = max(0, min(seg.end_sec, turn["end"]) - max(seg.start_sec, turn["start"]))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn["speaker"]
        seg.speaker_id = best_speaker
    for spk in result["speakers"]:
        project.add_speaker(spk)
    project.save()
    return {"method": result["method"], "num_speakers": len(result["speakers"]),
            "output": str(out_path.relative_to(project.root))}
''')

# translation.py
write("src/viddoblaje/stages/translation.py", '''"""Stage: traducción al español con MarianMT."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger

log = get_logger(__name__)

LANGUAGE_TO_MODEL = {"en": "opus-mt-en-es", "fr": "opus-mt-fr-es", "de": "opus-mt-de-es",
                     "it": "opus-mt-it-es", "pt": "opus-mt-pt-es"}


def pick_translation_model(source_language: str) -> str:
    if source_language == "es":
        return ""
    return LANGUAGE_TO_MODEL.get(source_language, "opus-mt-mul-es")


def run(project: Project, model_id: Optional[str] = None, batch_size: int = 8) -> dict:
    log.info("Stage: traducción al español")
    if not project.meta.segments:
        raise RuntimeError("No hay segmentos para traducir")
    src_lang = project.meta.source_language or "en"
    if src_lang == "es":
        for seg in project.meta.segments:
            seg.text_spanish = seg.text_original
        project.save()
        _save_translations(project)
        return {"method": "passthrough", "num_segments": len(project.meta.segments)}
    if model_id is None:
        model_id = pick_translation_model(src_lang)
    log.info("Modelo de traducción: {} (src={})", model_id, src_lang)
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    from viddoblaje.config import get_settings
    settings = get_settings()
    model_path = settings.models_dir / model_id
    model_src = str(model_path) if model_path.exists() and any(model_path.iterdir()) else f"Helsinki-NLP/{model_id}"
    if not (model_path.exists() and any(model_path.iterdir())):
        model_src = f"Helsinki-NLP/{model_id}"
    tokenizer = AutoTokenizer.from_pretrained(model_src)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_src)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    model.eval()
    texts = [seg.text_original for seg in project.meta.segments]
    translated = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        with torch.no_grad():
            inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)
            output = model.generate(**inputs, max_length=512, num_beams=4)
            decoded = tokenizer.batch_decode(output, skip_special_tokens=True)
            translated.extend([t.strip() for t in decoded])
    for seg, txt in zip(project.meta.segments, translated):
        seg.text_spanish = txt
    project.save()
    _save_translations(project)
    return {"method": "marianmt", "model": model_id, "source_language": src_lang, "num_segments": len(translated)}


def _save_translations(project: Project) -> None:
    import csv
    data = [{"index": s.index, "start": s.start_sec, "end": s.end_sec, "speaker": s.speaker_id,
             "original": s.text_original, "spanish": s.text_spanish} for s in project.meta.segments]
    out_json = project.translations_dir / "translations.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    out_csv = project.translations_dir / "translations.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "start", "end", "speaker", "original", "spanish"])
        for row in data:
            w.writerow([row["index"], f"{row['start']:.2f}", f"{row['end']:.2f}", row["speaker"], row["original"], row["spanish"]])
''')

# tts.py
write("src/viddoblaje/stages/tts.py", '''"""Stage: generación de voz con Piper TTS."""
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
''')

# sync.py
write("src/viddoblaje/stages/sync.py", '''"""Stage: sincronización temporal."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import run_ffmpeg, probe_video

log = get_logger(__name__)


def _get_wav_duration(path: Path) -> float:
    try:
        info = probe_video(path)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        try:
            return path.stat().st_size / 32.0
        except Exception:
            return 0.0


def _time_stretch(input_wav, output_wav, target_duration_sec, current_duration_sec):
    if current_duration_sec <= 0 or target_duration_sec <= 0:
        run_ffmpeg(["-y", "-i", str(input_wav), "-c", "copy", str(output_wav)])
        return
    ratio = current_duration_sec / target_duration_sec
    if abs(ratio - 1.0) < 0.05:
        run_ffmpeg(["-y", "-i", str(input_wav), "-c", "copy", str(output_wav)])
        return
    run_ffmpeg(["-y", "-i", str(input_wav), "-filter:a", f"atempo={ratio:.4f}", "-vn", str(output_wav)])


def _pad_silence(input_wav, output_wav, pad_start_sec, pad_end_sec):
    if pad_start_sec <= 0 and pad_end_sec <= 0:
        run_ffmpeg(["-y", "-i", str(input_wav), "-c", "copy", str(output_wav)])
        return
    parts = []
    if pad_start_sec > 0:
        sil_start = output_wav.parent / "_silence_start.wav"
        run_ffmpeg(["-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=16000", "-t", f"{pad_start_sec:.3f}", str(sil_start)])
        parts.append(sil_start)
    parts.append(input_wav)
    if pad_end_sec > 0:
        sil_end = output_wav.parent / "_silence_end.wav"
        run_ffmpeg(["-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=16000", "-t", f"{pad_end_sec:.3f}", str(sil_end)])
        parts.append(sil_end)
    concat_file = output_wav.parent / "_concat.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p.absolute()}\\n'")
    run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_wav)])
    for p in parts:
        if p != input_wav:
            try: p.unlink()
            except Exception: pass
    try: concat_file.unlink()
    except Exception: pass


def run(project: Project) -> dict:
    log.info("Stage: sincronización temporal")
    synced_dir = project.audio_dir / "synced_voices"
    synced_dir.mkdir(exist_ok=True)
    too_long_count = 0
    for seg in project.meta.segments:
        if not seg.voice_path:
            continue
        in_wav = project.root / seg.voice_path
        if not in_wav.exists():
            continue
        target_dur = seg.end_sec - seg.start_sec
        current_dur = _get_wav_duration(in_wav)
        out_wav = synced_dir / f"seg_{seg.index:04d}.wav"
        if current_dur > target_dur * 1.05:
            if current_dur > target_dur * 1.5:
                too_long_count += 1
            _time_stretch(in_wav, out_wav, target_dur, current_dur)
        elif current_dur < target_dur * 0.95:
            diff = target_dur - current_dur
            _pad_silence(in_wav, out_wav, diff / 2, diff / 2)
        else:
            run_ffmpeg(["-y", "-i", str(in_wav), "-c", "copy", str(out_wav)])
        seg.voice_path = str(out_wav.relative_to(project.root))
        seg.status = "synced"
    if too_long_count > 0:
        log.warning("{} segmentos requirieron time-stretch agresivo", too_long_count)
    project.save()
    return {"num_synced": len(project.meta.segments), "too_long_count": too_long_count}
''')

# subtitles.py
write("src/viddoblaje/stages/subtitles.py", '''"""Stage: generación de subtítulos SRT y VTT."""
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
    out_path.write_text("\\n".join(lines), encoding="utf-8")


def write_vtt(project, out_path, use_spanish=True):
    lines = ["WEBVTT", ""]
    for seg in project.meta.segments:
        text = seg.text_spanish if use_spanish else seg.text_original
        if not text.strip():
            continue
        lines.append(f"{_format_vtt(seg.start_sec)} --> {_format_vtt(seg.end_sec)}")
        lines.append(text)
        lines.append("")
    out_path.write_text("\\n".join(lines), encoding="utf-8")


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
''')

# mix.py
write("src/viddoblaje/stages/mix.py", '''"""Stage: mezcla de audio."""
from __future__ import annotations
from pathlib import Path
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger
from viddoblaje.utils.ffmpeg import run_ffmpeg, get_video_duration

log = get_logger(__name__)


def _build_concat_list(segments, project):
    concat_file = project.audio_dir / "_voices_concat.txt"
    segments_dir = project.audio_dir / "synced_voices"
    silence_dir = project.cache_dir / "silences"
    silence_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    last_end = 0.0
    for seg in segments:
        if not seg.voice_path:
            continue
        voice = project.root / seg.voice_path
        gap = seg.start_sec - last_end
        if gap > 0.05:
            sil_path = silence_dir / f"sil_{int(last_end*1000):08d}.wav"
            if not sil_path.exists():
                run_ffmpeg(["-y", "-f", "lavfi", "-i", f"anullsrc=channel_layout=mono:sample_rate=16000", "-t", f"{gap:.3f}", str(sil_path)])
            entries.append(sil_path)
        entries.append(voice)
        last_end = seg.end_sec
    with open(concat_file, "w", encoding="utf-8") as f:
        for p in entries:
            f.write(f"file '{p.absolute()}\\n'")
    return concat_file


def run(project, mix_original_audio=True, voice_gain_db=0.0, original_gain_db=-6.0, normalize=True):
    log.info("Stage: mezcla de audio")
    segments = [s for s in project.meta.segments if s.voice_path]
    if not segments:
        raise RuntimeError("No hay segmentos con voz generada para mezclar")
    concat_file = _build_concat_list(segments, project)
    voices_track = project.audio_dir / "voices_full.wav"
    run_ffmpeg(["-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(voices_track)])
    voices_48k = project.audio_dir / "voices_48k.wav"
    run_ffmpeg(["-y", "-i", str(voices_track), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(voices_48k)])
    final_mix = project.audio_dir / "final_mix.wav"
    audio_48k = project.audio_dir / "audio_48k_stereo.wav"
    if mix_original_audio and audio_48k.exists():
        inputs = ["-i", str(voices_48k), "-i", str(audio_48k)]
        filter_complex = f"[0:a]volume={voice_gain_db}dB[v];[1:a]volume={original_gain_db}dB[o];[v][o]amix=inputs=2:duration=longest:dropout_transition=0[a]"
        run_ffmpeg(["-y", *inputs, "-filter_complex", filter_complex, "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(final_mix)])
    else:
        run_ffmpeg(["-y", "-i", str(voices_48k), "-c", "copy", str(final_mix)])
    if normalize:
        normalized = project.audio_dir / "final_mix_norm.wav"
        run_ffmpeg(["-y", "-i", str(final_mix), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(normalized)])
        final_mix.unlink()
        normalized.rename(final_mix)
    for tmp in [voices_track, voices_48k, concat_file]:
        try: tmp.unlink()
        except Exception: pass
    import shutil
    silence_dir = project.cache_dir / "silences"
    if silence_dir.exists():
        shutil.rmtree(silence_dir, ignore_errors=True)
    return {"output": str(final_mix.relative_to(project.root)), "duration_sec": get_video_duration(final_mix)}
''')

# export.py
write("src/viddoblaje/stages/export.py", '''"""Stage: exportación final."""
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
            sub_path_escaped = str(subtitles_file.absolute()).replace("\\\\", "/").replace(":", "\\\\:")
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
''')

# voice_cloning.py
write("src/viddoblaje/stages/voice_cloning.py", '''"""Stage opcional: clonación de voz con XTTS v2 (CPML, no-comercial)."""
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
''')

# audio_separation.py
write("src/viddoblaje/stages/audio_separation.py", '''"""Stage opcional: separación de audio con Demucs."""
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
''')

print("Stages creados.")
