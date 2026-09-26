"""Cola de procesamiento con estados."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from viddoblaje.utils import get_logger
from viddoblaje.core.project import Project

log = get_logger(__name__)

try:
    from PySide6.QtCore import QObject, Signal
    _HAS_QT = True
except ImportError:
    _HAS_QT = False
    class _DummySignal:
        def __init__(self, *a, **k):
            self._callbacks = []
        def connect(self, cb):
            self._callbacks.append(cb)
        def emit(self, *args):
            for cb in self._callbacks:
                try: cb(*args)
                except Exception: pass
    class Signal(_DummySignal): pass
    class QObject: pass


class JobStatus(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    project_root: Path
    name: str
    status: JobStatus = JobStatus.WAITING
    progress: float = 0.0
    added_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    error: str = ""

    @property
    def project(self) -> Project:
        return Project.load(Path(self.project_root))


class QueueManager(QObject):
    job_added = Signal(int)
    job_status_changed = Signal(int, str)
    job_progress = Signal(int, float)
    job_error = Signal(int, str)
    queue_empty = Signal()

    def __init__(self, max_concurrent: int = 1):
        super().__init__()
        self.max_concurrent = max_concurrent
        self._jobs: list[Job] = []
        self._waiting: deque[int] = deque()
        self._current: Optional[int] = None
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._lock = threading.RLock()
        self._processor: Optional[Callable] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False

    def set_processor(self, fn: Callable) -> None:
        self._processor = fn

    def add(self, project_root: Path, name: str = "") -> int:
        with self._lock:
            job = Job(project_root=Path(project_root), name=name or project_root.name)
            self._jobs.append(job)
            idx = len(self._jobs) - 1
            self._waiting.append(idx)
            self.job_added.emit(idx)
            return idx

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._cancel_event.clear()
        self._pause_event.set()
        self._worker_thread = threading.Thread(target=self._run, name="queue-worker", daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        self._cancel_event.set()
        self._running = False

    def pause_current(self) -> None:
        self._pause_event.clear()
        if self._current is not None:
            self._jobs[self._current].status = JobStatus.PAUSED
            self.job_status_changed.emit(self._current, JobStatus.PAUSED.value)

    def resume_current(self) -> None:
        self._pause_event.set()

    def cancel_current(self) -> None:
        self._cancel_event.set()
        self._pause_event.set()

    @property
    def jobs(self) -> list:
        return list(self._jobs)

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def wait_if_paused(self) -> None:
        self._pause_event.wait()

    def report_progress(self, progress: float) -> None:
        if self._current is not None:
            self._jobs[self._current].progress = progress
            self.job_progress.emit(self._current, progress)

    def _run(self) -> None:
        while self._running and not self._cancel_event.is_set():
            with self._lock:
                if not self._waiting:
                    break
                self._current = self._waiting.popleft()
            job = self._jobs[self._current]
            if self._cancel_event.is_set():
                job.status = JobStatus.CANCELLED
                self.job_status_changed.emit(self._current, job.status.value)
                continue
            job.status = JobStatus.PROCESSING
            job.started_at = time.time()
            self.job_status_changed.emit(self._current, job.status.value)
            try:
                if self._processor:
                    self._processor(job, self)
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                self.job_error.emit(self._current, str(e))
            self.job_status_changed.emit(self._current, job.status.value)
            self._current = None
        if not self._waiting and not self._cancel_event.is_set():
            self.queue_empty.emit()
