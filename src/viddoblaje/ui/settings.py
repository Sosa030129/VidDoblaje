"""Diálogo de Ajustes."""
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
            txt = f"OS: {info.os_name} {info.os_version}\nCPU: {info.cpu_name} ({info.cpu_cores_physical}c/{info.cpu_cores_logical}t)\nRAM: {info.ram_total_mb} MB\nGPUs: {len(info.gpus)}\n"
            for g in info.gpus:
                txt += f"  • {g}\n"
            txt += f"Perfil recomendado: {info.recommend_profile().value}"
            self.lbl_hw.setText(txt)
            profile = info.recommend_profile().value
            idx = self.cmb_profile.findData(profile)
            if idx >= 0:
                self.cmb_profile.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo detectar hardware:\n{e}")

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
