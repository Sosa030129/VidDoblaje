"""Gestión de proyectos VidDoblaje."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from viddoblaje.utils import get_logger

log = get_logger(__name__)


class ProjectStatus(str, Enum):
    CREATED = "created"
    ANALYZING = "analyzing"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    TRANSLATING = "translating"
    GENERATING_VOICES = "generating_voices"
    SYNCING = "syncing"
    MIXING = "mixing"
    SUBTITLES = "subtitles"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class Speaker:
    id: str
    label: str = ""
    voice_profile: str = ""
    segments: int = 0
    total_duration_sec: float = 0.0
    voice_sample_path: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Speaker":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Segment:
    index: int
    start_sec: float
    end_sec: float
    speaker_id: str
    text_original: str
    text_spanish: str = ""
    voice_path: Optional[str] = None
    status: str = "pending"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Segment":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ProjectMeta:
    id: str
    name: str
    created_at: float
    updated_at: float
    source_video: str
    source_language: str = "auto"
    target_language: str = "es"
    duration_sec: float = 0.0
    status: str = ProjectStatus.CREATED.value
    last_checkpoint: str = ""
    speakers: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    output_video: str = ""
    error: str = ""
    progress: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectMeta":
        speakers = [Speaker.from_dict(s) for s in d.pop("speakers", [])]
        segments = [Segment.from_dict(s) for s in d.pop("segments", [])]
        return cls(speakers=speakers, segments=segments, **{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


PROJECT_SUBDIRS = ["source", "audio", "transcription", "speakers", "voices", "translations", "subtitles", "previews", "renders", "checkpoints", "logs", "cache"]


class Project:
    SCHEMA_VERSION = 1

    def __init__(self, root: Path, meta: ProjectMeta):
        self.root = Path(root)
        self.meta = meta

    @classmethod
    def create(cls, name: str, source_video: Path, base_dir: Path) -> "Project":
        project_id = uuid.uuid4().hex[:12]
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60]
        root = base_dir / f"{safe_name}_{project_id}"
        root.mkdir(parents=True, exist_ok=True)
        for sub in PROJECT_SUBDIRS:
            (root / sub).mkdir(exist_ok=True)
        import shutil
        source_dir = root / "source"
        dest_video = source_dir / Path(source_video).name
        if Path(source_video).resolve() != dest_video.resolve():
            shutil.copy2(source_video, dest_video)
        now = time.time()
        meta = ProjectMeta(id=project_id, name=name, created_at=now, updated_at=now, source_video=str(dest_video))
        proj = cls(root=root, meta=meta)
        proj.save()
        return proj

    @classmethod
    def load(cls, root: Path) -> "Project":
        root = Path(root)
        meta_path = root / "project.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"No existe {meta_path}")
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = ProjectMeta.from_dict(data["project"])
        return cls(root=root, meta=meta)

    def save(self) -> None:
        self.meta.updated_at = time.time()
        meta_path = self.root / "project.json"
        tmp = meta_path.with_suffix(".json.tmp")
        payload = {"schema_version": self.SCHEMA_VERSION, "app_version": "1.0.0", "project": self.meta.to_dict()}
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
        tmp.replace(meta_path)

    @property
    def source_dir(self): return self.root / "source"
    @property
    def audio_dir(self): return self.root / "audio"
    @property
    def transcription_dir(self): return self.root / "transcription"
    @property
    def speakers_dir(self): return self.root / "speakers"
    @property
    def voices_dir(self): return self.root / "voices"
    @property
    def translations_dir(self): return self.root / "translations"
    @property
    def subtitles_dir(self): return self.root / "subtitles"
    @property
    def previews_dir(self): return self.root / "previews"
    @property
    def renders_dir(self): return self.root / "renders"
    @property
    def checkpoints_dir(self): return self.root / "checkpoints"
    @property
    def logs_dir(self): return self.root / "logs"
    @property
    def cache_dir(self): return self.root / "cache"

    def speaker_dir(self, speaker_id: str) -> Path:
        d = self.speakers_dir / speaker_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def voice_dir(self, speaker_id: str) -> Path:
        d = self.voices_dir / speaker_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def update_status(self, status: ProjectStatus, progress: float = -1.0) -> None:
        self.meta.status = status.value
        if progress >= 0:
            self.meta.progress = max(0.0, min(1.0, progress))
        self.save()

    def add_speaker(self, speaker_id: str) -> Speaker:
        for s in self.meta.speakers:
            if s.id == speaker_id:
                return s
        sp = Speaker(id=speaker_id)
        self.meta.speakers.append(sp)
        self.speaker_dir(speaker_id)
        return sp

    def set_error(self, err: str) -> None:
        self.meta.error = err
        self.meta.status = ProjectStatus.FAILED.value
        self.save()
        log.error("Proyecto {}: {}", self.meta.name, err)
