"""
CoCompute Task SDK — Core Contract Definitions.

Every distributed task in CoCompute implements the 7-method TaskDefinition contract:
  1. resource_requirements(self) -> dict
  2. validate_input(self, input_data) -> (is_valid: bool, error_msg: str)
  3. partition(self, input_data, chunks) -> list of chunk payloads
  4. execute(self, payload) -> chunk result dictionary
  5. validate_partial(self, chunk_result) -> (is_valid: bool, error_msg: str)
  6. aggregate(self, results) -> global aggregated result
  7. validate_final(self, final_result, input_data) -> (is_valid: bool, error_msg: str)
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
        1. Declare minimum CPU cores, RAM GB, GPU count, VRAM GB, and estimated time.
        CIE uses this to filter and score workers.
        """
        return {
            "min_cpu_cores": self.min_cpu_cores,
            "min_ram_gb": self.min_ram_gb,
            "requires_gpu": self.requires_gpu,
            "min_vram_gb": self.min_vram_gb,
            "timeout_seconds": self.timeout_seconds
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
        7. Verify the mathematical correctness, completeness, and integrity of the final aggregated result.
        """
        if not isinstance(final_result, dict):
            return False, "Final result must be a dictionary"
        return True, ""
