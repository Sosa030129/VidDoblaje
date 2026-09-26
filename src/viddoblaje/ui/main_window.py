"""Ventana principal."""
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
            QMessageBox.critical(self, "Error", f"No se pudo crear proyecto:\n{e}")

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
            QMessageBox.critical(self, "Error", f"No se pudo abrir proyecto:\n{e}")

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
            QMessageBox.critical(self, "Error", f"No se pudo iniciar:\n{e}")
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
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{e}")

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
