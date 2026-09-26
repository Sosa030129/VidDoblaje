"""Stage: diarización con speechbrain (sin HF token)."""
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
