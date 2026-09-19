"""
Worker Reliability Intelligence Engine — CoCompute.

Calculates the 5-factor composite reliability score:
  Score = 0.30 * success_rate
        + 0.20 * execution_consistency
        + 0.20 * uptime
        + 0.15 * network_stability
        + 0.15 * thermal_stability
"""

import math
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..db import models

logger = logging.getLogger(__name__)


def compute_worker_reliability(worker: models.Worker, db: Session) -> Dict[str, float]:
    """
    Computes fine-grained 5-factor reliability breakdown and updates the composite score.
    """
    total_completed = worker.total_tasks_completed or 0
    total_failed = worker.total_tasks_failed or 0
    total_tasks = total_completed + total_failed

    # 1. Success Rate (0.0 to 1.0)
    if total_tasks > 0:
        success_rate = total_completed / total_tasks
    else:
        success_rate = 1.0

    # 2. Execution Consistency (0.0 to 1.0 based on runtime variance)
    recent_attempts = db.query(models.ChunkAttempt).filter(
        models.ChunkAttempt.worker_id == worker.id,
        models.ChunkAttempt.status == "completed",
        models.ChunkAttempt.duration_seconds.isnot(None)
    ).order_by(models.ChunkAttempt.id.desc()).limit(20).all()

    durations = [a.duration_seconds for a in recent_attempts if a.duration_seconds and a.duration_seconds > 0]
    if len(durations) >= 3:
        avg_dur = sum(durations) / len(durations)
        variance = sum((d - avg_dur) ** 2 for d in durations) / len(durations)
        std_dev = math.sqrt(variance)
        cv = std_dev / avg_dur if avg_dur > 0 else 0.0
        consistency = max(0.0, min(1.0, 1.0 - (cv * 0.5)))
    else:
        consistency = 1.0

    # 3. Uptime Ratio (0.0 to 1.0)
    uptime_ratio = getattr(worker, "uptime_ratio", 1.0) or 1.0
    if worker.status in ("offline", "failed"):
        uptime_ratio = max(0.2, uptime_ratio * 0.9)
    else:
        uptime_ratio = min(1.0, uptime_ratio * 1.02)

    # 4. Network Stability (0.0 to 1.0 based on latency)
    lat = getattr(worker, "network_latency_ms", 1.0) or 1.0
    if lat <= 5.0:
        net_stability = 1.0
    elif lat <= 20.0:
        net_stability = 0.9
    elif lat <= 50.0:
        net_stability = 0.75
    elif lat <= 100.0:
        net_stability = 0.5
    else:
        net_stability = 0.3

    # 5. Thermal / Resource Stability (0.0 to 1.0 based on temperature & throttling)
    temp = getattr(worker, "gpu_temperature", None)
    if temp is not None:
        if temp < 60.0:
            thermal_stability = 1.0
        elif temp < 75.0:
            thermal_stability = 0.85
        elif temp < 85.0:
            thermal_stability = 0.6
        else:
            thermal_stability = 0.3  # Thermal throttling zone
    else:
        # For CPU only, check CPU utilization variance
        cpu_util = getattr(worker, "cpu_utilization", 0.0) or 0.0
        thermal_stability = 1.0 if cpu_util < 85.0 else 0.7

    # 5-Factor Weighted Composite Formula
    composite_score = (
        (0.30 * success_rate) +
        (0.20 * consistency) +
        (0.20 * uptime_ratio) +
        (0.15 * net_stability) +
        (0.15 * thermal_stability)
    )
    composite_score = max(0.05, min(1.0, round(composite_score, 4)))

    # Persist metrics on worker model
    worker.reliability_score = composite_score
    worker.execution_consistency = round(consistency, 4)
    worker.network_stability = round(net_stability, 4)
    worker.thermal_stability = round(thermal_stability, 4)
    worker.uptime_ratio = round(uptime_ratio, 4)

    # Self-Healing Check: If composite reliability drops severely, mark degraded
    if composite_score < 0.60 and worker.lifecycle_state == "healthy":
        logger.warning(f"Worker {worker.worker_uid} reliability dropped to {composite_score}; transitioning to DEGRADED.")
        worker.lifecycle_state = "degraded"
    elif composite_score >= 0.70 and worker.lifecycle_state in ("degraded", "recovering"):
        worker.lifecycle_state = "healthy"

    return {
        "worker_uid": worker.worker_uid,
        "composite_score": composite_score,
        "success_rate": round(success_rate, 4),
        "execution_consistency": round(consistency, 4),
        "uptime_ratio": round(uptime_ratio, 4),
        "network_stability": round(net_stability, 4),
        "thermal_stability": round(thermal_stability, 4),
        "lifecycle_state": worker.lifecycle_state
    }
