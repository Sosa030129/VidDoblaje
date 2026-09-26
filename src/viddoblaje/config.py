"""Configuración central persistente."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

APP_NAME = "VidDoblaje"
APP_VERSION = "1.0.0"


def _default_user_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(base) / APP_NAME


def _default_projects_dir() -> Path:
    return Path.home() / "VidDoblajeProjects"


@dataclass
class Settings:
    user_dir: Path = field(default_factory=_default_user_dir)
    projects_dir: Path = field(default_factory=_default_projects_dir)
    models_dir: Path = field(default_factory=lambda: _default_user_dir() / "models")
    cache_dir: Path = field(default_factory=lambda: _default_user_dir() / "cache")
    logs_dir: Path = field(default_factory=lambda: _default_user_dir() / "logs")
    theme: Literal["dark", "light", "auto"] = "dark"
    language: str = "es"
    window_geometry: dict = field(default_factory=dict)
    default_asr_model: str = "whisper-base"
    default_translation_model: str = "opus-mt-en-es"
    default_tts_voice: str = "piper-es_ES-davefx-medium"
    enable_voice_cloning: bool = False
    enable_audio_separation: bool = False
    burn_subtitles: bool = False
    subtitles_format: Literal["srt", "vtt"] = "srt"
    hardware_profile: Literal["ultra_low", "low", "medium", "high", "maximum"] = "medium"
    force_cpu_only: bool = False
    gpu_device: str = "auto"
    output_format: Literal["mp4", "mkv"] = "mp4"
    output_video_codec: str = "libx264"
    output_audio_codec: str = "aac"
    output_bitrate: str = "auto"
    max_concurrent_jobs: int = 1
    chunk_duration_sec: int = 600
    enable_checkpoints: bool = True
    auto_resume_on_crash: bool = True
    hf_token: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("user_dir", "projects_dir", "models_dir", "cache_dir", "logs_dir"):
            d[k] = str(d[k])
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        path_keys = ("user_dir", "projects_dir", "models_dir", "cache_dir", "logs_dir")
        for k in path_keys:
            if k in d and isinstance(d[k], str):
                d[k] = Path(d[k])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def ensure_dirs(self) -> None:
        for d in (self.user_dir, self.projects_dir, self.models_dir, self.cache_dir, self.logs_dir):
            d.mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = _load_or_create()
    return _settings


def save_settings(s: Settings | None = None) -> None:
    s = s or get_settings()
    path = s.user_dir / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s.to_dict(), f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def _load_or_create() -> Settings:
    user_dir = _default_user_dir()
    path = user_dir / "settings.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = Settings.from_dict(data)
            settings.ensure_dirs()
            return settings
        except Exception:
            pass
    settings = Settings()
    settings.ensure_dirs()
    save_settings(settings)
    return settings


def reset_settings() -> Settings:
    global _settings
    _settings = Settings()
    _settings.ensure_dirs()
    return _settings
