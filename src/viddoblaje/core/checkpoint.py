"""Sistema de checkpoints y recuperación."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from viddoblaje.utils import get_logger

log = get_logger(__name__)

STAGE_ORDER = ["analysis", "audio_extraction", "transcription", "diarization", "translation", "voice_generation", "sync", "subtitles", "mix", "export"]


@dataclass
class Checkpoint:
    stage: str
    started_at: float
    completed_at: float
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    duration_sec: float = 0.0
    success: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Checkpoint":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CheckpointManager:
    def __init__(self, checkpoints_dir: Path):
        self.dir = Path(checkpoints_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, stage: str) -> Path:
        return self.dir / f"{stage}.json"

    def exists(self, stage: str) -> bool:
        p = self._path(stage)
        if not p.exists():
            return False
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("success", False)
        except Exception:
            return False

    def load(self, stage: str) -> Optional[Checkpoint]:
        p = self._path(stage)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return Checkpoint.from_dict(data)
        except Exception:
            return None

    def save(self, stage: str, started_at: float, inputs: dict, outputs: dict, success: bool = True, error: str = "") -> Checkpoint:
        now = time.time()
        cp = Checkpoint(stage=stage, started_at=started_at, completed_at=now, inputs=inputs, outputs=outputs, duration_sec=now - started_at, success=success, error=error)
        p = self._path(stage)
        tmp = p.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cp.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        tmp.replace(p)
        log.info("Checkpoint '{}' guardado ({:.1f}s)", stage, cp.duration_sec)
        return cp

    def invalidate(self, stage: str) -> None:
        p = self._path(stage)
        if p.exists():
            p.unlink()

    def invalidate_from(self, stage: str) -> None:
        try:
            idx = STAGE_ORDER.index(stage)
        except ValueError:
            return
        for s in STAGE_ORDER[idx:]:
            self.invalidate(s)

    def last_completed(self) -> Optional[str]:
        for stage in reversed(STAGE_ORDER):
            if self.exists(stage):
                return stage
        return None

    def next_stage(self) -> Optional[str]:
        for stage in STAGE_ORDER:
            if not self.exists(stage):
                return stage
        return None

    def all_completed(self) -> bool:
        return all(self.exists(s) for s in STAGE_ORDER)

    def list_all(self) -> list:
        result = []
        for stage in STAGE_ORDER:
            cp = self.load(stage)
            if cp:
                result.append(cp)
        return result
