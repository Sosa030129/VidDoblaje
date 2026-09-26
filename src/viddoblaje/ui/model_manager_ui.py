"""Diálogo del Model Manager."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QProgressBar, QTabWidget, QWidget,
    QGroupBox)
from viddoblaje.config import get_settings
from viddoblaje.core.model_manager import ModelManager, KNOWN_MODELS, ModelStatus, ModelCategory
from viddoblaje.utils import get_logger

log = get_logger(__name__)


class _DownloadWorker(QThread):
    progress = Signal(str, int, int)
    finished_one = Signal(str, bool, str)
    all_done = Signal()

    def __init__(self, manager, model_ids):
        super().__init__()
        self.manager = manager
        self.model_ids = model_ids
        self._cancel = False

    def run(self):
        for mid in self.model_ids:
            if self._cancel:
                break
            try:
                self.manager.download(mid, progress_cb=lambda d, t: self.progress.emit(mid, d // (1024*1024), t // (1024*1024)))
                self.finished_one.emit(mid, True, "")
            except Exception as e:
                self.finished_one.emit(mid, False, str(e))
        self.all_done.emit()

    def cancel(self):
        self._cancel = True


class ModelManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Model Manager — VidDoblaje")
        self.resize(900, 600)
        s = get_settings()
        self.manager = ModelManager(s.models_dir, hf_token=s.hf_token)
        self._worker = None
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.tables = {}
        categories = {
            "ASR": ModelCategory.ASR, "Diarización": ModelCategory.DIARIZATION,
            "Traducción": ModelCategory.TRANSLATION, "TTS": ModelCategory.TTS,
            "Clonación de voz": ModelCategory.VOICE_CLONING,
            "Separación": ModelCategory.AUDIO_SEPARATION, "Embeddings": ModelCategory.EMBEDDING,
        }
        for name, cat in categories.items():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            table = self._make_table()
            tab_layout.addWidget(table)
            self.tabs.addTab(tab, name)
            self.tables[cat.value] = table
        info_box = QGroupBox("Estado")
        info_layout = QHBoxLayout(info_box)
        self.lbl_installed = QLabel("Instalados: 0 MB")
        self.lbl_required = QLabel("Requeridos: 0 MB")
        info_layout.addWidget(self.lbl_installed)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_required)
        layout.addWidget(info_box)
        btns = QHBoxLayout()
        self.btn_install = QPushButton("Instalar seleccionados")
        self.btn_install.clicked.connect(self._on_install)
        btns.addWidget(self.btn_install)
        self.btn_install_required = QPushButton("Instalar modelos base")
        self.btn_install_required.clicked.connect(self._on_install_required)
        btns.addWidget(self.btn_install_required)
        btns.addStretch()
        self.btn_remove = QPushButton("Eliminar seleccionados")
        self.btn_remove.clicked.connect(self._on_remove)
        btns.addWidget(self.btn_remove)
        self.btn_close = QPushButton("Cerrar")
        self.btn_close.clicked.connect(self.accept)
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)
        self.global_progress = QProgressBar()
        self.global_progress.setVisible(False)
        layout.addWidget(self.global_progress)

    def _make_table(self):
        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(["Modelo", "Tamaño", "Estado", "Licencia", "Idiomas", "VRAM min", "Acciones"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 7):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _refresh_table(self):
        for cat_val, table in self.tables.items():
            cat = ModelCategory(cat_val)
            table.setRowCount(0)
            for info in self.manager.list_models(category=cat):
                row = table.rowCount()
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(info.name))
                table.setItem(row, 1, QTableWidgetItem(f"{info.size_mb} MB"))
                status = self.manager.get_status(info.id).value
                table.setItem(row, 2, QTableWidgetItem(status))
                table.setItem(row, 3, QTableWidgetItem(info.license.split()[0] if info.license else ""))
                table.setItem(row, 4, QTableWidgetItem(", ".join(info.languages)))
                table.setItem(row, 5, QTableWidgetItem(f"{info.min_vram_mb} MB" if info.min_vram_mb else "—"))
                btn = QPushButton("Instalar" if status != ModelStatus.INSTALLED.value else "Reinstalar")
                btn.clicked.connect(lambda _, mid=info.id: self._install_one(mid))
                table.setCellWidget(row, 6, btn)
                table.item(row, 0).setData(Qt.ItemDataRole.UserRole, info.id)
        installed = self.manager.total_size_mb()
        required_models = self.manager.list_required_for_pipeline()
        required_mb = sum(KNOWN_MODELS[m].size_mb for m in required_models if m in KNOWN_MODELS)
        self.lbl_installed.setText(f"Instalados: {installed} MB")
        self.lbl_required.setText(f"Requeridos: {required_mb} MB")

    def _install_one(self, model_id):
        info = KNOWN_MODELS.get(model_id)
        if not info:
            return
        if info.requires_license_acceptance:
            ret = QMessageBox.warning(self, "Aceptación de licencia requerida",
                f"El modelo {info.name} requiere aceptar la licencia:\n\n{info.license}\n\nURL: {info.license_url}\n\n¿Aceptas la licencia?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return
        if info.requires_hf_token and not self.manager.hf_token:
            QMessageBox.warning(self, "Token de HuggingFace requerido",
                f"El modelo {info.name} requiere un token de HuggingFace.\nConfigúralo en Ajustes.")
            return
        self._run_download([model_id])

    def _on_install(self):
        table = self.tables[list(self.tables.keys())[self.tabs.currentIndex()]]
        selected = set()
        for item in table.selectedItems():
            row = item.row()
            mid = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if mid:
                selected.add(mid)
        if not selected:
            QMessageBox.information(self, "Nada seleccionado", "Selecciona modelos en la tabla.")
            return
        self._run_download(list(selected))

    def _on_install_required(self):
        required = self.manager.list_required_for_pipeline()
        not_installed = [m for m in required if not self.manager.is_installed(m)]
        if not not_installed:
            QMessageBox.information(self, "Todo instalado", "Los modelos base ya están instalados.")
            return
        self._run_download(not_installed)

    def _on_remove(self):
        for cat_val, table in self.tables.items():
            for item in table.selectedItems():
                row = item.row()
                mid = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if mid and self.manager.is_installed(mid):
                    ret = QMessageBox.question(self, "Confirmar eliminación", f"¿Eliminar {KNOWN_MODELS[mid].name}?")
                    if ret == QMessageBox.StandardButton.Yes:
                        self.manager.remove(mid)
        self._refresh_table()

    def _run_download(self, model_ids):
        self.global_progress.setVisible(True)
        self.global_progress.setRange(0, 0)
        self.btn_install.setEnabled(False)
        self.btn_install_required.setEnabled(False)
        self._worker = _DownloadWorker(self.manager, model_ids)
        self._worker.finished_one.connect(self._on_one_done)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _on_one_done(self, model_id, success, error):
        if not success:
            QMessageBox.warning(self, "Error descargando", f"Modelo {model_id}:\n{error}")

    def _on_all_done(self):
        self.global_progress.setVisible(False)
        self.btn_install.setEnabled(True)
        self.btn_install_required.setEnabled(True)
        self._refresh_table()
        QMessageBox.information(self, "Descarga completada", "Modelos instalados correctamente.")
