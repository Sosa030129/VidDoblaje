"""Sistema de temas."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication
from viddoblaje.config import get_settings
from viddoblaje.utils import get_logger

log = get_logger(__name__)
THEMES_DIR = Path(__file__).parent / "themes"


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._current = get_settings().theme

    def apply(self, app, theme=None):
        if theme is None:
            theme = self._current
        if theme == "auto":
            palette = app.palette()
            bg = palette.color(QPalette.ColorRole.Window)
            theme = "dark" if bg.lightness() < 128 else "light"
        qss_path = THEMES_DIR / f"{theme}.qss"
        if qss_path.exists():
            app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
            log.info("Tema aplicado: {}", theme)
        self._current = theme
        self.theme_changed.emit(theme)

    @property
    def current(self):
        return self._current


_theme_manager = None

def get_theme_manager():
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
