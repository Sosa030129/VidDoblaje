"""Controlador de procesamiento."""
from __future__ import annotations
import threading
from typing import Callable, Optional
from PySide6.QtCore import QObject, QThread, Signal
from viddoblaje.config import get_settings
from viddoblaje.core import Project
from viddoblaje.pipeline import PipelineOptions, run as run_pipeline
from viddoblaje.utils import get_logger

log = get_logger(__name__)


class _Worker(QObject):
    progress = Signal(object, str, float, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, projects, options):
        super().__init__()
        self.projects = projects
        self.options = options
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._pause.set()

    def run(self):
        try:
            for proj in self.projects:
                if self._cancel.is_set():
                    break
                run_pipeline(project=proj, options=self.options,
                             progress_cb=lambda stage, p, msg: self.progress.emit(proj, stage, p, msg),
                             cancel_event=self._cancel, pause_event=self._pause)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def cancel(self):
        self._cancel.set()

    def pause(self):
        self._pause.clear()

    def resume(self):
        self._pause.set()


class ProcessingController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None

    def start(self, projects, options=None, on_done=None, on_progress=None, on_error=None):
        if self._thread and self._thread.isRunning():
            return
        settings = get_settings()
        if options is None:
            options = PipelineOptions(asr_model=settings.default_asr_model, tts_voice=settings.default_tts_voice,
                                      use_voice_cloning=settings.enable_voice_cloning,
                                      use_audio_separation=settings.enable_audio_separation,
                                      burn_subtitles=settings.burn_subtitles, subtitles_format=settings.subtitles_format,
                                      output_format=settings.output_format)
        self._worker = _Worker(projects, options)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._cleanup)
        if on_done:
            self._worker.finished.connect(on_done)
        if on_progress:
            self._worker.progress.connect(on_progress)
        if on_error:
            self._worker.error.connect(on_error)
        self._thread.start()

    def cancel(self):
        if self._worker:
            self._worker.cancel()

    def _cleanup(self):
        if self._thread:
            self._thread.wait()
        self._worker = None
        self._thread = None
