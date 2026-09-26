"""First Run Wizard."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QMessageBox, QFrame)
from viddoblaje.config import get_settings
from viddoblaje.core.model_manager import ModelManager, KNOWN_MODELS, ModelStatus
from viddoblaje.utils import get_logger

log = get_logger(__name__)

BASE_REQUIRED_MODELS = ["whisper-base", "opus-mt-en-es", "piper-es_ES-davefx-medium", "speechbrain-ecapa"]


class _BootstrapWorker(QThread):
    progress = Signal(str, int, int)
    status_update = Signal(str, str)
    finished_all = Signal(bool, str)

    def __init__(self, manager, model_ids):
        super().__init__()
        self.manager = manager
        self.model_ids = model_ids
        self._cancel = False

    def run(self):
        errors = []
        for mid in self.model_ids:
            if self._cancel:
                break
            self.status_update.emit(mid, "downloading")
            try:
                self.manager.download(mid, progress_cb=lambda d, t: self.progress.emit(mid, d // (1024*1024), t // (1024*1024)))
                self.status_update.emit(mid, "installed")
            except Exception as e:
                self.status_update.emit(mid, "error")
                errors.append(f"{mid}: {e}")
        self.finished_all.emit(not errors, "; ".join(errors))

    def cancel(self):
        self._cancel = True


class FirstRunWizard(QDialog):
    def __init__(self, parent=None, model_ids=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración inicial — VidDoblaje")
        self.setModal(True)
        self.resize(600, 480)
        s = get_settings()
        self.manager = ModelManager(s.models_dir, hf_token=s.hf_token)
        self.model_ids = model_ids or BASE_REQUIRED_MODELS
        self._worker = None
        self._build_ui()
        self._check_status()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Configuración inicial")
        title.setStyleSheet("font-size: 18pt; font-weight: bold;")
        layout.addWidget(title)
        intro = QLabel("VidDoblaje necesita descargar los modelos de IA base (~588 MB). El proceso es completamente automático.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.model_rows = {}
        for mid in self.model_ids:
            info = KNOWN_MODELS[mid]
            frame = QFrame()
            row = QVBoxLayout(frame)
            row.setContentsMargins(8, 8, 8, 8)
            header = QHBoxLayout()
            name_label = QLabel(f"<b>{info.name}</b>")
            name_label.setMinimumWidth(280)
            header.addWidget(name_label)
            header.addStretch()
            size_label = QLabel(f"{info.size_mb} MB")
            size_label.setStyleSheet("color: #888;")
            header.addWidget(size_label)
            row.addLayout(header)
            desc = QLabel(info.description)
            desc.setStyleSheet("color: #666; font-size: 9pt;")
            desc.setWordWrap(True)
            row.addWidget(desc)
            status_row = QHBoxLayout()
            self.model_rows[mid] = {"status_label": QLabel("Pendiente"), "progress": QProgressBar()}
            self.model_rows[mid]["status_label"].setStyleSheet("color: #888;")
            self.model_rows[mid]["progress"].setRange(0, 100)
            self.model_rows[mid]["progress"].setValue(0)
            self.model_rows[mid]["progress"].setFixedHeight(12)
            status_row.addWidget(self.model_rows[mid]["status_label"])
            status_row.addWidget(self.model_rows[mid]["progress"], stretch=1)
            row.addLayout(status_row)
            layout.addWidget(frame)
        layout.addStretch()
        btns = QHBoxLayout()
        self.btn_start = QPushButton("Descargar e instalar")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.clicked.connect(self._start_download)
        btns.addWidget(self.btn_start)
        self.btn_skip = QPushButton("Saltar (avanzado)")
        self.btn_skip.clicked.connect(self.reject)
        btns.addWidget(self.btn_skip)
        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.reject)
        self.btn_close.setVisible(False)
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)
        self.global_status = QLabel("")
        self.global_status.setWordWrap(True)
        layout.addWidget(self.global_status)

    def _check_status(self):
        for mid in self.model_ids:
            status = self.manager.get_status(mid)
            label = self.model_rows[mid]["status_label"]
            progress = self.model_rows[mid]["progress"]
            if status == ModelStatus.INSTALLED:
                label.setText("Instalado ✓")
                label.setStyleSheet("color: #3a9; font-weight: bold;")
                progress.setValue(100)
            else:
                label.setText("Pendiente de descarga")

    def _start_download(self):
        missing = [mid for mid in self.model_ids if self.manager.get_status(mid) != ModelStatus.INSTALLED]
        if not missing:
            self.global_status.setText("Todos los modelos ya están instalados.")
            self.btn_close.setVisible(True)
            self.btn_start.setVisible(False)
            self.btn_skip.setVisible(False)
            return
        self.btn_start.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.global_status.setText(f"Descargando {len(missing)} modelo(s)...")
        self._worker = _BootstrapWorker(self.manager, missing)
        self._worker.progress.connect(self._on_progress)
        self._worker.status_update.connect(self._on_status)
        self._worker.finished_all.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, model_id, downloaded_mb, total_mb):
        if model_id in self.model_rows:
            progress = self.model_rows[model_id]["progress"]
            if total_mb > 0:
                progress.setRange(0, total_mb)
                progress.setValue(downloaded_mb)
                self.model_rows[model_id]["status_label"].setText(f"Descargando {downloaded_mb}/{total_mb} MB")
            else:
                progress.setRange(0, 0)

    def _on_status(self, model_id, status):
        if model_id not in self.model_rows:
            return
        label = self.model_rows[model_id]["status_label"]
        progress = self.model_rows[model_id]["progress"]
        if status == "downloading":
            label.setText("Iniciando descarga...")
            label.setStyleSheet("color: #4a7fff;")
        elif status == "installed":
            label.setText("Instalado ✓")
            label.setStyleSheet("color: #3a9; font-weight: bold;")
            progress.setRange(0, 100)
            progress.setValue(100)
        elif status == "error":
            label.setText("Error")
            label.setStyleSheet("color: #e55; font-weight: bold;")

    def _on_finished(self, success, error_msg):
        if success:
            self.global_status.setText("<b>Configuración completada.</b>")
            self.global_status.setStyleSheet("color: #3a9;")
            self.btn_close.setVisible(True)
            self.btn_close.setText("Finalizar")
            self.btn_start.setVisible(False)
            self.btn_skip.setVisible(False)
            QTimer.singleShot(2000, self.accept)
        else:
            self.global_status.setText(f"Error: {error_msg}")
            self.global_status.setStyleSheet("color: #e55;")
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Reintentar")
            self.btn_skip.setEnabled(True)


def should_run_wizard():
    s = get_settings()
    mgr = ModelManager(s.models_dir, hf_token=s.hf_token)
    for mid in BASE_REQUIRED_MODELS:
        if mgr.get_status(mid) != ModelStatus.INSTALLED:
            return True
    return False


def run_wizard_if_needed(parent=None):
    if not should_run_wizard():
        return True
    wizard = FirstRunWizard(parent)
    wizard.exec()
    return not should_run_wizard()
