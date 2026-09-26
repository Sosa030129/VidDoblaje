"""Wrapper de FFmpeg con auto-descarga."""
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
