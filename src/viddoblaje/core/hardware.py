"""Detección automática de hardware."""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import psutil

from viddoblaje.utils import get_logger

log = get_logger(__name__)


class GpuVendor(str, Enum):
    NONE = "none"
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    APPLE = "apple"
    UNKNOWN = "unknown"


class HardwareProfile(str, Enum):
    ULTRA_LOW = "ultra_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class GpuInfo:
    index: int
    vendor: GpuVendor
    name: str
    vram_mb: int = 0
    cuda_support: bool = False
    directml_support: bool = False


@dataclass
class HardwareInfo:
    os_name: str = ""
    os_version: str = ""
    cpu_name: str = ""
    cpu_cores_physical: int = 0
    cpu_cores_logical: int = 0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    gpus: list = field(default_factory=list)
    disk_free_mb: int = 0
    disk_total_mb: int = 0
    python_version: str = ""
    has_cuda: bool = False
    has_directml: bool = False

    @property
    def best_gpu(self) -> Optional[GpuInfo]:
        if not self.gpus:
            return None
        nvidia_cuda = [g for g in self.gpus if g.vendor == GpuVendor.NVIDIA and g.cuda_support]
        if nvidia_cuda:
            return max(nvidia_cuda, key=lambda g: g.vram_mb)
        nvidia = [g for g in self.gpus if g.vendor == GpuVendor.NVIDIA]
        if nvidia:
            return max(nvidia, key=lambda g: g.vram_mb)
        return max(self.gpus, key=lambda g: g.vram_mb)

    @property
    def is_cpu_only(self) -> bool:
        return not self.gpus

    def recommend_profile(self) -> HardwareProfile:
        ram_gb = self.ram_total_mb / 1024
        vram_gb = (self.best_gpu.vram_mb if self.best_gpu else 0) / 1024
        if not self.best_gpu or self.best_gpu.vram_mb == 0:
            if ram_gb < 4:
                return HardwareProfile.ULTRA_LOW
            if ram_gb < 8:
                return HardwareProfile.LOW
            return HardwareProfile.MEDIUM
        if vram_gb >= 8 and ram_gb >= 16:
            return HardwareProfile.MAXIMUM
        if vram_gb >= 6 and ram_gb >= 12:
            return HardwareProfile.HIGH
        if vram_gb >= 2 and ram_gb >= 8:
            return HardwareProfile.MEDIUM
        if vram_gb >= 1:
            return HardwareProfile.LOW
        return HardwareProfile.ULTRA_LOW


def _detect_nvidia_gpus() -> list[GpuInfo]:
    if not shutil.which("nvidia-smi"):
        return []
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=10,
        ).decode("utf-8", errors="ignore")
        gpus = []
        for i, line in enumerate(out.strip().splitlines()):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                continue
            try:
                vram = int(float(parts[2]))
            except ValueError:
                vram = 0
            gpus.append(GpuInfo(index=i, vendor=GpuVendor.NVIDIA, name=parts[1], vram_mb=vram, cuda_support=True))
        return gpus
    except Exception:
        return []


def _detect_torch_gpus() -> list[GpuInfo]:
    gpus: list[GpuInfo] = []
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                props = torch.cuda.get_device_properties(i)
                gpus.append(GpuInfo(index=i, vendor=GpuVendor.NVIDIA, name=name, vram_mb=int(props.total_memory / 1024 / 1024), cuda_support=True))
    except Exception:
        pass
    return gpus


def detect_hardware() -> HardwareInfo:
    info = HardwareInfo()
    info.python_version = sys.version
    info.os_name = platform.system()
    info.os_version = platform.version()
    info.cpu_name = platform.processor() or "Unknown CPU"
    info.cpu_cores_physical = psutil.cpu_count(logical=False) or 1
    info.cpu_cores_logical = psutil.cpu_count(logical=True) or 1
    vm = psutil.virtual_memory()
    info.ram_total_mb = int(vm.total / 1024 / 1024)
    info.ram_available_mb = int(vm.available / 1024 / 1024)
    try:
        disk = psutil.disk_usage(str(Path.home()))
        info.disk_free_mb = int(disk.free / 1024 / 1024)
        info.disk_total_mb = int(disk.total / 1024 / 1024)
    except Exception:
        pass
    gpus = _detect_nvidia_gpus()
    if not gpus:
        gpus = _detect_torch_gpus()
    info.gpus = gpus
    info.has_cuda = any(g.cuda_support for g in gpus)
    info.has_directml = any(g.directml_support for g in gpus)
    log.info("Hardware: OS={} {}, CPU={} ({}c/{}t), RAM={}MB, GPUs={}", info.os_name, info.os_version, info.cpu_name, info.cpu_cores_physical, info.cpu_cores_logical, info.ram_total_mb, len(info.gpus))
    return info


def get_device(pref: str = "auto", info: HardwareInfo | None = None) -> str:
    if info is None:
        info = detect_hardware()
    if pref == "cpu":
        return "cpu"
    if pref != "auto":
        return pref
    if info.has_cuda:
        return "cuda:0"
    return "cpu"
