#!/usr/bin/env python3
"""Genera todos los archivos fuente de VidDoblaje."""
import os
from pathlib import Path

BASE = Path("/home/z/my-project/viddoblaje")

def write(rel_path, content):
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  {rel_path}")

# ============================================================
# src/viddoblaje/__init__.py
# ============================================================
write("src/viddoblaje/__init__.py", '''"""VidDoblaje — Traducción y doblaje automático de vídeos al español."""

__version__ = "1.0.0"
__author__ = "VidDoblaje"
__license__ = "MIT"

__all__ = ["__version__"]
''')

# ============================================================
# src/viddoblaje/__main__.py
# ============================================================
write("src/viddoblaje/__main__.py", '''"""Punto de entrada: python -m viddoblaje o VidDoblaje.exe"""
from __future__ import annotations

import sys


def _is_headless_mode() -> bool:
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        return True
    if sys.platform.startswith("linux"):
        import os
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            if os.environ.get("QT_QPA_PLATFORM") not in ("offscreen", "minimal"):
                return True
    return False


def main() -> int:
    if not _is_headless_mode():
        try:
            from viddoblaje.ui.app import run_gui
            return run_gui()
        except Exception as exc:
            print(f"[VidDoblaje] No se pudo iniciar la GUI: {exc}", file=sys.stderr)
            print("[VidDoblaje] Iniciando modo CLI...", file=sys.stderr)
    from viddoblaje.cli import run_cli
    return run_cli(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
''')

# ============================================================
# src/viddoblaje/config.py
# ============================================================
write("src/viddoblaje/config.py", '''"""Configuración central persistente."""
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
''')

# ============================================================
# src/viddoblaje/utils/__init__.py
# ============================================================
write("src/viddoblaje/utils/__init__.py", '''"""Utilidades de logging."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from loguru import logger as _logger

_configured = False


def configure_logging(logs_dir: Optional[Path] = None, level: str = "INFO") -> None:
    global _configured
    _logger.remove()
    _logger.add(
        sys.stderr, level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        colorize=True,
    )
    if logs_dir:
        logs_dir.mkdir(parents=True, exist_ok=True)
        _logger.add(
            logs_dir / "viddoblaje.log", level=level,
            rotation="10 MB", retention="7 days", encoding="utf-8",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        )
    _configured = True


def get_logger(name: str):
    if not _configured:
        configure_logging()
    return _logger.bind(module=name)
''')

# ============================================================
# src/viddoblaje/utils/logging.py
# ============================================================
write("src/viddoblaje/utils/logging.py", '''from . import get_logger, configure_logging
__all__ = ["get_logger", "configure_logging"]
''')

# ============================================================
# src/viddoblaje/utils/ffmpeg.py
# ============================================================
write("src/viddoblaje/utils/ffmpeg.py", '''"""Wrapper de FFmpeg con auto-descarga."""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Optional

from viddoblaje.utils import get_logger

log = get_logger(__name__)


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []
    if "FFMPEG_BINARY" in os.environ:
        paths.append(Path(os.environ["FFMPEG_BINARY"]))
    which = shutil.which("ffmpeg")
    if which:
        paths.append(Path(which))
    try:
        from viddoblaje.config import get_settings
        s = get_settings()
        paths.append(s.user_dir / "ffmpeg" / "ffmpeg")
        paths.append(s.user_dir / "ffmpeg" / "bin" / "ffmpeg")
        paths.append(s.user_dir / "ffmpeg" / "ffmpeg.exe")
        paths.append(s.user_dir / "ffmpeg" / "bin" / "ffmpeg.exe")
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
        paths.append(bundle_dir / "ffmpeg")
        paths.append(bundle_dir / "ffmpeg.exe")
        paths.append(bundle_dir / "bin" / "ffmpeg.exe")
    return paths


def _is_executable(p: Path) -> bool:
    if sys.platform == "win32":
        return p.suffix.lower() == ".exe" and p.is_file()
    return p.is_file() and (p.stat().st_mode & stat.S_IXUSR)


def _is_real_ffmpeg(p: Path) -> bool:
    if not _is_executable(p):
        return False
    try:
        clean_env = {"PATH": "/usr/bin:/usr/local/bin:/bin", "HOME": "/tmp"}
        result = subprocess.run([str(p), "-version"], capture_output=True, text=True, timeout=10, env=clean_env)
        output = (result.stdout + result.stderr).lower()
        return result.returncode == 0 and "ffmpeg version" in output
    except Exception:
        return False


def find_ffmpeg() -> Optional[Path]:
    for p in _candidate_paths():
        if p.exists() and _is_real_ffmpeg(p):
            log.debug("FFmpeg encontrado: {}", p)
            return p
    log.warning("FFmpeg no encontrado. Intentando descargar...")
    try:
        return download_ffmpeg()
    except Exception as e:
        log.error("No se pudo descargar FFmpeg: {}", e)
        return None


def download_ffmpeg() -> Optional[Path]:
    from viddoblaje.config import get_settings
    s = get_settings()
    target_dir = s.user_dir / "ffmpeg"
    target_dir.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        zip_path = target_dir / "ffmpeg.zip"
        log.info("Descargando FFmpeg desde {}", url)
        import urllib.request
        urllib.request.urlretrieve(url, zip_path)
        import zipfile
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target_dir)
        zip_path.unlink()
        for sub in target_dir.iterdir():
            if sub.is_dir() and sub.name.startswith("ffmpeg-"):
                bin_dir = sub / "bin"
                if bin_dir.exists():
                    for f in bin_dir.iterdir():
                        shutil.move(str(f), str(target_dir / f.name))
                    shutil.rmtree(sub, ignore_errors=True)
                    break
        exe = target_dir / "ffmpeg.exe"
        if exe.exists():
            log.info("FFmpeg instalado en {}", exe)
            return exe
    elif sys.platform == "linux":
        import tarfile
        url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-linux64-lgpl.tar.xz"
        archive = target_dir / "ffmpeg.tar.xz"
        import urllib.request
        urllib.request.urlretrieve(url, archive)
        with tarfile.open(archive, "r:xz") as tf:
            tf.extractall(target_dir)
        archive.unlink()
        for sub in target_dir.iterdir():
            if sub.is_dir() and sub.name.startswith("ffmpeg-"):
                bin_dir = sub / "bin"
                if bin_dir.exists():
                    for f in bin_dir.iterdir():
                        shutil.move(str(f), str(target_dir / f.name))
                    shutil.rmtree(sub, ignore_errors=True)
                    break
        exe = target_dir / "ffmpeg"
        if exe.exists():
            exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            return exe
    return None


_ffmpeg_path: Optional[Path] = None


def get_ffmpeg() -> Path:
    global _ffmpeg_path
    if _ffmpeg_path is None or not _ffmpeg_path.exists():
        _ffmpeg_path = find_ffmpeg()
        if _ffmpeg_path is None:
            raise RuntimeError("FFmpeg no está disponible.")
    return _ffmpeg_path


def get_ffprobe() -> Optional[Path]:
    ff = get_ffmpeg()
    ffprobe = ff.parent / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
    return ffprobe if ffprobe.exists() else None


def run_ffmpeg(args: list[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess:
    cmd = [str(get_ffmpeg())] + args
    log.debug("ffmpeg {}", " ".join(cmd))
    clean_env = {k: v for k, v in os.environ.items() if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD")}
    clean_env["PATH"] = "/usr/bin:/usr/local/bin:/bin:" + clean_env.get("PATH", "")
    return subprocess.run(cmd, check=check, capture_output=capture_output, text=True, env=clean_env)


def probe_video(path: Path) -> dict:
    ffprobe = get_ffprobe()
    if not ffprobe:
        return _probe_via_ffmpeg(path)
    import json
    cmd = [str(ffprobe), "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env={k: v for k, v in os.environ.items() if k not in ("LD_LIBRARY_PATH",)}).stdout
    return json.loads(out)


def _probe_via_ffmpeg(path: Path) -> dict:
    cmd = [str(get_ffmpeg()), "-i", str(path)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    info = proc.stderr
    duration = 0.0
    for line in info.splitlines():
        if "Duration" in line:
            try:
                d = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = d.split(":")
                duration = int(h) * 3600 + int(m) * 60 + float(s)
            except Exception:
                pass
    return {"format": {"duration": str(duration)}, "streams": []}


def get_video_duration(path: Path) -> float:
    try:
        info = probe_video(path)
        return float(info.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0
''')

print("Archivos core creados.")
