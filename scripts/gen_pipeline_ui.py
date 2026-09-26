#!/usr/bin/env python3
"""Genera pipeline, cli, ui, tests, scripts, docs."""
from pathlib import Path

BASE = Path("/home/z/my-project/viddoblaje")

def write(rel_path, content):
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  {rel_path}")

# pipeline.py
write("src/viddoblaje/pipeline.py", '''"""Orquestador del pipeline VidDoblaje."""
from __future__ import annotations
import time
from pathlib import Path
from typing import Callable, Optional

from viddoblaje.config import get_settings
from viddoblaje.core import CheckpointManager, Project, ProjectStatus, detect_hardware, get_device
from viddoblaje.utils import get_logger, configure_logging
from viddoblaje.stages import analysis, audio_extraction, asr, diarization, translation, tts as tts_stage, sync, subtitles, mix, export, voice_cloning, audio_separation

log = get_logger(__name__)


class PipelineOptions:
    def __init__(self, asr_model="whisper-base", translation_model=None, tts_voice="piper-es_ES-davefx-medium",
                 use_voice_cloning=False, use_audio_separation=False, burn_subtitles=False,
                 subtitles_format="srt", output_format="mp4", force_rerun_stages=None, source_language=None):
        self.asr_model = asr_model
        self.translation_model = translation_model
        self.tts_voice = tts_voice
        self.use_voice_cloning = use_voice_cloning
        self.use_audio_separation = use_audio_separation
        self.burn_subtitles = burn_subtitles
        self.subtitles_format = subtitles_format
        self.output_format = output_format
        self.force_rerun_stages = force_rerun_stages or []
        self.source_language = source_language

    def to_dict(self):
        return {"asr_model": self.asr_model, "translation_model": self.translation_model,
                "tts_voice": self.tts_voice, "use_voice_cloning": self.use_voice_cloning,
                "use_audio_separation": self.use_audio_separation, "burn_subtitles": self.burn_subtitles,
                "subtitles_format": self.subtitles_format, "output_format": self.output_format,
                "source_language": self.source_language}


ProgressCallback = Callable[[str, float, str], None]


def _ensure_models_available(options, hw_info):
    from viddoblaje.core.model_manager import ModelManager, KNOWN_MODELS, ModelStatus
    settings = get_settings()
    mgr = ModelManager(settings.models_dir, hf_token=settings.hf_token)
    required = mgr.list_required_for_pipeline(asr_id=options.asr_model, translation_id=options.translation_model or "opus-mt-en-es",
                                              tts_id=options.tts_voice, with_diarization=True,
                                              with_voice_cloning=options.use_voice_cloning, with_separation=options.use_audio_separation)
    missing = [m for m in required if mgr.get_status(m) != ModelStatus.INSTALLED and not KNOWN_MODELS[m].requires_license_acceptance]
    if missing:
        log.info("Auto-descargando modelos faltantes: {}", missing)
        for mid in missing:
            try:
                mgr.download(mid)
            except Exception as e:
                log.error("No se pudo descargar {}: {}", mid, e)


def run(project, options, progress_cb=None, cancel_event=None, pause_event=None):
    settings = get_settings()
    configure_logging(project.logs_dir)
    cp_mgr = CheckpointManager(project.checkpoints_dir)
    hw_info = detect_hardware()
    log.info("Iniciando pipeline para: {}", project.meta.name)
    try:
        _ensure_models_available(options, hw_info)
    except Exception as e:
        log.error("Auto-descarga falló: {}", e)
        project.set_error(f"models: {e}")
        raise

    def report(stage, progress, msg=""):
        if progress_cb:
            progress_cb(stage, progress, msg)
        project.meta.progress = progress
        log.info("[{:.0f}%] {} — {}", progress * 100, stage, msg)

    def is_cancelled():
        return cancel_event is not None and cancel_event.is_set()

    def wait_if_paused():
        if pause_event is not None:
            pause_event.wait()

    for stage in options.force_rerun_stages:
        cp_mgr.invalidate_from(stage)

    stages = [
        ("analysis", 0.01, ProjectStatus.ANALYZING, lambda: analysis.run(project)),
        ("audio_extraction", 0.05, ProjectStatus.EXTRACTING_AUDIO, lambda: audio_extraction.run(project)),
        ("transcription", 0.10, ProjectStatus.TRANSCRIBING, lambda: asr.run(project, model_id=options.asr_model, language=options.source_language)),
        ("diarization", 0.30, ProjectStatus.DIARIZING, lambda: diarization.run(project, hf_token=settings.hf_token)),
        ("translation", 0.45, ProjectStatus.TRANSLATING, lambda: translation.run(project, model_id=options.translation_model)),
        ("voice_generation", 0.60, ProjectStatus.GENERATING_VOICES, lambda: tts_stage.run(project, voice_model_id=options.tts_voice)),
        ("sync", 0.75, ProjectStatus.SYNCING, lambda: sync.run(project)),
        ("subtitles", 0.82, ProjectStatus.SUBTITLES, lambda: subtitles.run(project, formats=[options.subtitles_format])),
        ("mix", 0.88, ProjectStatus.MIXING, lambda: mix.run(project)),
        ("export", 0.95, ProjectStatus.EXPORTING, lambda: export.run(project, output_format=options.output_format, burn_subtitles=options.burn_subtitles)),
    ]

    for stage_name, progress, status, fn in stages:
        if is_cancelled():
            return project
        wait_if_paused()
        if not cp_mgr.exists(stage_name) or stage_name in options.force_rerun_stages:
            report(stage_name, progress, f"Ejecutando {stage_name}...")
            project.update_status(status, progress)
            t0 = time.time()
            try:
                result = fn()
                cp_mgr.save(stage_name, t0, inputs={}, outputs=result)
            except Exception as e:
                project.set_error(f"{stage_name}: {e}")
                raise
        else:
            log.info("Checkpoint '{}' existe, saltando", stage_name)

    project.update_status(ProjectStatus.COMPLETED, 1.0)
    report("done", 1.0, f"Vídeo final: {project.meta.output_video}")
    return project
''')

# cli.py
write("src/viddoblaje/cli.py", '''"""CLI mode."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from viddoblaje.config import get_settings
from viddoblaje.core import Project
from viddoblaje.pipeline import PipelineOptions, run as run_pipeline
from viddoblaje.utils import configure_logging, get_logger


def run_cli(args):
    parser = argparse.ArgumentParser(prog="viddoblaje", description="VidDoblaje CLI")
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("video", nargs="?")
    parser.add_argument("--project", "-p")
    parser.add_argument("--asr", default="whisper-base")
    parser.add_argument("--tts", default="piper-es_ES-davefx-medium")
    parser.add_argument("--format", default="mp4", choices=["mp4", "mkv"])
    parser.add_argument("--burn-subs", action="store_true")
    parser.add_argument("--cloning", action="store_true")
    parser.add_argument("--separation", action="store_true")
    parser.add_argument("--lang")
    parser.add_argument("--list-models", action="store_true")
    pargs = parser.parse_args(args)

    settings = get_settings()
    configure_logging(settings.logs_dir)
    log = get_logger("cli")

    if pargs.list_models:
        from viddoblaje.core.model_manager import KNOWN_MODELS, ModelCategory
        for cat in ModelCategory:
            print(f"\\n# {cat.value}")
            for m in [x for x in KNOWN_MODELS.values() if x.category == cat]:
                print(f"  {m.id}: {m.name} ({m.size_mb} MB) - {m.license}")
        return 0

    if not pargs.video and not pargs.project:
        parser.print_help()
        return 1

    if pargs.project:
        project = Project.load(Path(pargs.project))
    else:
        video_path = Path(pargs.video)
        if not video_path.exists():
            print(f"Vídeo no encontrado: {video_path}", file=sys.stderr)
            return 1
        project = Project.create(name=video_path.stem, source_video=video_path, base_dir=settings.projects_dir)

    options = PipelineOptions(asr_model=pargs.asr, tts_voice=pargs.tts, use_voice_cloning=pargs.cloning,
                              use_audio_separation=pargs.separation, burn_subtitles=pargs.burn_subs,
                              output_format=pargs.format, source_language=pargs.lang)

    def progress(stage, p, msg):
        print(f"[{p*100:5.1f}%] {stage}: {msg}", flush=True)

    try:
        project = run_pipeline(project, options, progress_cb=progress)
        print(f"\\nVídeo final: {project.meta.output_video}", flush=True)
        return 0
    except Exception as e:
        log.exception("Pipeline falló")
        print(f"\\nERROR: {e}", file=sys.stderr)
        return 2
''')

# UI files
write("src/viddoblaje/ui/__init__.py", '"""GUI de VidDoblaje."""\\n')

write("src/viddoblaje/ui/themes.py", '''"""Sistema de temas."""
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
''')

write("src/viddoblaje/ui/app.py", '''"""Entry point GUI."""
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
''')

write("src/viddoblaje/ui/main_window.py", '''"""Ventana principal."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QFrame, QTableWidget, QTableWidgetItem,
    QProgressBar, QStatusBar, QToolBar, QMessageBox, QHeaderView, QStyle)

from viddoblaje.config import get_settings, save_settings
from viddoblaje.core import Project, ProjectStatus
from viddoblaje.utils import get_logger
from viddoblaje.ui.themes import get_theme_manager

log = get_logger(__name__)
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".mpg", ".mpeg"}


class DropZone(QFrame):
    video_dropped = Signal(str)
    add_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Arrastra y suelta un vídeo aquí")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        hint = QLabel("o")
        hint.setObjectName("subtitleLabel")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        btn = QPushButton("+ AGREGAR VIDEO")
        btn.setObjectName("primaryButton")
        btn.clicked.connect(self.add_clicked.emit)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        exts = QLabel("Formatos: MP4, MKV, AVI, MOV, WEBM")
        exts.setObjectName("hintLabel")
        exts.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(exts)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                if Path(u.toLocalFile()).suffix.lower() in VIDEO_EXTS:
                    e.acceptProposedAction()
                    self.setProperty("dragActive", True)
                    self.style().unpolish(self)
                    self.style().polish(self)

    def dragLeaveEvent(self, e):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, e):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in VIDEO_EXTS:
                self.video_dropped.emit(path)


class ProjectsTable(QTableWidget):
    def __init__(self):
        super().__init__(0, 5)
        self.setHorizontalHeaderLabels(["Proyecto", "Estado", "Progreso", "Duración", "Salida"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(2, 200)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def add_project(self, project):
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QTableWidgetItem(project.meta.name))
        self.setItem(row, 1, QTableWidgetItem(project.meta.status))
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(project.meta.progress * 100))
        self.setCellWidget(row, 2, progress)
        dur = project.meta.duration_sec
        m, s = divmod(int(dur), 60)
        h, m = divmod(m, 60)
        self.setItem(row, 3, QTableWidgetItem(f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"))
        self.setItem(row, 4, QTableWidgetItem(project.meta.output_video or "—"))
        return row

    def update_row(self, row, project):
        if row >= self.rowCount():
            return
        self.item(row, 0).setText(project.meta.name)
        self.item(row, 1).setText(project.meta.status)
        progress = self.cellWidget(row, 2)
        if isinstance(progress, QProgressBar):
            v = int(project.meta.progress * 100)
            progress.setValue(v)
        self.item(row, 4).setText(project.meta.output_video or "—")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VidDoblaje — Traducción y doblaje al español")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)
        self._projects = []
        self._build_ui()
        self._build_toolbar()
        self._build_statusbar()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("VidDoblaje")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        self.btn_dub = QPushButton("TRADUCIR Y DOBLAR AL ESPAÑOL")
        self.btn_dub.setObjectName("primaryButton")
        self.btn_dub.setEnabled(False)
        self.btn_dub.clicked.connect(self._on_dub_clicked)
        header.addWidget(self.btn_dub)
        layout.addLayout(header)
        self.drop_zone = DropZone()
        self.drop_zone.video_dropped.connect(self._on_video_dropped)
        self.drop_zone.add_clicked.connect(self._on_add_video_clicked)
        layout.addWidget(self.drop_zone)
        label = QLabel("Proyectos en cola:")
        label.setObjectName("subtitleLabel")
        layout.addWidget(label)
        self.projects_table = ProjectsTable()
        layout.addWidget(self.projects_table, stretch=1)
        actions = QHBoxLayout()
        self.btn_open_project = QPushButton("Abrir proyecto existente...")
        self.btn_open_project.clicked.connect(self._on_open_project)
        actions.addWidget(self.btn_open_project)
        actions.addStretch()
        self.btn_remove = QPushButton("Quitar seleccionado")
        self.btn_remove.clicked.connect(self._on_remove_selected)
        actions.addWidget(self.btn_remove)
        layout.addLayout(actions)

    def _build_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.act_models = QAction("Model Manager", self)
        self.act_models.triggered.connect(self._open_model_manager)
        toolbar.addAction(self.act_models)
        self.act_settings = QAction("Ajustes", self)
        self.act_settings.triggered.connect(self._open_settings)
        toolbar.addAction(self.act_settings)
        self.act_editor = QAction("Editor de traducción", self)
        self.act_editor.triggered.connect(self._open_translation_editor)
        toolbar.addAction(self.act_editor)
        toolbar.addSeparator()
        from PySide6.QtWidgets import QComboBox
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light", "auto"])
        self.theme_combo.setCurrentText(get_settings().theme)
        self.theme_combo.currentTextChanged.connect(self._change_theme)
        self.theme_combo.setFixedWidth(100)
        toolbar.addWidget(QLabel("Tema:"))
        toolbar.addWidget(self.theme_combo)
        toolbar.addSeparator()
        self.act_about = QAction("Acerca de", self)
        self.act_about.triggered.connect(self._show_about)
        toolbar.addAction(self.act_about)

    def _build_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Listo")
        self.global_progress = QProgressBar()
        self.global_progress.setFixedWidth(200)
        self.global_progress.setRange(0, 100)
        self.global_progress.setValue(0)
        self.global_progress.setFormat("Cola: %p%")
        self.status.addPermanentWidget(self.global_progress)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_wizard_shown", False):
            self._wizard_shown = True
            QTimer.singleShot(100, self._maybe_run_wizard)

    def _maybe_run_wizard(self):
        try:
            from viddoblaje.ui.first_run import run_wizard_if_needed
            run_wizard_if_needed(parent=self)
        except Exception as e:
            log.warning("No se pudo ejecutar wizard: {}", e)

    def _on_add_video_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Agregar vídeos", str(get_settings().projects_dir),
            "Vídeos (*.mp4 *.mkv *.avi *.mov *.webm *.m4v *.mpg *.mpeg);;Todos (*)")
        for f in files:
            self._add_video(Path(f))

    def _on_video_dropped(self, path):
        self._add_video(Path(path))

    def _add_video(self, path):
        if not path.exists():
            QMessageBox.warning(self, "Vídeo no encontrado", str(path))
            return
        try:
            project = Project.create(name=path.stem, source_video=path, base_dir=get_settings().projects_dir)
            row = self.projects_table.add_project(project)
            self._projects.append((project, row))
            self.btn_dub.setEnabled(True)
            self.status.showMessage(f"Proyecto creado: {project.meta.name}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear proyecto:\\n{e}")

    def _on_open_project(self):
        proj_root = QFileDialog.getExistingDirectory(self, "Abrir proyecto VidDoblaje", str(get_settings().projects_dir))
        if not proj_root:
            return
        try:
            project = Project.load(Path(proj_root))
            row = self.projects_table.add_project(project)
            self._projects.append((project, row))
            self.btn_dub.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir proyecto:\\n{e}")

    def _on_remove_selected(self):
        rows = sorted({idx.row() for idx in self.projects_table.selectedIndexes()}, reverse=True)
        for r in rows:
            if 0 <= r < len(self._projects):
                del self._projects[r]
            self.projects_table.removeRow(r)
        if not self._projects:
            self.btn_dub.setEnabled(False)

    def _on_dub_clicked(self):
        if not self._projects:
            return
        self.btn_dub.setEnabled(False)
        self.btn_dub.setText("Procesando...")
        try:
            from viddoblaje.ui.processor import ProcessingController
            if not hasattr(self, "_controller"):
                self._controller = ProcessingController(self)
            self._controller.start([p for p, _ in self._projects], on_done=self._on_processing_done, on_progress=self._on_progress)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo iniciar:\\n{e}")
            self.btn_dub.setEnabled(True)
            self.btn_dub.setText("TRADUCIR Y DOBLAR AL ESPAÑOL")

    def _on_processing_done(self):
        self.btn_dub.setEnabled(True)
        self.btn_dub.setText("TRADUCIR Y DOBLAR AL ESPAÑOL")
        self.status.showMessage("Procesamiento completado", 5000)
        for project, row in self._projects:
            self.projects_table.update_row(row, project)

    def _on_progress(self, project, stage, progress, msg):
        for p, row in self._projects:
            if p.meta.id == project.meta.id:
                project.meta.status = stage
                project.meta.progress = progress
                self.projects_table.update_row(row, project)
                break
        self.status.showMessage(f"[{int(progress*100)}%] {stage} — {msg}")
        self.global_progress.setValue(int(progress * 100))

    def _change_theme(self, theme):
        s = get_settings()
        s.theme = theme
        save_settings(s)
        get_theme_manager().apply(QApplication.instance(), theme)

    def _open_model_manager(self):
        from viddoblaje.ui.model_manager_ui import ModelManagerDialog
        dlg = ModelManagerDialog(self)
        dlg.exec()

    def _open_settings(self):
        from viddoblaje.ui.settings import SettingsDialog
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.status.showMessage("Ajustes guardados", 3000)

    def _open_translation_editor(self):
        proj_root = QFileDialog.getExistingDirectory(self, "Selecciona un proyecto para editar", str(get_settings().projects_dir))
        if not proj_root:
            return
        try:
            project = Project.load(Path(proj_root))
            from viddoblaje.ui.translation_editor import TranslationEditor
            editor = TranslationEditor(project, self)
            editor.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\\n{e}")

    def _show_about(self):
        from viddoblaje import __version__
        QMessageBox.about(self, "Acerca de VidDoblaje",
            f"<h3>VidDoblaje v{__version__}</h3>"
            "<p>Traducción y doblaje automático de vídeos al español.</p>"
            "<p>100% local. Sin APIs en la nube.</p>"
            "<p>Powered by Whisper, MarianMT, Piper TTS, SpeechBrain.</p>")

    def closeEvent(self, e):
        s = get_settings()
        s.window_geometry = {"x": self.x(), "y": self.y(), "w": self.width(), "h": self.height()}
        save_settings(s)
        super().closeEvent(e)
''')

print("Pipeline, CLI y UI principales creados.")
