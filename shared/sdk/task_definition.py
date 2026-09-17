"""
CoCompute Task SDK — Canonical 7-Hook Task Contract.

Every distributed task in CoCompute implements this contract:
  1. validate_input(input_data) -> (bool, str)       — reject malformed input early
  2. estimate_resources(input_data) -> ResourceEstimate — declare CPU/RAM/GPU/VRAM needs
  3. partition(input_data, chunks) -> List[dict]       — decompose into parallel chunks
  4. execute(payload) -> dict                          — run one chunk (on worker)
  5. validate_partial(chunk_result) -> (bool, str)     — validate before acceptance
  6. aggregate(results) -> dict                        — combine all accepted results
  7. validate_final(final_result, input_data) -> (bool, str) — end-to-end correctness

System Invariant: CORRECTNESS > STATUS
A job cannot be COMPLETED unless validate_final() passes.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Tuple, List


class TaskDefinition(ABC):
    """
    Abstract Base Class defining the lifecycle and execution contract for CoCompute tasks.
    """
    task_type: str = "base_task"
    display_name: str = "Base Task"
    description: str = "Base distributed task contract"
    requires_gpu: bool = False
    min_vram_gb: float = 0.0
    min_cpu_cores: int = 1
    min_ram_gb: float = 1.0
    timeout_seconds: int = 300

    def resource_requirements(self) -> Dict[str, Any]:
        """
        Declare minimum CPU cores, RAM GB, GPU count, VRAM GB, and estimated time.
        CIE uses this to filter and score workers.
        """
        return {
            "min_cpu_cores": self.min_cpu_cores,
            "min_ram_gb": self.min_ram_gb,
            "requires_gpu": self.requires_gpu,
            "min_vram_gb": self.min_vram_gb,
            "timeout_seconds": self.timeout_seconds
        }

    def estimate_resources(self, input_data: Any) -> Dict[str, Any]:
        """
        Hook 2: Estimate resource needs based on actual input data size.
        Override in subclasses for data-aware estimation.
        Returns dict with keys: cpu_cores, ram_mb, gpu_required, vram_mb, estimated_io_mb.
        """
        size_estimate_mb = 1.0
        if isinstance(input_data, dict):
            size_estimate_mb = max(0.1, len(str(input_data)) / (1024 * 1024))
        return {
            "cpu_cores": self.min_cpu_cores,
            "ram_mb": int(self.min_ram_gb * 1024),
            "gpu_required": self.requires_gpu,
            "vram_mb": int(self.min_vram_gb * 1024),
            "estimated_io_mb": round(size_estimate_mb, 2),
        }

    def validate_input(self, input_data: dict) -> Tuple[bool, str]:
        """
        2. Validate input before partitioning.
        Reject malformed or unsupported input immediately.
        """
        if not isinstance(input_data, dict):
            return False, "Input data must be a dictionary"
        return True, ""

    @abstractmethod
    def partition(self, input_data: dict, chunks: int) -> List[dict]:
        """
        3. Partition the input dataset into independent chunks for parallel execution.
        """
        pass

    @abstractmethod
    def execute(self, payload: dict) -> dict:
        """
        4. Execute computation for an individual chunk (runs inside Docker container on Worker).
        """
        pass

    def validate_partial(self, chunk_result: dict) -> Tuple[bool, str]:
        """
        5. Validate worker output before accepting it into aggregation.
        """
        if not isinstance(chunk_result, dict):
            return False, "Chunk result must be a dictionary"
        return True, ""

    @abstractmethod
    def aggregate(self, results: List[dict]) -> dict:
        """
        6. Combine all partial chunk results into a single globally aggregated result.
        """
        pass

    def validate_final(self, final_result: dict, input_data: Optional[dict] = None) -> Tuple[bool, str]:
        """
        7. Verify the mathematical correctness, completeness, and integrity
        of the final aggregated result.

        System Invariant: CORRECTNESS > STATUS
        If this returns (False, error), the job MUST NOT be marked COMPLETED.
        The aggregator will set job.status = 'validation_failed' instead.
        """
        if not isinstance(final_result, dict):
            return False, "Final result must be a dictionary"
        return True, ""
