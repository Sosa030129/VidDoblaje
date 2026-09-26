"""CLI mode."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from viddoblaje.config import get_settings
from viddoblaje.core import Project
from viddoblaje.pipeline import PipelineOptions, run as run_pipeline
from viddoblaje.utils import configure_logging, get_logger


def run_cli(args):
    parser = argparse.ArgumentParser(prog="viddoblaje", description="VidDoblaje CLI")
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("video", nargs="?")
    parser.add_argument("--project", "-p")
    parser.add_argument("--asr", default="whisper-base")
    parser.add_argument("--tts", default="piper-es_ES-davefx-medium")
    parser.add_argument("--format", default="mp4", choices=["mp4", "mkv"])
    parser.add_argument("--burn-subs", action="store_true")
    parser.add_argument("--cloning", action="store_true")
    parser.add_argument("--separation", action="store_true")
    parser.add_argument("--lang")
    parser.add_argument("--list-models", action="store_true")
    pargs = parser.parse_args(args)

    settings = get_settings()
    configure_logging(settings.logs_dir)
    log = get_logger("cli")

    if pargs.list_models:
        from viddoblaje.core.model_manager import KNOWN_MODELS, ModelCategory
        for cat in ModelCategory:
            print(f"\n# {cat.value}")
            for m in [x for x in KNOWN_MODELS.values() if x.category == cat]:
                print(f"  {m.id}: {m.name} ({m.size_mb} MB) - {m.license}")
        return 0

    if not pargs.video and not pargs.project:
        parser.print_help()
        return 1

    if pargs.project:
        project = Project.load(Path(pargs.project))
    else:
        video_path = Path(pargs.video)
        if not video_path.exists():
            print(f"Vídeo no encontrado: {video_path}", file=sys.stderr)
            return 1
        project = Project.create(name=video_path.stem, source_video=video_path, base_dir=settings.projects_dir)

    options = PipelineOptions(asr_model=pargs.asr, tts_voice=pargs.tts, use_voice_cloning=pargs.cloning,
                              use_audio_separation=pargs.separation, burn_subtitles=pargs.burn_subs,
                              output_format=pargs.format, source_language=pargs.lang)

    def progress(stage, p, msg):
        print(f"[{p*100:5.1f}%] {stage}: {msg}", flush=True)

    try:
        project = run_pipeline(project, options, progress_cb=progress)
        print(f"\nVídeo final: {project.meta.output_video}", flush=True)
        return 0
    except Exception as e:
        log.exception("Pipeline falló")
        print(f"\nERROR: {e}", file=sys.stderr)
        return 2
