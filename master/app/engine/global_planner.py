"""
Level 1: Global Resource Planner & Formal Execution Plan Engine — CoCompute 4.0.

Emits and dynamically adapts formal ExecutionPlan objects:
  - Selects optimal worker subsets
  - Generates initial per-worker chunk allocations and weights
  - Performs dynamic runtime adaptation (v1 -> v2 -> v3) when worker speeds diverge
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from master.app.db import models
from master.app.engine.reliability_engine import compute_worker_reliability

logger = logging.getLogger(__name__)


def generate_execution_plan(
    db: Session,
    job_uid: str,
    parallelism_analysis: Dict[str, Any],
    workload_profile: Dict[str, Any],
    energy_mode: str = "BALANCED",
    custom_workers_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Constructs the initial Level-1 Execution Plan before chunk dispatch.
    """
    plan_id = f"PLAN-{uuid.uuid4().hex[:8].upper()}"
    decision = parallelism_analysis.get("decision", "DISTRIBUTED")

    # Fetch available trusted workers
    available_workers = db.query(models.Worker).filter(
        models.Worker.status.in_(["online", "idle"]),
        models.Worker.trust_status.in_(["trusted", "auto_trusted"]),
        models.Worker.lifecycle_state.in_(["healthy", "degraded"])
    ).all()

    if not available_workers:
        # Fallback dummy single-worker allocation if testing offline
        available_workers = [models.Worker(id=1, worker_uid="local-worker", status="online")]

    # Sort workers by reliability & compute capacity
    scored_workers = []
    for w in available_workers:
        rel = compute_worker_reliability(w, db)
        rel_val = rel.get("composite_score", 1.0) if isinstance(rel, dict) else (float(rel) if rel else 1.0)
        cores = getattr(w, "cpu_cores", 4) or 4
        score = rel_val * cores
        scored_workers.append((w, score))
    scored_workers.sort(key=lambda x: x[1], reverse=True)

    if decision == "SINGLE_NODE" or len(scored_workers) == 1:
        selected_nodes = [scored_workers[0][0]]
    else:
        max_w = custom_workers_count or parallelism_analysis.get("recommended_workers", len(scored_workers))
        selected_nodes = [w for w, _ in scored_workers[:max_w]]

    # Compute per-worker elastic chunk targets
    total_score = sum(s for _, s in scored_workers[:len(selected_nodes)]) or 1.0
    total_chunks = workload_profile.get("recommended_chunks", max(len(selected_nodes) * 2, 4))
    
    worker_allocations: Dict[str, Dict[str, Any]] = {}
    for w, score in scored_workers[:len(selected_nodes)]:
        weight = round(score / total_score, 3)
        target_chunks = max(1, round(total_chunks * weight))
        worker_allocations[w.worker_uid] = {
            "worker_id": w.id,
            "target_chunks": target_chunks,
            "chunk_weight": weight,
            "assigned_so_far": 0,
            "completed_so_far": 0,
            "avg_chunk_duration_sec": None
        }

    return {
        "plan_id": plan_id,
        "version": 1,
        "decision": decision,
        "scheduler": "adaptive_hybrid",
        "selected_workers": [w.worker_uid for w in selected_nodes],
        "chunk_count": total_chunks,
        "estimated_duration_sec": parallelism_analysis.get("estimated_duration_sec", 15.0),
        "estimated_speedup": parallelism_analysis.get("estimated_speedup", 1.0),
        "energy_mode": energy_mode,
        "worker_allocations": worker_allocations,
        "adaptation_history": []
    }


def adapt_execution_plan(
    current_plan: Dict[str, Any],
    completed_chunks_count: int,
    total_chunks_count: int,
    measured_worker_durations: Dict[str, List[float]]
) -> Optional[Dict[str, Any]]:
    """
    Evaluates runtime progress and adapts worker allocations if speeds diverge significantly.
    """
    if not current_plan or total_chunks_count <= 0:
        return None

    progress_pct = round((completed_chunks_count / total_chunks_count) * 100, 1)
    if progress_pct < 25 or progress_pct > 85:
        return None  # Only adapt during active middle phase

    allocations = current_plan.get("worker_allocations", {})
    if len(allocations) <= 1:
        return None

    # Calculate average duration per worker
    avg_durations: Dict[str, float] = {}
    for uid, durations in measured_worker_durations.items():
        if durations:
            avg_durations[uid] = sum(durations) / len(durations)

    if len(avg_durations) < 2:
        return None

    min_dur = min(avg_durations.values())
    max_dur = max(avg_durations.values())

    # If speed divergence > 2.0x, adjust chunk weights
    if max_dur > (min_dur * 2.0):
        new_version = current_plan.get("version", 1) + 1
        adaptation_entry = {
            "adapted_at_version": new_version,
            "progress_pct": progress_pct,
            "reason": f"Divergence detected: fast worker ({min_dur:.2f}s) vs slow worker ({max_dur:.2f}s). Increased allocation for fast nodes."
        }

        # Increase allocation for fast workers, throttle slow workers
        for uid, avg_d in avg_durations.items():
            if uid in allocations:
                allocations[uid]["avg_chunk_duration_sec"] = round(avg_d, 3)
                if avg_d <= (min_dur * 1.3):
                    allocations[uid]["chunk_weight"] = round(allocations[uid]["chunk_weight"] * 1.3, 3)
                elif avg_d >= (min_dur * 2.0):
                    allocations[uid]["chunk_weight"] = round(allocations[uid]["chunk_weight"] * 0.6, 3)

        current_plan["version"] = new_version
        current_plan["adaptation_history"].append(adaptation_entry)
        logger.info(f"Execution plan adapted to version {new_version} at {progress_pct}% completion.")
        return current_plan

    return None
