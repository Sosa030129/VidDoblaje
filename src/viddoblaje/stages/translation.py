"""Stage: traducción al español con MarianMT."""
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
