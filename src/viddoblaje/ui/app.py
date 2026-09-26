"""Entry point GUI."""
from __future__ import annotations
import os
import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication
from viddoblaje.config import get_settings
from viddoblaje.utils import configure_logging, get_logger
from viddoblaje.ui.themes import get_theme_manager
from viddoblaje.ui.main_window import MainWindow


def run_gui():
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("VidDoblaje")
    app.setOrganizationName("VidDoblaje")
    settings = get_settings()
    configure_logging(settings.logs_dir)
    log = get_logger(__name__)
    log.info("VidDoblaje arrancando (v{})", "1.0.0")
    theme_mgr = get_theme_manager()
    theme_mgr.apply(app, settings.theme)
    window = MainWindow()
    geo = settings.window_geometry
    if geo:
        window.setGeometry(geo.get("x", 100), geo.get("y", 100), geo.get("w", 1100), geo.get("h", 720))
    window.show()
    if os.environ.get("QT_QPA_PLATFORM") in ("offscreen", "minimal"):
        log.info("Modo headless detectado: auto-quit en 1s")
        QTimer.singleShot(1000, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_gui())
