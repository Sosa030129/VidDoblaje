"""Model Manager — gestión automática de modelos de IA."""
from __future__ import annotations

import json
import shutil
import urllib.request
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from viddoblaje.utils import get_logger

log = get_logger(__name__)


class ModelStatus(str, Enum):
    NOT_INSTALLED = "not_installed"
    DOWNLOADING = "downloading"
    INSTALLED = "installed"
    CORRUPT = "corrupt"
    ERROR = "error"


class ModelCategory(str, Enum):
    ASR = "asr"
    DIARIZATION = "diarization"
    TRANSLATION = "translation"
    TTS = "tts"
    VOICE_CLONING = "voice_cloning"
    AUDIO_SEPARATION = "audio_separation"
    EMBEDDING = "embedding"


@dataclass
class ModelInfo:
    id: str
    name: str
    category: ModelCategory
    description: str = ""
    license: str = ""
    license_url: str = ""
    size_mb: int = 0
    version: str = "1.0"
    requires_hf_token: bool = False
    requires_license_acceptance: bool = False
    non_commercial_only: bool = False
    languages: list = field(default_factory=list)
    min_vram_mb: int = 0
    min_ram_mb: int = 0
    cpu_compatible: bool = True
    cuda_compatible: bool = True
    directml_compatible: bool = False
    hf_repo_id: str = ""
    hf_filename: str = ""
    is_directory: bool = False
    shared_with: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)

    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = ModelCategory(self.category)


KNOWN_MODELS: dict[str, ModelInfo] = {
    "whisper-tiny": ModelInfo(
        id="whisper-tiny", name="Whisper Tiny", category=ModelCategory.ASR,
        description="ASR rápido y ligero.", license="MIT", size_mb=75,
        min_ram_mb=512, hf_repo_id="Systran/faster-whisper-tiny", is_directory=True,
    ),
    "whisper-base": ModelInfo(
        id="whisper-base", name="Whisper Base", category=ModelCategory.ASR,
        description="ASR base recomendado por defecto.", license="MIT", size_mb=145,
        min_ram_mb=1024, hf_repo_id="Systran/faster-whisper-base", is_directory=True,
    ),
    "whisper-small": ModelInfo(
        id="whisper-small", name="Whisper Small", category=ModelCategory.ASR,
        description="ASR small. Mejor calidad.", license="MIT", size_mb=480,
        min_ram_mb=2048, hf_repo_id="Systran/faster-whisper-small", is_directory=True,
    ),
    "whisper-medium": ModelInfo(
        id="whisper-medium", name="Whisper Medium", category=ModelCategory.ASR,
        description="ASR medium. Calidad alta.", license="MIT", size_mb=1500,
        min_ram_mb=4096, min_vram_mb=2048, hf_repo_id="Systran/faster-whisper-medium", is_directory=True,
    ),
    "whisper-large-v3": ModelInfo(
        id="whisper-large-v3", name="Whisper Large v3", category=ModelCategory.ASR,
        description="ASR más preciso.", license="MIT", size_mb=3000,
        min_ram_mb=6144, min_vram_mb=4096, hf_repo_id="Systran/faster-whisper-large-v3", is_directory=True,
    ),
    "pyannote-3.1": ModelInfo(
        id="pyannote-3.1", name="Pyannote Speaker Diarization 3.1", category=ModelCategory.DIARIZATION,
        description="Diarización de hablantes. Requiere aceptar licencia en HF.",
        license="CC-BY-NC-SA-4.0 + HF gate", license_url="https://huggingface.co/pyannote/speaker-diarization-3.1",
        size_mb=200, min_ram_mb=1024, min_vram_mb=1024,
        requires_hf_token=True, requires_license_acceptance=True,
        hf_repo_id="pyannote/speaker-diarization-3.1", is_directory=True,
        dependencies=["pyannote-segmentation-3.0"],
    ),
    "pyannote-segmentation-3.0": ModelInfo(
        id="pyannote-segmentation-3.0", name="Pyannote Segmentation 3.0", category=ModelCategory.DIARIZATION,
        description="Modelo de segmentación (dependencia).", license="MIT", size_mb=20,
        hf_repo_id="pyannote/segmentation-3.0", is_directory=True,
    ),
    "speechbrain-ecapa": ModelInfo(
        id="speechbrain-ecapa", name="SpeechBrain ECAPA Speaker", category=ModelCategory.EMBEDDING,
        description="Embeddings de voz. Alternativa Apache 2.0 a pyannote.",
        license="Apache-2.0", size_mb=85, hf_repo_id="speechbrain/spkrec-ecapa-voxceleb", is_directory=True,
    ),
    "opus-mt-en-es": ModelInfo(
        id="opus-mt-en-es", name="Opus-MT Inglés→Español", category=ModelCategory.TRANSLATION,
        description="Traducción EN→ES.", license="CC-BY-4.0", size_mb=300, min_ram_mb=512,
        languages=["en→es"], hf_repo_id="Helsinki-NLP/opus-mt-en-es", is_directory=True,
    ),
    "opus-mt-fr-es": ModelInfo(
        id="opus-mt-fr-es", name="Opus-MT Francés→Español", category=ModelCategory.TRANSLATION,
        description="Traducción FR→ES.", license="CC-BY-4.0", size_mb=300, languages=["fr→es"],
        hf_repo_id="Helsinki-NLP/opus-mt-fr-es", is_directory=True,
    ),
    "opus-mt-de-es": ModelInfo(
        id="opus-mt-de-es", name="Opus-MT Alemán→Español", category=ModelCategory.TRANSLATION,
        description="Traducción DE→ES.", license="CC-BY-4.0", size_mb=300, languages=["de→es"],
        hf_repo_id="Helsinki-NLP/opus-mt-de-es", is_directory=True,
    ),
    "opus-mt-it-es": ModelInfo(
        id="opus-mt-it-es", name="Opus-MT Italiano→Español", category=ModelCategory.TRANSLATION,
        description="Traducción IT→ES.", license="CC-BY-4.0", size_mb=300, languages=["it→es"],
        hf_repo_id="Helsinki-NLP/opus-mt-it-es", is_directory=True,
    ),
    "opus-mt-pt-es": ModelInfo(
        id="opus-mt-pt-es", name="Opus-MT Portugués→Español", category=ModelCategory.TRANSLATION,
        description="Traducción PT→ES.", license="CC-BY-4.0", size_mb=300, languages=["pt→es"],
        hf_repo_id="Helsinki-NLP/opus-mt-pt-es", is_directory=True,
    ),
    "opus-mt-mul-es": ModelInfo(
        id="opus-mt-mul-es", name="Opus-MT Multi→Español", category=ModelCategory.TRANSLATION,
        description="Traducción multi-idioma → ES.", license="CC-BY-4.0", size_mb=300,
        languages=["multi→es"], hf_repo_id="Helsinki-NLP/opus-mt-mul-es", is_directory=True,
    ),
    "piper-es_ES-davefx-medium": ModelInfo(
        id="piper-es_ES-davefx-medium", name="Piper Voz Española (davefx medium)", category=ModelCategory.TTS,
        description="Voz española masculina. Recomendada.", license="MIT", size_mb=63, min_ram_mb=128,
        languages=["es"], hf_repo_id="rhasspy/piper-voices",
        hf_filename="es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
    ),
    "piper-es_ES-davefx-x_low": ModelInfo(
        id="piper-es_ES-davefx-x_low", name="Piper Voz Española (davefx x_low)", category=ModelCategory.TTS,
        description="Voz española muy ligera.", license="MIT", size_mb=22, min_ram_mb=64,
        hf_repo_id="rhasspy/piper-voices", hf_filename="es/es_ES/davefx/x_low/es_ES-davefx-x_low.onnx",
    ),
    "piper-es_ES-carlfm-x_low": ModelInfo(
        id="piper-es_ES-carlfm-x_low", name="Piper Voz Española (carlfm x_low)", category=ModelCategory.TTS,
        description="Voz española alternativa.", license="MIT", size_mb=22,
        hf_repo_id="rhasspy/piper-voices", hf_filename="es/es_ES/carlfm/x_low/es_ES-carlfm-x_low.onnx",
    ),
    "piper-es_ES-mls_9972-medium": ModelInfo(
        id="piper-es_ES-mls_9972-medium", name="Piper Voz Española MLS 9972", category=ModelCategory.TTS,
        description="Voz española alternativa masculina.", license="CC-0", size_mb=63,
        hf_repo_id="rhasspy/piper-voices", hf_filename="es/es_ES/mls_9972/medium/es_ES-mls_9972-medium.onnx",
    ),
    "xtts-v2": ModelInfo(
        id="xtts-v2", name="Coqui XTTS v2", category=ModelCategory.VOICE_CLONING,
        description="Clonación de voz multi-idioma. CPML no-comercial.",
        license="CPML (non-commercial)", license_url="https://coqui.ai/cpml",
        size_mb=1800, min_ram_mb=2048, min_vram_mb=2048,
        non_commercial_only=True, requires_license_acceptance=True,
        hf_repo_id="coqui/XTTS-v2", is_directory=True,
    ),
    "htdemucs": ModelInfo(
        id="htdemucs", name="Demucs htdemucs", category=ModelCategory.AUDIO_SEPARATION,
        description="Separación avanzada de audio.", license="MIT", size_mb=80, min_ram_mb=1024,
        hf_repo_id="facebookresearch/demucs", is_directory=True,
    ),
}


class ModelManager:
    MANIFEST_NAME = "manifest.json"

    def __init__(self, models_dir: Path, hf_token: str = ""):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.hf_token = hf_token
        self._manifest_path = self.models_dir / self.MANIFEST_NAME

    def get_path(self, model_id: str) -> Path:
        return self.models_dir / model_id

    def is_installed(self, model_id: str) -> bool:
        p = self.get_path(model_id)
        if not p.exists():
            return False
        if p.is_file():
            return p.stat().st_size > 0
        return any(p.iterdir())

    def get_status(self, model_id: str) -> ModelStatus:
        if not self.is_installed(model_id):
            return ModelStatus.NOT_INSTALLED
        return ModelStatus.INSTALLED

    def list_models(self, category: Optional[ModelCategory] = None) -> list:
        if category:
            return [m for m in KNOWN_MODELS.values() if m.category == category]
        return list(KNOWN_MODELS.values())

    def list_installed(self) -> list:
        return [mid for mid in KNOWN_MODELS if self.is_installed(mid)]

    def list_required_for_pipeline(self, asr_id="whisper-base", translation_id="opus-mt-en-es",
                                   tts_id="piper-es_ES-davefx-medium", with_diarization=True,
                                   with_voice_cloning=False, with_separation=False) -> list:
        required = [asr_id, translation_id, tts_id]
        if with_diarization:
            required.append("speechbrain-ecapa")
        if with_voice_cloning:
            required.append("xtts-v2")
        if with_separation:
            required.append("htdemucs")
        seen = set()
        stack = list(required)
        while stack:
            mid = stack.pop()
            if mid in seen:
                continue
            seen.add(mid)
            info = KNOWN_MODELS.get(mid)
            if info:
                for dep in info.dependencies:
                    if dep not in seen:
                        stack.append(dep)
        return sorted(seen)

    def download(self, model_id: str, force: bool = False, progress_cb=None) -> Path:
        if model_id not in KNOWN_MODELS:
            raise ValueError(f"Modelo desconocido: {model_id}")
        info = KNOWN_MODELS[model_id]
        target = self.get_path(model_id)
        if self.is_installed(model_id) and not force:
            log.info("Modelo {} ya instalado", model_id)
            return target
        for dep in info.dependencies:
            if not self.is_installed(dep):
                self.download(dep, force=force, progress_cb=progress_cb)
        log.info("Descargando modelo '{}'...", model_id)
        if info.requires_hf_token and not self.hf_token:
            raise RuntimeError(f"El modelo {model_id} requiere un token de HuggingFace.")
        target.parent.mkdir(parents=True, exist_ok=True)
        if info.is_directory:
            self._download_repo(info, target, progress_cb)
        else:
            if target.exists() and target.is_file():
                target = target.parent / (target.name + "_dir")
            target.mkdir(parents=True, exist_ok=True)
            file_target = target / Path(info.hf_filename).name
            self._download_file(info, file_target, progress_cb)
        manifest = self._load_manifest()
        actual_size = self._dir_size(target) if target.is_dir() else target.stat().st_size
        manifest[model_id] = {"size_bytes": actual_size, "version": info.version, "license": info.license}
        self._save_manifest(manifest)
        log.info("Modelo {} descargado ({} MB)", model_id, actual_size // (1024*1024))
        return target

    def _download_file(self, info: ModelInfo, target: Path, progress_cb=None) -> None:
        base_url = f"https://huggingface.co/{info.hf_repo_id}/resolve/main/{info.hf_filename}"
        self._http_download(base_url, target, progress_cb, info)
        if info.hf_filename.endswith(".onnx"):
            json_url = base_url + ".json"
            json_target = target.with_suffix(target.suffix + ".json")
            try:
                self._http_download(json_url, json_target, None, info)
            except Exception:
                pass

    def _download_repo(self, info: ModelInfo, target: Path, progress_cb=None) -> None:
        try:
            from huggingface_hub import snapshot_download
            kwargs = {"repo_id": info.hf_repo_id, "local_dir": str(target)}
            if self.hf_token:
                kwargs["token"] = self.hf_token
            snapshot_download(**kwargs)
        except ImportError:
            if info.hf_filename:
                self._download_file(info, target / Path(info.hf_filename).name, progress_cb)
            else:
                raise RuntimeError(f"No se puede descargar {info.id} sin huggingface_hub.")

    def _http_download(self, url: str, target: Path, progress_cb, info: ModelInfo) -> None:
        headers = {"User-Agent": "VidDoblaje/1.0"}
        if self.hf_token:
            headers["Authorization"] = f"Bearer {self.hf_token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(target, "wb") as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

    def remove(self, model_id: str) -> None:
        target = self.get_path(model_id)
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.is_file():
            target.unlink(missing_ok=True)
        manifest = self._load_manifest()
        manifest.pop(model_id, None)
        self._save_manifest(manifest)

    def verify(self, model_id: str) -> bool:
        return self.get_status(model_id) == ModelStatus.INSTALLED

    def repair(self, model_id: str) -> None:
        self.remove(model_id)
        self.download(model_id, force=True)

    def disk_usage(self) -> dict:
        usage = {}
        manifest = self._load_manifest()
        for mid, entry in manifest.items():
            info = KNOWN_MODELS.get(mid)
            if info:
                cat = info.category.value
                usage[cat] = usage.get(cat, 0) + entry.get("size_bytes", 0)
        return usage

    def total_size_mb(self) -> int:
        total = 0
        for mid in KNOWN_MODELS:
            p = self.get_path(mid)
            if p.is_dir():
                total += self._dir_size(p)
            elif p.is_file():
                total += p.stat().st_size
        return total // (1024 * 1024)

    @staticmethod
    def _dir_size(p: Path) -> int:
        if p.is_file():
            return p.stat().st_size
        total = 0
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        return total

    def _load_manifest(self) -> dict:
        if not self._manifest_path.exists():
            return {}
        try:
            with open(self._manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_manifest(self, data: dict) -> None:
        tmp = self._manifest_path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp.replace(self._manifest_path)
