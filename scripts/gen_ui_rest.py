#!/usr/bin/env python3
"""Genera UI restante, tests, scripts, docs."""
from pathlib import Path

BASE = Path("/home/z/my-project/viddoblaje")

def write(rel_path, content):
    p = BASE / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  {rel_path}")

# processor.py
write("src/viddoblaje/ui/processor.py", '''"""Controlador de procesamiento."""
from __future__ import annotations
import threading
from typing import Callable, Optional
from PySide6.QtCore import QObject, QThread, Signal
from viddoblaje.config import get_settings
from viddoblaje.core import Project
from viddoblaje.pipeline import PipelineOptions, run as run_pipeline
from viddoblaje.utils import get_logger

log = get_logger(__name__)


class _Worker(QObject):
    progress = Signal(object, str, float, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, projects, options):
        super().__init__()
        self.projects = projects
        self.options = options
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._pause.set()

    def run(self):
        try:
            for proj in self.projects:
                if self._cancel.is_set():
                    break
                run_pipeline(project=proj, options=self.options,
                             progress_cb=lambda stage, p, msg: self.progress.emit(proj, stage, p, msg),
                             cancel_event=self._cancel, pause_event=self._pause)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def cancel(self):
        self._cancel.set()

    def pause(self):
        self._pause.clear()

    def resume(self):
        self._pause.set()


class ProcessingController(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._worker = None

    def start(self, projects, options=None, on_done=None, on_progress=None, on_error=None):
        if self._thread and self._thread.isRunning():
            return
        settings = get_settings()
        if options is None:
            options = PipelineOptions(asr_model=settings.default_asr_model, tts_voice=settings.default_tts_voice,
                                      use_voice_cloning=settings.enable_voice_cloning,
                                      use_audio_separation=settings.enable_audio_separation,
                                      burn_subtitles=settings.burn_subtitles, subtitles_format=settings.subtitles_format,
                                      output_format=settings.output_format)
        self._worker = _Worker(projects, options)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._cleanup)
        if on_done:
            self._worker.finished.connect(on_done)
        if on_progress:
            self._worker.progress.connect(on_progress)
        if on_error:
            self._worker.error.connect(on_error)
        self._thread.start()

    def cancel(self):
        if self._worker:
            self._worker.cancel()

    def _cleanup(self):
        if self._thread:
            self._thread.wait()
        self._worker = None
        self._thread = None
''')

# first_run.py
write("src/viddoblaje/ui/first_run.py", '''"""First Run Wizard."""
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
''')

# model_manager_ui.py
write("src/viddoblaje/ui/model_manager_ui.py", '''"""Diálogo del Model Manager."""
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
                f"El modelo {info.name} requiere aceptar la licencia:\\n\\n{info.license}\\n\\nURL: {info.license_url}\\n\\n¿Aceptas la licencia?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ret != QMessageBox.StandardButton.Yes:
                return
        if info.requires_hf_token and not self.manager.hf_token:
            QMessageBox.warning(self, "Token de HuggingFace requerido",
                f"El modelo {info.name} requiere un token de HuggingFace.\\nConfigúralo en Ajustes.")
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
            QMessageBox.warning(self, "Error descargando", f"Modelo {model_id}:\\n{error}")

    def _on_all_done(self):
        self.global_progress.setVisible(False)
        self.btn_install.setEnabled(True)
        self.btn_install_required.setEnabled(True)
        self._refresh_table()
        QMessageBox.information(self, "Descarga completada", "Modelos instalados correctamente.")
''')

# settings.py
write("src/viddoblaje/ui/settings.py", '''"""Diálogo de Ajustes."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QGroupBox, QTabWidget, QWidget, QFileDialog, QMessageBox)
from viddoblaje.config import get_settings, save_settings
from viddoblaje.core.hardware import detect_hardware, HardwareProfile
from viddoblaje.core.model_manager import KNOWN_MODELS, ModelCategory
from viddoblaje.utils import get_logger

log = get_logger(__name__)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes — VidDoblaje")
        self.resize(640, 600)
        self.settings = get_settings()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["dark", "light", "auto"])
        self.cmb_theme.setCurrentText(self.settings.theme)
        general_layout.addRow("Tema:", self.cmb_theme)
        self.edt_projects = QLineEdit(str(self.settings.projects_dir))
        btn_projects = QPushButton("...")
        btn_projects.clicked.connect(lambda: self._pick_dir(self.edt_projects))
        general_layout.addRow("Directorio de proyectos:", self._hbox(self.edt_projects, btn_projects))
        self.edt_models = QLineEdit(str(self.settings.models_dir))
        btn_models = QPushButton("...")
        btn_models.clicked.connect(lambda: self._pick_dir(self.edt_models))
        general_layout.addRow("Directorio de modelos:", self._hbox(self.edt_models, btn_models))
        tabs.addTab(general_tab, "General")

        pipe_tab = QWidget()
        pipe_layout = QFormLayout(pipe_tab)
        self.cmb_asr = QComboBox()
        for m in [x for x in KNOWN_MODELS.values() if x.category == ModelCategory.ASR]:
            self.cmb_asr.addItem(f"{m.name} ({m.size_mb} MB)", m.id)
        idx = self.cmb_asr.findData(self.settings.default_asr_model)
        if idx >= 0:
            self.cmb_asr.setCurrentIndex(idx)
        pipe_layout.addRow("Modelo ASR:", self.cmb_asr)
        self.cmb_tts = QComboBox()
        for m in [x for x in KNOWN_MODELS.values() if x.category == ModelCategory.TTS]:
            self.cmb_tts.addItem(f"{m.name} ({m.size_mb} MB)", m.id)
        idx = self.cmb_tts.findData(self.settings.default_tts_voice)
        if idx >= 0:
            self.cmb_tts.setCurrentIndex(idx)
        pipe_layout.addRow("Modelo TTS:", self.cmb_tts)
        self.chk_cloning = QCheckBox("Habilitar clonación de voz (XTTS v2, CPML)")
        self.chk_cloning.setChecked(self.settings.enable_voice_cloning)
        pipe_layout.addRow(self.chk_cloning)
        self.chk_separation = QCheckBox("Habilitar separación de audio (Demucs)")
        self.chk_separation.setChecked(self.settings.enable_audio_separation)
        pipe_layout.addRow(self.chk_separation)
        self.chk_burn = QCheckBox("Quemar subtítulos en el vídeo")
        self.chk_burn.setChecked(self.settings.burn_subtitles)
        pipe_layout.addRow(self.chk_burn)
        self.cmb_subs = QComboBox()
        self.cmb_subs.addItems(["srt", "vtt"])
        self.cmb_subs.setCurrentText(self.settings.subtitles_format)
        pipe_layout.addRow("Formato subtítulos:", self.cmb_subs)
        self.cmb_output = QComboBox()
        self.cmb_output.addItems(["mp4", "mkv"])
        self.cmb_output.setCurrentText(self.settings.output_format)
        pipe_layout.addRow("Formato salida:", self.cmb_output)
        tabs.addTab(pipe_tab, "Pipeline")

        hw_tab = QWidget()
        hw_layout = QFormLayout(hw_tab)
        btn_detect = QPushButton("Detectar hardware ahora")
        btn_detect.clicked.connect(self._detect_hardware)
        hw_layout.addRow("", btn_detect)
        self.lbl_hw = QLabel("No detectado todavía")
        self.lbl_hw.setWordWrap(True)
        hw_layout.addRow("Detectado:", self.lbl_hw)
        self.cmb_profile = QComboBox()
        for p in HardwareProfile:
            self.cmb_profile.addItem(p.value, p.value)
        idx = self.cmb_profile.findData(self.settings.hardware_profile)
        if idx >= 0:
            self.cmb_profile.setCurrentIndex(idx)
        hw_layout.addRow("Perfil de hardware:", self.cmb_profile)
        self.chk_cpu = QCheckBox("Forzar CPU-only")
        self.chk_cpu.setChecked(self.settings.force_cpu_only)
        hw_layout.addRow(self.chk_cpu)
        tabs.addTab(hw_tab, "Hardware")

        adv_tab = QWidget()
        adv_layout = QFormLayout(adv_tab)
        self.edt_hf_token = QLineEdit(self.settings.hf_token)
        self.edt_hf_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.edt_hf_token.setPlaceholderText("hf_xxx (solo para pyannote)")
        adv_layout.addRow("Token HuggingFace:", self.edt_hf_token)
        self.spn_chunk = QSpinBox()
        self.spn_chunk.setRange(60, 3600)
        self.spn_chunk.setValue(self.settings.chunk_duration_sec)
        adv_layout.addRow("Duración de chunk:", self.spn_chunk)
        self.chk_checkpoints = QCheckBox("Habilitar checkpoints")
        self.chk_checkpoints.setChecked(self.settings.enable_checkpoints)
        adv_layout.addRow(self.chk_checkpoints)
        tabs.addTab(adv_tab, "Avanzado")

        btns = QHBoxLayout()
        btns.addStretch()
        self.btn_ok = QPushButton("Guardar")
        self.btn_ok.setObjectName("primaryButton")
        self.btn_ok.clicked.connect(self._save)
        btns.addWidget(self.btn_ok)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        layout.addLayout(btns)

    def _hbox(self, *widgets):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        for x in widgets:
            h.addWidget(x)
        return w

    def _pick_dir(self, edt):
        d = QFileDialog.getExistingDirectory(self, "Selecciona carpeta", edt.text())
        if d:
            edt.setText(d)

    def _detect_hardware(self):
        try:
            info = detect_hardware()
            txt = f"OS: {info.os_name} {info.os_version}\\nCPU: {info.cpu_name} ({info.cpu_cores_physical}c/{info.cpu_cores_logical}t)\\nRAM: {info.ram_total_mb} MB\\nGPUs: {len(info.gpus)}\\n"
            for g in info.gpus:
                txt += f"  • {g}\\n"
            txt += f"Perfil recomendado: {info.recommend_profile().value}"
            self.lbl_hw.setText(txt)
            profile = info.recommend_profile().value
            idx = self.cmb_profile.findData(profile)
            if idx >= 0:
                self.cmb_profile.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo detectar hardware:\\n{e}")

    def _save(self):
        s = self.settings
        s.theme = self.cmb_theme.currentText()
        s.projects_dir = Path(self.edt_projects.text())
        s.models_dir = Path(self.edt_models.text())
        s.default_asr_model = self.cmb_asr.currentData()
        s.default_tts_voice = self.cmb_tts.currentData()
        s.enable_voice_cloning = self.chk_cloning.isChecked()
        s.enable_audio_separation = self.chk_separation.isChecked()
        s.burn_subtitles = self.chk_burn.isChecked()
        s.subtitles_format = self.cmb_subs.currentText()
        s.output_format = self.cmb_output.currentText()
        s.hardware_profile = self.cmb_profile.currentData()
        s.force_cpu_only = self.chk_cpu.isChecked()
        s.hf_token = self.edt_hf_token.text().strip()
        s.chunk_duration_sec = self.spn_chunk.value()
        s.enable_checkpoints = self.chk_checkpoints.isChecked()
        s.ensure_dirs()
        save_settings(s)
        self.accept()
''')

# translation_editor.py
write("src/viddoblaje/ui/translation_editor.py", '''"""Editor de traducción."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFileDialog, QMessageBox, QLabel, QHeaderView, QComboBox)
from viddoblaje.core.project import Project
from viddoblaje.utils import get_logger

log = get_logger(__name__)


class TranslationEditor(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle(f"Editor de traducción — {project.meta.name}")
        self.resize(1000, 700)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        info = QLabel(f"<b>Proyecto:</b> {self.project.meta.name} &nbsp; <b>Idioma:</b> {self.project.meta.source_language} → es &nbsp; <b>Segmentos:</b> {len(self.project.meta.segments)}")
        layout.addWidget(info)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["#", "Tiempo", "Speaker", "Original", "Español"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        btns = QHBoxLayout()
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)
        btn_export = QPushButton("Exportar CSV...")
        btn_export.clicked.connect(self._export_csv)
        btns.addWidget(btn_export)
        btn_import = QPushButton("Importar CSV...")
        btn_import.clicked.connect(self._import_csv)
        btns.addWidget(btn_import)
        btns.addStretch()
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.accept)
        btns.addWidget(btn_close)
        layout.addLayout(btns)

    def _load_data(self):
        self.table.setRowCount(0)
        for seg in self.project.meta.segments:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(seg.index)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{seg.start_sec:.1f} - {seg.end_sec:.1f}"))
            sp_combo = QComboBox()
            for sp in self.project.meta.speakers:
                sp_combo.addItem(sp.id)
            sp_combo.setCurrentText(seg.speaker_id)
            self.table.setCellWidget(row, 2, sp_combo)
            orig = QTableWidgetItem(seg.text_original)
            orig.setFlags(orig.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, orig)
            self.table.setItem(row, 4, QTableWidgetItem(seg.text_spanish))

    def _save(self):
        for row in range(self.table.rowCount()):
            try:
                idx = int(self.table.item(row, 0).text())
                sp_combo = self.table.cellWidget(row, 2)
                speaker = sp_combo.currentText() if sp_combo else "SPEAKER_001"
                esp = self.table.item(row, 4).text()
                for seg in self.project.meta.segments:
                    if seg.index == idx:
                        seg.text_spanish = esp
                        seg.speaker_id = speaker
                        break
            except Exception:
                pass
        self.project.save()
        from viddoblaje.core.checkpoint import CheckpointManager
        cp = CheckpointManager(self.project.checkpoints_dir)
        cp.invalidate_from("translation")
        QMessageBox.information(self, "Guardado", "Traducciones guardadas.")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "translations.csv", "CSV (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["index", "start", "end", "speaker", "original", "spanish"])
            for seg in self.project.meta.segments:
                w.writerow([seg.index, f"{seg.start_sec:.2f}", f"{seg.end_sec:.2f}", seg.speaker_id, seg.text_original, seg.text_spanish])

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar CSV", "", "CSV (*.csv)")
        if not path:
            return
        import csv
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    idx = int(row["index"])
                    for seg in self.project.meta.segments:
                        if seg.index == idx:
                            seg.text_spanish = row["spanish"]
                            break
                except Exception:
                    pass
        self._load_data()
''')

print("UI restante creada.")
