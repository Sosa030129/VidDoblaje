"""Editor de traducción."""
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
