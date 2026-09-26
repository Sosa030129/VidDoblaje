"""Core: reexporta módulos principales."""
from .checkpoint import CheckpointManager, STAGE_ORDER
from .hardware import detect_hardware, get_device, HardwareInfo, HardwareProfile
from .model_manager import ModelManager, KNOWN_MODELS, ModelInfo, ModelStatus, ModelCategory
from .project import Project, ProjectMeta, ProjectStatus, Speaker, Segment
from .queue_manager import QueueManager, Job, JobStatus

__all__ = [
    "CheckpointManager", "STAGE_ORDER",
    "detect_hardware", "get_device", "HardwareInfo", "HardwareProfile",
    "ModelManager", "KNOWN_MODELS", "ModelInfo", "ModelStatus", "ModelCategory",
    "Project", "ProjectMeta", "ProjectStatus", "Speaker", "Segment",
    "QueueManager", "Job", "JobStatus",
]
