"""Utilidades de logging."""
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
