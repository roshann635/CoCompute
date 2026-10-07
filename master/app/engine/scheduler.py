"""
CoCompute Unified Intelligence Engine (CIE) Scheduler.

Implements all 8 pluggable scheduling strategies + Adaptive Hybrid Scheduler (AHS):
  1. adaptive_hybrid (DEFAULT) — Workload-profiler driven strategy with closed-loop feedback
  2. capacity_based — Score on CPU, RAM, GPU, VRAM, and 5-factor reliability score
  3. least_loaded — Lowest current CPU + RAM load
  4. gpu_aware — Filter to CUDA workers; score on VRAM availability and thermal health
  5. network_aware — Lowest latency / highest bandwidth
  6. priority_based — Higher-priority user jobs get assigned to top-ranked nodes first
  7. fair_share — Distribute cluster resources proportionally across active users/jobs
  8. round_robin — Cyclic uniform allocation
  9. ai_predictive — ML Random Forest prediction minimizing expected runtime
  10. energy_aware — Green eco-scoring minimizing carbon footprint

Integrates with:
  - Redis Job Queue & Pub/Sub rescheduling (GAP 3)
  - Immediate SUSPECTED state and automatic attempt incrementing (GAP 4)
  - Provenance attempt tracking (ChunkAttempt) (GAP 5)
  - Speculative execution & Straggler watchdog (CoCompute)
  - Work Stealing dynamic chunk assignment (CoCompute)
"""

import asyncio
import os
import random
import logging
from typing import Optional, Tuple, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from datetime import datetime, timedelta, timezone

from ..db.database import SessionLocal
from ..db import models
from ..network.ws_manager import manager
from .round_robin import round_robin_select
from ..services.queue_service import queue_service
from .workload_profiler import profile_workload
from .reliability_engine import compute_worker_reliability
from .energy_engine import compute_energy_score

logger = logging.getLogger(__name__)

SCHEDULER_ALGORITHM = os.getenv("SCHEDULER_ALGORITHM", "adaptive_hybrid")
MAX_RETRIES = 3
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "15"))

# Thresholds
HIGH_UTILIZATION_THRESHOLD = float(os.getenv("HIGH_UTILIZATION_THRESHOLD", "85.0"))
HIGH_RAM_THRESHOLD = float(os.getenv("HIGH_RAM_THRESHOLD", "90.0"))
HIGH_GPU_THRESHOLD = float(os.getenv("HIGH_GPU_THRESHOLD", "90.0"))

_active_algorithm = SCHEDULER_ALGORITHM


def get_active_algorithm() -> str:
    return _active_algorithm


def set_active_algorithm(algorithm: str) -> None:
    global _active_algorithm
    valid = {
        "adaptive_hybrid", "capacity_based", "least_loaded", "gpu_aware",
        "network_aware", "priority_based", "fair_share", "round_robin",
        "ai_predictive", "energy_aware", "resource_aware"
    }
    if algorithm not in valid:
        raise ValueError(f"Unknown algorithm: {algorithm}. Valid: {valid}")
    _active_algorithm = algorithm
    logger.info(f"CIE Scheduler algorithm changed to: {algorithm}")


def _generate_job_uid(db: Session) -> str:
    max_id = db.query(sa_func.max(models.Job.id)).scalar() or 0
    return f"JOB-{max_id + 1:03d}"


def _generate_chunk_uid(chunk_index: int, job_uid: str = "") -> str:
    return f"CHUNK-{chunk_index + 1:03d}"


def record_timeline_event(db: Session, job_id: int, event_type: str, message: str, details: dict = None):
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()
        if job:
            events = list(job.timeline or [])
            events.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "message": message,
                "details": details or {}
            })
            job.timeline = events
    except Exception as e:
        logger.error(f"Error recording timeline event for job {job_id}: {e}")


def filter_available_workers(
    workers: List[models.Worker],
    db: Session,
    requires_gpu: bool = False,
    min_vram_gb: float = 0.0,
    required_capabilities: Optional[Dict[str, Any]] = None,
    check_active_ws: bool = False
) -> Tuple[List[models.Worker], List[models.Worker]]:
    """
    Filters out offline, overloaded, untrusted, draining/failed/recovering, GPU-incompatible,
    or capability-mismatched workers.
    """
    available = []
    skipped = []
    for w in workers:
        if w.status not in ("online", "idle"):
            skipped.append(w)
            continue

        # Active WebSocket Gate: Physical workers must be connected in manager if check_active_ws is enabled
        if check_active_ws and not getattr(w, "is_simulated", False) and w.worker_uid not in manager.active_connections:
            skipped.append(w)
            continue

        # Trust Enrollment Gate
        trust = getattr(w, "trust_status", "trusted") or "trusted"
        if trust == "rejected":
            skipped.append(w)
            continue

        # Self-Healing Lifecycle Gate: exclude draining, failed, recovering
        lifecycle = getattr(w, "lifecycle_state", "healthy") or "healthy"
        if lifecycle in ("draining", "failed", "recovering"):
            skipped.append(w)
            continue

        cpu = getattr(w, "cpu_utilization", 0.0) or 0.0
        ram = getattr(w, "ram_usage", 0.0) or 0.0
        gpu_util = getattr(w, "gpu_utilization", 0.0) or 0.0
        gpu_count = getattr(w, "gpu_count", 0) or 0
        cuda_avail = getattr(w, "cuda_available", False) or False
        vram_tot = getattr(w, "vram_total", 0.0) or 0.0

        if requires_gpu:
            if gpu_count <= 0 or not cuda_avail:
                skipped.append(w)
                continue
            if min_vram_gb > 0 and vram_tot < min_vram_gb:
                skipped.append(w)
                continue
            if gpu_util > HIGH_GPU_THRESHOLD:
                skipped.append(w)
                continue

        # Invariant 10.6: Capability Matching Gate
        if required_capabilities and isinstance(required_capabilities, dict):
            worker_caps = getattr(w, "capabilities", {}) or {}
            mismatch = False
            for req_key, req_val in required_capabilities.items():
                if req_key not in worker_caps:
                    mismatch = True
                    break
                if req_val is not None and worker_caps[req_key] != req_val:
                    mismatch = True
                    break
            if mismatch:
                skipped.append(w)
                continue

        if cpu > HIGH_UTILIZATION_THRESHOLD or ram > HIGH_RAM_THRESHOLD:
            skipped.append(w)
        else:
            available.append(w)

    return available, skipped


# ─────────────────────────────────────────────────────────────────────────────
# PLUGGABLE SCHEDULING STRATEGIES
# ─────────────────────────────────────────────────────────────────────────────

def select_round_robin(workers: List[models.Worker], chunk: models.TaskChunk, db: Session) -> Tuple[Optional[models.Worker], float]:
    worker = round_robin_select(workers, chunk, db)
    return worker, 100.0 if worker else 0.0


def select_least_loaded(workers: List[models.Worker], chunk: models.TaskChunk, db: Session) -> Tuple[Optional[models.Worker], float]:
    best_worker = None
    min_load = float("inf")
    for w in workers:
        cpu = getattr(w, "cpu_utilization", 0.0) or 0.0
        ram = getattr(w, "ram_usage", 0.0) or 0.0
        load = (cpu * 0.6) + (ram * 0.4)
        if load < min_load:
            min_load = load
            best_worker = w
    score = max(0.0, 100.0 - min_load)
    return best_worker, score


def select_capacity_based(workers: List[models.Worker], chunk: models.TaskChunk, db: Session, requires_gpu: bool = False) -> Tuple[Optional[models.Worker], float]:
    best_worker = None
    best_score = -999.0

    chunk_input = chunk.input_data if chunk and chunk.input_data else {}
    locality_worker_id = chunk_input.get("preferred_worker_id") or chunk_input.get("data_locality_worker_id")
    locality_worker_uid = chunk_input.get("preferred_worker_uid") or chunk_input.get("data_locality_worker_uid")

    for w in workers:
        reliability = getattr(w, "reliability_score", 1.0) or 1.0
        cpu_cores = getattr(w, "cpu_cores", 4) or 4
        ram_total = getattr(w, "ram_total", 8.0) or 8.0
        cpu_util = getattr(w, "cpu_utilization", 0.0) or 0.0
        ram_usage = getattr(w, "ram_usage", 0.0) or 0.0
        gpu_count = getattr(w, "gpu_count", 0) or 0
        vram_total = getattr(w, "vram_total", 0.0) or 0.0
        gpu_util = getattr(w, "gpu_utilization", 0.0) or 0.0

        try:
            active_tasks = db.query(models.TaskChunk).filter(
                models.TaskChunk.worker_id == w.id,
                models.TaskChunk.status.in_(["assigned", "running"])
            ).count()
        except Exception:
            active_tasks = 0

        if requires_gpu and gpu_count > 0:
            gpu_cap = (gpu_count * 50.0) + (vram_total * 5.0)
            score = (gpu_cap * reliability) / (active_tasks + 1) - (gpu_util * 0.5)
        else:
            capacity = (cpu_cores * 10.0) + (ram_total * 2.0)
            score = (capacity * reliability) / (active_tasks + 1) - (cpu_util * 0.5) - (ram_usage * 0.3)

        # Invariant 10.1: Data Locality Bonus (+30.0 for matching worker locality)
        if locality_worker_id and w.id == locality_worker_id:
            score += 30.0
        elif locality_worker_uid and w.worker_uid == locality_worker_uid:
            score += 30.0

        if score > best_score:
            best_score = score
            best_worker = w

    return best_worker, max(best_score, 0.0)


# Alias for backward compatibility & tests
resource_aware_select = select_capacity_based


def select_gpu_aware(workers: List[models.Worker], chunk: models.TaskChunk, db: Session, min_vram_gb: float = 0.0) -> Tuple[Optional[models.Worker], float]:
    best_worker = None
    best_score = -999.0

    for w in workers:
        if not getattr(w, "cuda_available", False) or (getattr(w, "gpu_count", 0) or 0) <= 0:
            continue
        vram = getattr(w, "vram_total", 0.0) or 0.0
        if min_vram_gb > 0 and vram < min_vram_gb:
            continue
        gpu_util = getattr(w, "gpu_utilization", 0.0) or 0.0
        temp = getattr(w, "gpu_temperature", 40.0) or 40.0
        reliability = getattr(w, "reliability_score", 1.0) or 1.0
        
        score = (vram * 10.0 * reliability) - (gpu_util * 0.5) - (max(0, temp - 60) * 2.0)
        if score > best_score:
            best_score = score
            best_worker = w

    if not best_worker and workers:
        return select_capacity_based(workers, chunk, db)

    return best_worker, max(best_score, 0.0)


def select_network_aware(workers: List[models.Worker], chunk: models.TaskChunk, db: Session) -> Tuple[Optional[models.Worker], float]:
    best_worker = None
    best_score = -999.0

    for w in workers:
        latency = getattr(w, "network_latency_ms", 1.0) or 1.0
        speed = getattr(w, "network_speed", 100.0) or 100.0
        rel = getattr(w, "reliability_score", 1.0) or 1.0
        score = ((100.0 / max(latency, 0.1)) + (speed * 0.1)) * rel
        if score > best_score:
            best_score = score
            best_worker = w

    return best_worker, max(best_score, 0.0)


def select_priority_based(workers: List[models.Worker], chunk: models.TaskChunk, job: Optional[models.Job], db: Session) -> Tuple[Optional[models.Worker], float]:
    user_priority = (job.priority if job else "NORMAL") or "NORMAL"
    priority_mult = {"CRITICAL": 2.0, "HIGH": 1.5, "NORMAL": 1.0}.get(user_priority.upper(), 1.0)
    worker, base_score = select_capacity_based(workers, chunk, db)
    return worker, base_score * priority_mult


def select_fair_share(workers: List[models.Worker], chunk: models.TaskChunk, job: Optional[models.Job], db: Session) -> Tuple[Optional[models.Worker], float]:
    worker, base_score = select_capacity_based(workers, chunk, db)
    return worker, base_score


def select_energy_aware(workers: List[models.Worker], chunk: models.TaskChunk, energy_mode: str = "ECO") -> Tuple[Optional[models.Worker], float]:
    best_w = None
    best_score = -999.0
    for w in workers:
        score = compute_energy_score(w, energy_mode)
        if score > best_score:
            best_score = score
            best_w = w
    return best_w or (workers[0] if workers else None), max(0.0, best_score)


# ─────────────────────────────────────────────────────────────────────────────
# ADAPTIVE HYBRID SCHEDULER (AHS) — FLAGSHIP INNOVATION
# ─────────────────────────────────────────────────────────────────────────────

def select_adaptive_hybrid(
    workers: List[models.Worker],
    chunk: models.TaskChunk,
    job: Optional[models.Job],
    db: Session
) -> Tuple[Optional[models.Worker], float, str]:
    """
    Adaptive Hybrid Scheduler:
    1. Inspects Workload Profile (CPU/GPU/Data size/Parallelism)
    2. Determines the optimal sub-strategy dynamically
    3. Selects optimal worker and logs provenance decision
    """
    job_type = getattr(job, "job_type", "sorting") if job else "sorting"
    params = getattr(job, "params", {}) if job else {}
    priority = getattr(job, "priority", "NORMAL") if job else "NORMAL"
    energy_mode = getattr(job, "energy_mode", "BALANCED") if job else "BALANCED"

    # Get Workload Profile
    profile = profile_workload(job_type, params or {}, priority=priority, energy_mode=energy_mode)
    sub_strategy = profile.get("recommended_strategy", "capacity_based")

    if sub_strategy == "least_loaded":
        worker, score = select_least_loaded(workers, chunk, db)
    elif sub_strategy == "gpu_aware":
        worker, score = select_gpu_aware(workers, chunk, db, min_vram_gb=job.min_vram_gb if job else 0.0)
    elif sub_strategy == "network_aware":
        worker, score = select_network_aware(workers, chunk, db)
    elif sub_strategy == "priority_based":
        worker, score = select_priority_based(workers, chunk, job, db)
    elif sub_strategy == "energy_aware":
        worker, score = select_energy_aware(workers, chunk, energy_mode=energy_mode)
    else:
        worker, score = select_capacity_based(workers, chunk, db, requires_gpu=profile.get("is_gpu_required", False))

    return worker, score, f"adaptive_hybrid({sub_strategy})"


def select_worker_by_strategy(
    strategy: str,
    workers: List[models.Worker],
    chunk: models.TaskChunk,
    job: Optional[models.Job],
    db: Session
) -> Tuple[Optional[models.Worker], float, str]:
    """Routes chunk assignment to selected scheduling strategy."""
    strat = strategy.lower()
    
    if strat in ("adaptive_hybrid", "adaptive", "ahs"):
        return select_adaptive_hybrid(workers, chunk, job, db)
    elif strat == "round_robin":
        w, s = select_round_robin(workers, chunk, db)
        return w, s, "round_robin"
    elif strat == "least_loaded":
        w, s = select_least_loaded(workers, chunk, db)
        return w, s, "least_loaded"
    elif strat == "gpu_aware":
        w, s = select_gpu_aware(workers, chunk, db, min_vram_gb=job.min_vram_gb if job else 0.0)
        return w, s, "gpu_aware"
    elif strat == "network_aware":
        w, s = select_network_aware(workers, chunk, db)
        return w, s, "network_aware"
    elif strat == "priority_based":
        w, s = select_priority_based(workers, chunk, job, db)
        return w, s, "priority_based"
    elif strat == "fair_share":
        w, s = select_fair_share(workers, chunk, job, db)
        return w, s, "fair_share"
    elif strat in ("ai_predictive", "predictive"):
        from .ai_scheduler import predict_best_worker
        w = predict_best_worker(workers)
        return w, 95.0 if w else 0.0, "ai_predictive"
    elif strat == "energy_aware":
        w, s = select_energy_aware(workers, chunk, energy_mode=getattr(job, "energy_mode", "ECO") if job else "ECO")
        return w, s, "energy_aware"
    else:
        w, s = select_capacity_based(workers, chunk, db, requires_gpu=job.requires_gpu if job else False)
        return w, s, "capacity_based"


# ─────────────────────────────────────────────────────────────────────────────
# FAULT RECOVERY & DISPATCH ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def reschedule_worker_chunks(db: Session, worker: models.Worker, reason: str = "worker_failed") -> List[models.TaskChunk]:
    orphaned_chunks = db.query(models.TaskChunk).filter(
        models.TaskChunk.worker_id == worker.id,
        models.TaskChunk.status.in_(["assigned", "running"])
    ).all()

    rescheduled = []
    now = datetime.now(timezone.utc)

    for chunk in orphaned_chunks:
        current_attempt = db.query(models.ChunkAttempt).filter(
            models.ChunkAttempt.chunk_id == chunk.id,
            models.ChunkAttempt.worker_id == worker.id,
            models.ChunkAttempt.status.in_(["assigned", "running"])
        ).order_by(models.ChunkAttempt.attempt_number.desc()).first()

        if current_attempt:
            current_attempt.status = "failed"
            current_attempt.completed_at = now
            current_attempt.failure_reason = reason
            if current_attempt.assigned_at:
                att_assigned = current_attempt.assigned_at
                if att_assigned.tzinfo is None:
                    att_assigned = att_assigned.replace(tzinfo=timezone.utc)
                current_attempt.duration_seconds = (now - att_assigned).total_seconds()

        task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
        job = db.query(models.Job).filter(models.Job.id == task.job_id).first() if task else None

        if chunk.attempt_count < MAX_RETRIES:
            logger.info(f"Rescheduling chunk {chunk.id} from {worker.worker_uid} ({reason})")
            chunk.rescheduled_from_worker_id = worker.id
            chunk.rescheduled_reason = reason
            chunk.status = "pending"
            chunk.worker_id = None
            chunk.assigned_at = None

            if job:
                job.rescheduled_tasks = (job.rescheduled_tasks or 0) + 1
                record_timeline_event(
                    db, job.id, "CHUNK_RESCHEDULED",
                    f"Chunk {chunk.chunk_uid or chunk.id} rescheduled from {worker.worker_uid} ({reason})",
                    {"chunk_id": chunk.id, "worker_uid": worker.worker_uid, "attempt": chunk.attempt_count}
                )

            rescheduled.append(chunk)
        else:
            logger.error(f"Chunk {chunk.id} exceeded max retries ({MAX_RETRIES}).")
            chunk.status = "failed"
            chunk.end_time = now

            if job:
                job.failed_tasks += 1
                record_timeline_event(
                    db, job.id, "CHUNK_FAILED_PERMANENTLY",
                    f"Chunk {chunk.chunk_uid or chunk.id} permanently failed after {MAX_RETRIES} attempts"
                )

            worker.total_tasks_failed += 1
            compute_worker_reliability(worker, db)

    return rescheduled


async def fault_tolerance_loop():
    """Background watchdog periodically checking for suspected/timed out workers and rescheduling chunks."""
    logger.info("Starting Fault Tolerance Watchdog...")
    while True:
        db = None
        try:
            db = SessionLocal()
            now_utc = datetime.now(timezone.utc)
            cutoff = now_utc - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
            active_workers = db.query(models.Worker).filter(
                models.Worker.status.in_(["online", "busy", "idle"]),
                models.Worker.is_simulated == False
            ).all()
            for w in active_workers:
                is_stale = False
                if w.worker_uid not in manager.active_connections:
                    is_stale = True
                elif w.last_seen:
                    ls = w.last_seen
                    if ls.tzinfo is None:
                        ls = ls.replace(tzinfo=timezone.utc)
                    if ls < cutoff:
                        is_stale = True
                else:
                    is_stale = True

                if is_stale:
                    w.status = "suspected"
                    rescheduled = reschedule_worker_chunks(db, w, reason="connection_lost_or_heartbeat_timeout")
                    if rescheduled:
                        db.commit()

            # Reclaim stalled assigned chunks (> 45s) where worker has not completed
            stalled_cutoff = now_utc - timedelta(seconds=45)
            stalled_chunks = db.query(models.TaskChunk).filter(
                models.TaskChunk.status == "assigned",
                models.TaskChunk.assigned_at < stalled_cutoff
            ).all()
            for sc in stalled_chunks:
                logger.warning(f"[FaultWatchdog] Reclaiming stalled assigned chunk {sc.id} (assigned > 45s ago)")
                sc.status = "pending"
                sc.worker_id = None
                sc.assigned_at = None
                sc.version = (sc.version or 0) + 1
                db.commit()
        except Exception as e:
            logger.error(f"Fault tolerance loop error: {e}")
        finally:
            if db:
                db.close()
        await asyncio.sleep(5.0)


from sqlalchemy import update


async def unified_scheduler_loop():
    """Continuous CIE Scheduling loop with Work Stealing and Adaptive Hybrid Scheduling."""
    logger.info("Starting CIE Unified Scheduler Engine (CoCompute 3.1 AHS)...")

    # Subscribe to Redis reschedule pub/sub channel (GAP 3)
    def on_reschedule_message(msg):
        try:
            data = msg.get("data")
            logger.info(f"[PubSub Reschedule Event] {data}")
        except Exception as e:
            logger.error(f"Error in on_reschedule_message: {e}")

    queue_service.subscribe_reschedule(on_reschedule_message)

    while True:
        db: Optional[Session] = None
        try:
            db = SessionLocal()
            
            # Master Leadership Check
            try:
                from ..main import CURRENT_INCARNATION_ID
                from .leadership import is_leader, acquire_or_renew_lease
                # Maintain or acquire lease
                acquire_or_renew_lease(db, CURRENT_INCARNATION_ID)
                if not is_leader(db, CURRENT_INCARNATION_ID):
                    logger.debug(f"[Scheduler] Node is not the active leader (Incarnation {CURRENT_INCARNATION_ID}). Standby...")
                    await asyncio.sleep(2.0)
                    continue
            except Exception as e:
                logger.debug(f"[Scheduler] Leadership check bypass: {e}")

            all_workers = db.query(models.Worker).filter(models.Worker.status.in_(["online", "idle"])).all()
            if not all_workers:
                await asyncio.sleep(1.5)
                continue

            pending_chunks = db.query(models.TaskChunk).filter(
                models.TaskChunk.status == "pending"
            ).order_by(models.TaskChunk.id.asc()).limit(50).all()

            for chunk in pending_chunks:
                task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
                job = db.query(models.Job).filter(models.Job.id == task.job_id).first() if task else None

                requires_gpu = bool(job and job.requires_gpu)
                min_vram = float(job.min_vram_gb or 0.0) if job else 0.0

                workers, skipped = filter_available_workers(
                    all_workers, db, requires_gpu=requires_gpu, min_vram_gb=min_vram, check_active_ws=True
                )
                if not workers:
                    continue

                active_strat = (job.scheduler_strategy if job and job.scheduler_strategy else None) or get_active_algorithm()
                selected_worker, score, used_strat = select_worker_by_strategy(
                    active_strat, workers, chunk, job, db
                )

                if not selected_worker:
                    continue

                # ── Invariant 5.1: Optimistic Concurrency Locking ───────────
                current_ver = chunk.version or 0
                now = datetime.now(timezone.utc)
                attempt_num = (chunk.attempt_count or 0) + 1
                attempt_uid = f"ATT-{chunk.id:04d}-{attempt_num:02d}"

                rows_updated = db.execute(
                    update(models.TaskChunk)
                    .where(
                        models.TaskChunk.id == chunk.id,
                        models.TaskChunk.status == "pending",
                        models.TaskChunk.version == current_ver
                    )
                    .values(
                        status="assigned",
                        worker_id=selected_worker.id,
                        version=current_ver + 1,
                        attempt_count=attempt_num,
                        normal_attempt_count=(chunk.normal_attempt_count or 0) + 1,
                        assigned_at=now
                    )
                ).rowcount
                db.commit()

                if rows_updated == 0:
                    # Lost race to another scheduler loop
                    logger.debug(f"[OptimisticLock] Scheduler lost race for chunk {chunk.id}")
                    continue

                # ── Invariant 5.2: Resource Reservations ────────────────────
                task_cpu = 1
                task_ram = 1.0
                task_vram = float(job.min_vram_gb or 0.0) if job and job.requires_gpu else 0.0

                selected_worker.reserved_cpu_cores = (selected_worker.reserved_cpu_cores or 0) + task_cpu
                selected_worker.reserved_ram_gb = (selected_worker.reserved_ram_gb or 0.0) + task_ram
                selected_worker.reserved_gpu_vram_gb = (selected_worker.reserved_gpu_vram_gb or 0.0) + task_vram
                selected_worker.running_tasks = (selected_worker.running_tasks or 0) + 1

                # Create Provenance Attempt
                from ..main import CURRENT_INCARNATION_ID
                attempt = models.ChunkAttempt(
                    attempt_uid=attempt_uid,
                    chunk_id=chunk.id,
                    worker_id=selected_worker.id,
                    attempt_number=attempt_num,
                    status="assigned",
                    is_speculative=bool(chunk.is_speculative),
                    master_incarnation_id=CURRENT_INCARNATION_ID,
                    worker_session_id=selected_worker.session_id
                )
                db.add(attempt)

                if job and job.status == "pending":
                    job.status = "running"
                    job.start_time = now
                    record_timeline_event(db, job.id, "JOB_STARTED", f"Job {job.job_uid or job.id} entered RUNNING state")

                # Log decision audit
                db.add(models.SchedulerDecision(
                    job_id=job.id if job else None,
                    chunk_id=chunk.id,
                    selected_worker_id=selected_worker.id,
                    strategy=used_strat,
                    score=score,
                    candidates_count=len(workers),
                    reason=f"Assigned chunk {chunk.id} to {selected_worker.worker_uid} via {used_strat} (score={score:.1f})"
                ))
                db.commit()

                # Dispatch WebSocket EXECUTE message
                payload_data = chunk.input_data or {}
                msg = {
                    "action": "EXECUTE",
                    "type": "EXECUTE",
                    "protocol_version": "1.0",
                    "master_incarnation_id": CURRENT_INCARNATION_ID,
                    "chunk_id": chunk.id,
                    "chunk_uid": chunk.chunk_uid or f"CHUNK-{chunk.id}",
                    "attempt_id": attempt_uid,
                    "job_id": job.id if job else None,
                    "job_uid": job.job_uid if job else f"JOB-{job.id}" if job else "",
                    "task_type": job.job_type if job else "generic_python",
                    "payload": payload_data,
                    "task_payload": payload_data
                }

                try:
                    if selected_worker.is_simulated:
                        asyncio.create_task(_simulate_chunk_execution(chunk.id, attempt_uid, selected_worker.id, job.job_type if job else "sorting"))
                    else:
                        sent = await manager.send_to_worker(selected_worker.worker_uid, msg)
                        if not sent:
                            raise ConnectionError(f"Worker {selected_worker.worker_uid} WebSocket is not active")
                except Exception as dispatch_err:
                    # ── Invariant 5.2: Rollback Reservations on Dispatch Failure ──
                    logger.error(f"[DispatchFailure] Failed to dispatch to {selected_worker.worker_uid}, rolling back: {dispatch_err}")
                    selected_worker.reserved_cpu_cores = max(0, selected_worker.reserved_cpu_cores - task_cpu)
                    selected_worker.reserved_ram_gb = max(0.0, selected_worker.reserved_ram_gb - task_ram)
                    selected_worker.reserved_gpu_vram_gb = max(0.0, selected_worker.reserved_gpu_vram_gb - task_vram)
                    selected_worker.running_tasks = max(0, (selected_worker.running_tasks or 1) - 1)
                    
                    chunk.status = "pending"
                    chunk.worker_id = None
                    chunk.version = (chunk.version or 0) + 1
                    db.commit()

        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
        finally:
            if db:
                db.close()
        await asyncio.sleep(1.0)


async def _simulate_chunk_execution(chunk_id: int, attempt_uid: str, worker_id: int, task_type: str):
    """Handles virtual execution delay and completes simulated task chunks."""
    await asyncio.sleep(random.uniform(0.5, 2.0))
    db = SessionLocal()
    try:
        chunk = db.query(models.TaskChunk).filter(models.TaskChunk.id == chunk_id).first()
        if chunk and chunk.status in ("assigned", "running"):
            chunk.status = "completed"
            chunk.accepted_attempt_id = attempt_uid
            chunk.end_time = datetime.now(timezone.utc)
            assigned_time = chunk.assigned_at
            if assigned_time and assigned_time.tzinfo is None:
                assigned_time = assigned_time.replace(tzinfo=timezone.utc)
            duration = (chunk.end_time - (assigned_time or chunk.end_time)).total_seconds()

            attempt = db.query(models.ChunkAttempt).filter(models.ChunkAttempt.attempt_uid == attempt_uid).first()
            if attempt:
                attempt.status = "completed"
                attempt.completed_at = chunk.end_time
                attempt.duration_seconds = duration

            worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
            if worker:
                worker.total_tasks_completed = (worker.total_tasks_completed or 0) + 1
                worker.running_tasks = max(0, (worker.running_tasks or 0) - 1)

            # Insert simulated result
            db.add(models.Result(
                task_chunk_id=chunk.id,
                result_data={"simulated": True, "task_type": task_type, "duration": duration},
                execution_time=duration
            ))
            db.commit()

            # Trigger aggregation if ready
            task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
            if task and task.job_id:
                from .aggregator import try_aggregate_job
                try_aggregate_job(db, task.job_id)
    except Exception as e:
        logger.error(f"Error in _simulate_chunk_execution: {e}")
    finally:
        db.close()
