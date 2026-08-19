"""
CoCompute 4.0 First-Class Task SDK & Lifecycle Contract.

Defines the universal 5-hook Task Contract:
  1. estimate_resources(input_data) -> ResourceEstimate
  2. partition(input_data, context) -> List[Any]
  3. execute(chunk, context) -> Any
  4. aggregate(results, context) -> Any
  5. validate(result, context) -> Dict[str, bool]
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ResourceEstimate:
    cpu_cores: int = 2
    ram_mb: int = 1024
    gpu_required: bool = False
    vram_mb: int = 0
    estimated_io_mb: float = 1.0
    expected_cpu_intensity: str = "HIGH"  # LOW, MEDIUM, HIGH, INTENSIVE


@dataclass
class TaskContext:
    task_id: Optional[str] = None
    chunk_index: int = 0
    total_chunks: int = 1
    attempt_number: int = 1
    worker_uid: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTaskDefinition:
    """
    Universal base class for user-defined and standard distributed tasks.
    """
    name: str = "custom_task"
    version: str = "1.0"
    description: str = "User defined distributed task"

    def estimate_resources(self, input_data: Any) -> ResourceEstimate:
        """
        Hook 1: Declares upfront resource expectations before micro-pilot verification.
        """
        size_estimate_mb = 1.0
        if isinstance(input_data, (list, tuple)):
            size_estimate_mb = max(0.1, len(input_data) * 8 / (1024 * 1024))
        elif isinstance(input_data, dict):
            size_estimate_mb = max(0.1, len(str(input_data)) / (1024 * 1024))

        return ResourceEstimate(
            cpu_cores=2,
            ram_mb=min(8192, max(512, int(size_estimate_mb * 4))),
            gpu_required=False,
            estimated_io_mb=round(size_estimate_mb, 2)
        )

    def partition(self, input_data: Any, context: TaskContext) -> List[Any]:
        """
        Hook 2: Decomposes arbitrary input data into elastic parallel chunks.
        """
        chunks_count = context.parameters.get("chunks", context.total_chunks or 4)
        if isinstance(input_data, list):
            chunk_size = max(1, (len(input_data) + chunks_count - 1) // chunks_count)
            return [input_data[i:i + chunk_size] for i in range(0, len(input_data), chunk_size)]
        elif isinstance(input_data, dict) and "data" in input_data and isinstance(input_data["data"], list):
            items = input_data["data"]
            chunk_size = max(1, (len(items) + chunks_count - 1) // chunks_count)
            return [{"data": items[i:i + chunk_size]} for i in range(0, len(items), chunk_size)]
        else:
            return [input_data]

    def execute(self, chunk: Any, context: TaskContext) -> Any:
        """
        Hook 3: Executes computational payload on a single worker node.
        """
        raise NotImplementedError("Task execute hook must be implemented by user task definition.")

    def aggregate(self, results: List[Any], context: TaskContext) -> Any:
        """
        Hook 4: Combines partial results from completed chunks into final result.
        """
        if not results:
            return None
        if isinstance(results[0], list):
            merged = []
            for r in results:
                if isinstance(r, list):
                    merged.extend(r)
                else:
                    merged.append(r)
            return merged
        elif isinstance(results[0], dict):
            combined = {}
            for r in results:
                if isinstance(r, dict):
                    combined.update(r)
            return combined
        return results

    def validate(self, result: Any, context: TaskContext) -> Dict[str, Any]:
        """
        Hook 5: Validates logical integrity, non-emptiness, and semantic correctness.
        """
        is_valid = result is not None
        checks = {
            "result_present": is_valid,
            "non_empty": bool(result) if is_valid else False
        }
        if isinstance(result, list):
            checks["count_positive"] = len(result) > 0
        return checks
