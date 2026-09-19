"""
Workload Intelligence Layer — CoCompute Workload Profiler.

Inspects incoming job parameters, data volume, and algorithmic profile to determine:
  - CPU intensity (0.0 to 1.0)
  - GPU intensity (0.0 to 1.0)
  - Memory footprint intensity (0.0 to 1.0)
  - Network transfer intensity (0.0 to 1.0)
  - Recommended scheduling strategy
  - Recommended dynamic chunk pool size
  - Estimated computational complexity
"""

import math
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


def profile_workload(job_type: str, params: Dict[str, Any], priority: str = "NORMAL", energy_mode: str = "BALANCED") -> Dict[str, Any]:
    """
    Analyzes task parameters and computes multi-dimensional workload profile.
    """
    cpu_intensity = 0.5
    gpu_intensity = 0.0
    memory_intensity = 0.3
    network_intensity = 0.2
    parallelism_potential = 0.8
    recommended_strategy = "capacity_based"
    estimated_data_mb = 1.0
    recommended_chunks = int(params.get("chunks", 5))

    if job_type == "sorting":
        size = int(params.get("array_size", 10000))
        estimated_data_mb = (size * 8) / (1024 * 1024)
        cpu_intensity = 0.85
        memory_intensity = min(1.0, 0.2 + (size / 1_000_000) * 0.6)
        network_intensity = 0.4 if size > 500000 else 0.2
        parallelism_potential = 0.95
        
        # Strategy selection
        if size < 50000:
            recommended_strategy = "least_loaded"
            recommended_chunks = max(2, min(4, recommended_chunks))
        else:
            recommended_strategy = "capacity_based"
            recommended_chunks = max(4, min(16, math.ceil(size / 50000)))

    elif job_type == "matrix_multiply":
        rows_a = int(params.get("rows_a", 50))
        cols_a = int(params.get("cols_a", 50))
        cols_b = int(params.get("cols_b", 50))
        total_ops = rows_a * cols_a * cols_b
        estimated_data_mb = (rows_a * cols_a + cols_a * cols_b) * 8 / (1024 * 1024)
        cpu_intensity = 0.95
        memory_intensity = 0.5
        network_intensity = 0.3
        parallelism_potential = 0.9
        recommended_strategy = "capacity_based" if total_ops > 100000 else "least_loaded"
        recommended_chunks = max(2, min(12, math.ceil(rows_a / 10)))

    elif job_type == "statistics":
        size = int(params.get("array_size", 1000))
        estimated_data_mb = (size * 8) / (1024 * 1024)
        cpu_intensity = 0.6
        memory_intensity = 0.3
        network_intensity = 0.1
        parallelism_potential = 0.85
        recommended_strategy = "least_loaded" if size < 100000 else "capacity_based"

    elif job_type == "search":
        size = int(params.get("array_size", 100000))
        estimated_data_mb = (size * 8) / (1024 * 1024)
        cpu_intensity = 0.7
        memory_intensity = 0.4
        network_intensity = 0.2
        parallelism_potential = 0.95
        recommended_strategy = "least_loaded"

    elif job_type == "word_count":
        text = str(params.get("text", ""))
        word_count = len(text.split())
        estimated_data_mb = max(0.1, len(text) / (1024 * 1024))
        cpu_intensity = 0.5
        memory_intensity = 0.3
        network_intensity = 0.5 if estimated_data_mb > 10 else 0.2
        parallelism_potential = 0.9
        recommended_strategy = "least_loaded"

    elif job_type == "image_processing":
        imgs = int(params.get("images_count", 5))
        estimated_data_mb = max(0.5, imgs * 0.2)
        cpu_intensity = 0.75
        memory_intensity = 0.6
        network_intensity = 0.6
        parallelism_potential = 0.95
        recommended_strategy = "capacity_based"

    elif job_type == "prime_generation":
        start = int(params.get("start", 1))
        end = int(params.get("end", 100000))
        range_size = end - start
        cpu_intensity = 0.9
        memory_intensity = 0.2
        network_intensity = 0.1
        parallelism_potential = 0.95
        recommended_strategy = "capacity_based" if range_size > 50000 else "least_loaded"

    elif job_type in ("ml_training", "distributed_inference", "llm_finetune"):
        gpu_intensity = 0.95
        cpu_intensity = 0.4
        memory_intensity = 0.9
        network_intensity = 0.8
        parallelism_potential = 0.9
        recommended_strategy = "gpu_aware"
        estimated_data_mb = float(params.get("dataset_size", 1000)) * 0.05

    elif job_type == "cipher":
        cpu_intensity = 0.4
        memory_intensity = 0.2
        network_intensity = 0.1
        parallelism_potential = 0.8
        recommended_strategy = "least_loaded"

    # Priority & Energy Mode Modifiers
    if priority in ("HIGH", "CRITICAL"):
        recommended_strategy = "priority_based"
    elif energy_mode == "ECO":
        recommended_strategy = "least_loaded"

    profile = {
        "job_type": job_type,
        "cpu_intensity": round(cpu_intensity, 2),
        "gpu_intensity": round(gpu_intensity, 2),
        "memory_intensity": round(memory_intensity, 2),
        "network_intensity": round(network_intensity, 2),
        "parallelism_potential": round(parallelism_potential, 2),
        "estimated_data_mb": round(estimated_data_mb, 2),
        "recommended_strategy": recommended_strategy,
        "recommended_chunks": recommended_chunks,
        "is_gpu_required": gpu_intensity > 0.5 or job_type in ("ml_training", "distributed_inference", "llm_finetune")
    }

    logger.info(f"Workload Profile for {job_type}: {profile}")
    return profile
