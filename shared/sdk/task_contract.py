"""
CoCompute Task SDK — Backward-Compatible Contract Aliases.

The canonical 7-hook Task Contract lives in task_definition.py (TaskDefinition).
This module provides:
  - ResourceEstimate: dataclass for declaring CPU/RAM/GPU/VRAM requirements
  - TaskContext: dataclass for per-chunk execution context
  - BaseTaskDefinition: thin backward-compatible alias → TaskDefinition

All new tasks should inherit from TaskDefinition directly.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from .task_definition import TaskDefinition


@dataclass
class ResourceEstimate:
    """Resource requirements declared by a task before scheduling."""
    cpu_cores: int = 2
    ram_mb: int = 1024
    gpu_required: bool = False
    vram_mb: int = 0
    estimated_io_mb: float = 1.0
    expected_cpu_intensity: str = "HIGH"  # LOW, MEDIUM, HIGH, INTENSIVE


@dataclass
class TaskContext:
    """Per-chunk execution context passed through the task lifecycle."""
    task_id: Optional[str] = None
    chunk_index: int = 0
    total_chunks: int = 1
    attempt_number: int = 1
    worker_uid: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Backward-Compatible Alias ────────────────────────────────────────────────
# BaseTaskDefinition is preserved for any code that imports it.
# New tasks should inherit from TaskDefinition (shared.sdk.task_definition).
BaseTaskDefinition = TaskDefinition
