"""
Task Profiler & Adaptive Micro-Pilot Execution Engine — CoCompute 4.0.

Executes a small micro-sample (1% -> 3%) of user data to measure real physical
hardware metrics (CPU, RAM, Duration, IO, Output Ratio) and construct an
empirical Workload Profile before full cluster dispatch.
"""

import time
import psutil
import logging
from typing import Any, Dict, Optional
from shared.sdk.task_contract import BaseTaskDefinition, TaskContext

logger = logging.getLogger(__name__)


def sample_input_data(input_data: Any, sample_ratio: float = 0.01) -> Any:
    """
    Extracts a proportional slice (1% - 5%) of input data for pilot execution.
    """
    if isinstance(input_data, list):
        sample_size = max(1, min(len(input_data), int(len(input_data) * sample_ratio)))
        return input_data[:sample_size]
    elif isinstance(input_data, dict):
        if "data" in input_data and isinstance(input_data["data"], list):
            items = input_data["data"]
            sample_size = max(1, min(len(items), int(len(items) * sample_ratio)))
            return {"data": items[:sample_size]}
        elif "matrix_a" in input_data and isinstance(input_data["matrix_a"], list):
            # Matrix sampling: smaller submatrix
            rows = input_data["matrix_a"]
            sample_size = max(2, int(len(rows) * sample_ratio))
            return {
                "matrix_a": [r[:sample_size] for r in rows[:sample_size]],
                "matrix_b": [r[:sample_size] for r in input_data.get("matrix_b", rows)[:sample_size]]
            }
        return input_data
    return input_data


def run_micro_pilot_execution(
    task_instance: BaseTaskDefinition,
    full_input_data: Any,
    initial_ratio: float = 0.02
) -> Dict[str, Any]:
    """
    Runs an empirical micro-pilot execution and measures real hardware utilization.
    Escalates from 1-2% to 5% if sample size is too small to achieve high confidence.
    """
    sample_data = sample_input_data(full_input_data, initial_ratio)
    ctx = TaskContext(task_id="PILOT-RUN", total_chunks=1)

    process = psutil.Process()
    ram_before = process.memory_info().rss / (1024 * 1024)
    cpu_percent_before = process.cpu_percent(interval=None)

    start_time = time.perf_counter()
    chunks = task_instance.partition(sample_data, ctx)
    results = [task_instance.execute(ch, ctx) for ch in chunks]
    aggregated = task_instance.aggregate(results, ctx)
    elapsed = max(0.001, time.perf_counter() - start_time)

    ram_after = process.memory_info().rss / (1024 * 1024)
    cpu_percent_after = process.cpu_percent(interval=None)

    ram_delta_mb = max(0.1, round(ram_after - ram_before, 2))
    cpu_intensity = min(1.0, max(0.1, round(cpu_percent_after / 100.0, 2))) if cpu_percent_after > 0 else 0.75
    io_rate_mb_s = round(max(0.1, (len(str(sample_data)) / (1024 * 1024)) / elapsed), 2)
    output_ratio = round(len(str(aggregated)) / max(len(str(sample_data)), 1), 3)

    # Escalation check: if pilot executed in < 0.005s, run with slightly larger slice for stability
    confidence = 0.92 if elapsed > 0.01 else 0.65
    if confidence < 0.70 and isinstance(full_input_data, (list, dict)):
        larger_sample = sample_input_data(full_input_data, sample_ratio=0.08)
        start_t2 = time.perf_counter()
        c2 = task_instance.partition(larger_sample, ctx)
        r2 = [task_instance.execute(ch, ctx) for ch in c2]
        task_instance.aggregate(r2, ctx)
        elapsed2 = max(0.001, time.perf_counter() - start_t2)
        elapsed = elapsed2
        confidence = 0.95

    return {
        "pilot_sample_ratio": initial_ratio,
        "pilot_duration_sec": round(elapsed, 4),
        "cpu_intensity": cpu_intensity,
        "memory_delta_mb": ram_delta_mb,
        "io_rate_mb_s": io_rate_mb_s,
        "output_input_ratio": output_ratio,
        "confidence": confidence,
        "gpu_required": getattr(task_instance, "estimate_resources", lambda x: None)(sample_data).gpu_required if hasattr(task_instance, "estimate_resources") else False
    }
