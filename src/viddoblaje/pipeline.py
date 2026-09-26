"""Orquestador del pipeline VidDoblaje."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Callable, Optional

from viddoblaje.config import get_settings
from viddoblaje.core import CheckpointManager, Project, ProjectStatus, detect_hardware, get_device
from viddoblaje.utils import get_logger, configure_logging
from viddoblaje.stages import analysis, audio_extraction, asr, diarization, translation, tts as tts_stage, sync, subtitles, mix, export, voice_cloning, audio_separation

log = get_logger(__name__)


class PipelineOptions:
    def __init__(self, asr_model="whisper-base", translation_model=None, tts_voice="piper-es_ES-davefx-medium",
                 use_voice_cloning=False, use_audio_separation=False, burn_subtitles=False,
                 subtitles_format="srt", output_format="mp4", force_rerun_stages=None, source_language=None):
        self.asr_model = asr_model
        self.translation_model = translation_model
        self.tts_voice = tts_voice
        self.use_voice_cloning = use_voice_cloning
        self.use_audio_separation = use_audio_separation
        self.burn_subtitles = burn_subtitles
        self.subtitles_format = subtitles_format
        self.output_format = output_format
        self.force_rerun_stages = force_rerun_stages or []
        self.source_language = source_language

    def to_dict(self):
        return {"asr_model": self.asr_model, "translation_model": self.translation_model,
                "tts_voice": self.tts_voice, "use_voice_cloning": self.use_voice_cloning,
                "use_audio_separation": self.use_audio_separation, "burn_subtitles": self.burn_subtitles,
                "subtitles_format": self.subtitles_format, "output_format": self.output_format,
                "source_language": self.source_language}


ProgressCallback = Callable[[str, float, str], None]


def _ensure_models_available(options, hw_info):
    from viddoblaje.core.model_manager import ModelManager, KNOWN_MODELS, ModelStatus
    settings = get_settings()
    mgr = ModelManager(settings.models_dir, hf_token=settings.hf_token)
    required = mgr.list_required_for_pipeline(asr_id=options.asr_model, translation_id=options.translation_model or "opus-mt-en-es",
                                              tts_id=options.tts_voice, with_diarization=True,
                                              with_voice_cloning=options.use_voice_cloning, with_separation=options.use_audio_separation)
    missing = [m for m in required if mgr.get_status(m) != ModelStatus.INSTALLED and not KNOWN_MODELS[m].requires_license_acceptance]
    if missing:
        log.info("Auto-descargando modelos faltantes: {}", missing)
        for mid in missing:
            try:
                mgr.download(mid)
            except Exception as e:
                log.error("No se pudo descargar {}: {}", mid, e)


def run(project, options, progress_cb=None, cancel_event=None, pause_event=None):
    settings = get_settings()
    configure_logging(project.logs_dir)
    cp_mgr = CheckpointManager(project.checkpoints_dir)
    hw_info = detect_hardware()
    log.info("Iniciando pipeline para: {}", project.meta.name)
    try:
        _ensure_models_available(options, hw_info)
    except Exception as e:
        log.error("Auto-descarga falló: {}", e)
        project.set_error(f"models: {e}")
        raise

    def report(stage, progress, msg=""):
        if progress_cb:
            progress_cb(stage, progress, msg)
        project.meta.progress = progress
        log.info("[{:.0f}%] {} — {}", progress * 100, stage, msg)

    def is_cancelled():
        return cancel_event is not None and cancel_event.is_set()

    def wait_if_paused():
        if pause_event is not None:
            pause_event.wait()

    for stage in options.force_rerun_stages:
        cp_mgr.invalidate_from(stage)

    stages = [
        ("analysis", 0.01, ProjectStatus.ANALYZING, lambda: analysis.run(project)),
        ("audio_extraction", 0.05, ProjectStatus.EXTRACTING_AUDIO, lambda: audio_extraction.run(project)),
        ("transcription", 0.10, ProjectStatus.TRANSCRIBING, lambda: asr.run(project, model_id=options.asr_model, language=options.source_language)),
        ("diarization", 0.30, ProjectStatus.DIARIZING, lambda: diarization.run(project, hf_token=settings.hf_token)),
        ("translation", 0.45, ProjectStatus.TRANSLATING, lambda: translation.run(project, model_id=options.translation_model)),
        ("voice_generation", 0.60, ProjectStatus.GENERATING_VOICES, lambda: tts_stage.run(project, voice_model_id=options.tts_voice)),
        ("sync", 0.75, ProjectStatus.SYNCING, lambda: sync.run(project)),
        ("subtitles", 0.82, ProjectStatus.SUBTITLES, lambda: subtitles.run(project, formats=[options.subtitles_format])),
        ("mix", 0.88, ProjectStatus.MIXING, lambda: mix.run(project)),
        ("export", 0.95, ProjectStatus.EXPORTING, lambda: export.run(project, output_format=options.output_format, burn_subtitles=options.burn_subtitles)),
    ]

    for stage_name, progress, status, fn in stages:
        if is_cancelled():
            return project
        wait_if_paused()
        if not cp_mgr.exists(stage_name) or stage_name in options.force_rerun_stages:
            report(stage_name, progress, f"Ejecutando {stage_name}...")
            project.update_status(status, progress)
            t0 = time.time()
            try:
                result = fn()
                cp_mgr.save(stage_name, t0, inputs={}, outputs=result)
            except Exception as e:
                project.set_error(f"{stage_name}: {e}")
                raise
        else:
            log.info("Checkpoint '{}' existe, saltando", stage_name)

    project.update_status(ProjectStatus.COMPLETED, 1.0)
    report("done", 1.0, f"Vídeo final: {project.meta.output_video}")
    return project
