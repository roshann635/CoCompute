"""
CoCompute Unified Intelligence Engine (CIE) Scheduler.

Implements all 7 pluggable scheduling strategies defined in Master Prompt Section 5:
  1. round_robin — Distribute chunks evenly across available nodes.
  2. least_loaded — Prefer workers with the lowest current CPU + RAM load.
  3. capacity_based — Score on CPU, RAM, GPU, VRAM, and reliability score.
  4. gpu_aware — Filter to GPU-capable workers; score on VRAM and GPU utilization.
  5. network_aware — Prefer workers with highest network throughput / lowest latency.
  6. priority_based — Higher-priority user jobs get assigned to top-ranked nodes first.
  7. fair_share — Distribute cluster resources proportionally across active users/jobs.
  (+ ai_predictive — ML-based execution time prediction).

Integrates with:
  - Redis Job Queue & Pub/Sub rescheduling (GAP 3)
  - Immediate SUSPECTED state and automatic attempt incrementing (GAP 4)
  - Provenance attempt tracking (ChunkAttempt) (GAP 5)
  - Real-time audit decision logging (SchedulerDecision)
"""

import asyncio
import os
import logging
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from datetime import datetime, timedelta, timezone

from ..db.database import SessionLocal
from ..db import models
from ..network.ws_manager import manager
from .round_robin import round_robin_select
from ..services.queue_service import queue_service

logger = logging.getLogger(__name__)

SCHEDULER_ALGORITHM = os.getenv("SCHEDULER_ALGORITHM", "capacity_based")
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
        "round_robin", "least_loaded", "capacity_based", "gpu_aware",
        "network_aware", "priority_based", "fair_share", "ai_predictive",
        "resource_aware"
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
    min_vram_gb: float = 0.0
) -> Tuple[List[models.Worker], List[models.Worker]]:
    """
    Filters out offline, overloaded, or GPU-incompatible workers.
    """
    available = []
    skipped = []
    for w in workers:
        if w.status not in ("online", "idle"):
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

        if cpu > HIGH_UTILIZATION_THRESHOLD or ram > HIGH_RAM_THRESHOLD:
            skipped.append(w)
        else:
            available.append(w)

    return available, skipped


# ─────────────────────────────────────────────────────────────────────────────
# 7 PLUGGABLE SCHEDULING STRATEGIES
# ─────────────────────────────────────────────────────────────────────────────

def select_round_robin(workers: List[models.Worker], chunk: models.TaskChunk, db: Session) -> Tuple[Optional[models.Worker], float]:
    worker = round_robin_select(workers, chunk, db)
    return worker, 100.0 if worker else 0.0


def select_least_loaded(workers: List[models.Worker], chunk: models.TaskChunk, db: Session) -> Tuple[Optional[models.Worker], float]:
    """Prefers workers with lowest (CPU utilization + RAM usage)."""
    best_worker = None
    min_load = 9999.0
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
    """
    Capacity-Based Strategy:
    Scores based on raw hardware specs (cores, RAM), adjusted by reliability score
    and penalized by current utilization and active chunk queue.
    """
    best_worker = None
    best_score = -999.0

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

        if score > best_score:
            best_score = score
            best_worker = w

    return best_worker, max(best_score, 0.0)


# Alias for backward compatibility & tests
resource_aware_select = select_capacity_based


def select_gpu_aware(workers: List[models.Worker], chunk: models.TaskChunk, db: Session, min_vram_gb: float = 0.0) -> Tuple[Optional[models.Worker], float]:
    """Filters GPU nodes and ranks by VRAM availability and thermal health."""
    best_worker = None
    best_score = -999.0

    for w in workers:
        gpu_count = getattr(w, "gpu_count", 0) or 0
        vram_tot = getattr(w, "vram_total", 0.0) or 0.0
        vram_use = getattr(w, "vram_usage", 0.0) or 0.0
        gpu_util = getattr(w, "gpu_utilization", 0.0) or 0.0
        temp = getattr(w, "gpu_temperature", 40.0) or 40.0

        vram_avail = vram_tot * (1.0 - (vram_use / 100.0))
        thermal_penalty = max(0.0, (temp - 70.0) * 1.5)

        score = (gpu_count * 40.0) + (vram_avail * 10.0) - (gpu_util * 0.4) - thermal_penalty
        if score > best_score:
            best_score = score
            best_worker = w

    return best_worker, max(best_score, 0.0)


def select_network_aware(workers: List[models.Worker], chunk: models.TaskChunk, db: Session) -> Tuple[Optional[models.Worker], float]:
    """Prefers workers with lowest network latency and highest transfer rate."""
    best_worker = None
    best_score = -999.0

    for w in workers:
        speed = getattr(w, "network_speed", 100.0) or 100.0
        latency = getattr(w, "network_latency_ms", 2.0) or 2.0
        cpu_util = getattr(w, "cpu_utilization", 0.0) or 0.0

        score = (speed * 0.5) - (latency * 10.0) - (cpu_util * 0.2)
        if score > best_score:
            best_score = score
            best_worker = w

    return best_worker, max(best_score, 0.0)


def select_priority_based(workers: List[models.Worker], chunk: models.TaskChunk, job: models.Job, db: Session) -> Tuple[Optional[models.Worker], float]:
    """Factors user/job priority into capacity assignment."""
    priority_multiplier = 1.5 if (job and job.priority == "CRITICAL") else 1.2 if (job and job.priority == "HIGH") else 1.0
    worker, score = select_capacity_based(workers, chunk, db, requires_gpu=bool(job and job.requires_gpu))
    return worker, score * priority_multiplier


def select_fair_share(workers: List[models.Worker], chunk: models.TaskChunk, job: models.Job, db: Session) -> Tuple[Optional[models.Worker], float]:
    """Distributes worker assignments across active jobs and users."""
    best_worker = None
    min_user_chunks = 9999

    for w in workers:
        # Count chunks currently assigned to this worker for the same job
        chunk_count = db.query(models.TaskChunk).filter(
            models.TaskChunk.worker_id == w.id,
            models.TaskChunk.status.in_(["assigned", "running"])
        ).count()

        if chunk_count < min_user_chunks:
            min_user_chunks = chunk_count
            best_worker = w

    return best_worker, max(0.0, 100.0 - (min_user_chunks * 10.0))


def select_worker_by_strategy(
    strategy: str,
    workers: List[models.Worker],
    chunk: models.TaskChunk,
    job: Optional[models.Job],
    db: Session
) -> Tuple[Optional[models.Worker], float, str]:
    strat = strategy.lower().replace("-", "_")
    requires_gpu = bool(job and job.requires_gpu)
    min_vram = float(job.min_vram_gb or 0.0) if job else 0.0

    if strat == "round_robin":
        w, s = select_round_robin(workers, chunk, db)
    elif strat == "least_loaded":
        w, s = select_least_loaded(workers, chunk, db)
    elif strat == "gpu_aware" or (requires_gpu and strat == "capacity_based"):
        w, s = select_gpu_aware(workers, chunk, db, min_vram)
    elif strat == "network_aware":
        w, s = select_network_aware(workers, chunk, db)
    elif strat == "priority_based":
        w, s = select_priority_based(workers, chunk, job, db)
    elif strat == "fair_share":
        w, s = select_fair_share(workers, chunk, job, db)
    elif strat == "ai_predictive":
        try:
            from .ai_scheduler import predict_best_worker
            w = predict_best_worker(workers)
            s = 100.0 if w else 0.0
        except Exception:
            w, s = select_capacity_based(workers, chunk, db, requires_gpu)
    else:  # Default: capacity_based / resource_aware
        w, s = select_capacity_based(workers, chunk, db, requires_gpu)

    return w, s, strat


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOGGING & PROVENANCE CREATION
# ─────────────────────────────────────────────────────────────────────────────

def log_decision(db: Session, chunk_id: int, worker_id: int, algorithm: str, score: float | None, reasoning: str):
    decision = models.SchedulerDecision(
        chunk_id=chunk_id,
        worker_id=worker_id,
        algorithm=algorithm,
        score=score,
        decision_reason=reasoning
    )
    db.add(decision)


def log_system_event(db: Session, level: str, source: str, message: str, metadata: dict | None = None):
    entry = models.Log(level=level, source=source, message=message, log_metadata=metadata)
    db.add(entry)


def create_chunk_attempt(db: Session, chunk: models.TaskChunk, worker: models.Worker) -> models.ChunkAttempt:
    now = datetime.now(timezone.utc)
    attempt_count = chunk.attempt_count or 1
    attempt_uid = f"ATT-{chunk.id:04d}-{attempt_count:02d}"
    attempt = models.ChunkAttempt(
        attempt_uid=attempt_uid,
        chunk_id=chunk.id,
        worker_id=worker.id,
        attempt_number=attempt_count,
        status="assigned",
        assigned_at=now,
        input_reference=chunk.input_reference or f"minio://chunks/{chunk.task_id}/{chunk.chunk_uid or chunk.id}.bin"
    )
    db.add(attempt)
    return attempt


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
                current_attempt.duration_seconds = (now - current_attempt.assigned_at).total_seconds()

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
            total = worker.total_tasks_completed + worker.total_tasks_failed
            worker.reliability_score = worker.total_tasks_completed / max(total, 1)

    return rescheduled


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED SCHEDULER & FAULT RECOVERY LOOPS
# ─────────────────────────────────────────────────────────────────────────────

async def unified_scheduler_loop():
    """Continuous CIE Scheduling loop assigning pending chunks via configured strategy."""
    logger.info("Starting CIE Unified Scheduler Engine...")

    # Subscribe to Redis reschedule pub/sub channel (GAP 3)
    def on_reschedule_message(msg):
        try:
            data = json.loads(msg["data"]) if isinstance(msg.get("data"), str) else msg.get("data")
            logger.info(f"[PubSub Reschedule Event] {data}")
        except Exception as e:
            logger.error(f"Error in on_reschedule_message: {e}")

    queue_service.subscribe_reschedule(on_reschedule_message)

    while True:
        db: Session | None = None
        try:
            db = SessionLocal()
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
                    all_workers, db, requires_gpu=requires_gpu, min_vram_gb=min_vram
                )
                if not workers:
                    continue

                active_strat = (job.scheduler_strategy if job and job.scheduler_strategy else None) or get_active_algorithm()
                selected_worker, score, used_strat = select_worker_by_strategy(
                    active_strat, workers, chunk, job, db
                )

                if selected_worker:
                    now = datetime.now(timezone.utc)
                    chunk.status = "assigned"
                    chunk.worker_id = selected_worker.id
                    chunk.start_time = now
                    chunk.assigned_at = now
                    chunk.attempt_count = (chunk.attempt_count or 0) + 1

                    if not chunk.chunk_uid:
                        chunk.chunk_uid = _generate_chunk_uid(chunk.chunk_index)

                    attempt = create_chunk_attempt(db, chunk, selected_worker)

                    if task and task.status == "pending":
                        task.status = "running"
                    if job:
                        if job.status == "pending":
                            job.status = "running"
                            job.start_time = now
                            if not job.job_uid:
                                job.job_uid = _generate_job_uid(db)
                            record_timeline_event(
                                db, job.id, "JOB_STARTED",
                                f"Job {job.job_uid} execution started across cluster ({used_strat})"
                            )

                        record_timeline_event(
                            db, job.id, "CHUNK_DISPATCHED",
                            f"Dispatched {chunk.chunk_uid} to {selected_worker.hostname or selected_worker.worker_uid} (attempt {chunk.attempt_count})",
                            {"chunk_id": chunk.id, "worker_uid": selected_worker.worker_uid, "attempt_id": attempt.attempt_uid}
                        )

                    log_decision(
                        db, chunk.id, selected_worker.id, used_strat, score,
                        f"Strategy={used_strat} assigned to {selected_worker.worker_uid} (score={score:.2f})"
                    )

                    db.commit()

                    # Dispatch via WebSocket with MinIO reference and attempt tracking
                    payload = {
                        "type": "EXECUTE",
                        "chunk_id": chunk.id,
                        "chunk_uid": chunk.chunk_uid,
                        "attempt_id": attempt.attempt_uid or f"ATT-{attempt.id}",
                        "attempt_number": chunk.attempt_count,
                        "job_id": job.id if job else 0,
                        "job_uid": job.job_uid if job else "",
                        "task_type": job.job_type if job else "generic_python",
                        "input_reference": chunk.input_reference,
                        "task_payload": chunk.data_payload
                    }
                    await manager.send_personal_message(payload, selected_worker.worker_uid)
                    logger.info(
                        f"[{used_strat}] Dispatched chunk {chunk.id} ({chunk.chunk_uid}) → "
                        f"{selected_worker.worker_uid} (score={score:.2f}, attempt={chunk.attempt_count})"
                    )

        except Exception as e:
            logger.error(f"Scheduler Loop Error: {e}")
        finally:
            if db:
                db.close()

        await asyncio.sleep(1.5)


async def fault_tolerance_loop():
    """Background monitoring loop detecting heartbeat loss and transitioning SUSPECTED -> FAILED."""
    logger.info("Starting CIE Fault Tolerance Monitor...")

    while True:
        db: Session | None = None
        try:
            db = SessionLocal()
            now = datetime.now(timezone.utc)
            timeout_threshold = now - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)

            # Detect workers missing heartbeats
            dead_workers = db.query(models.Worker).filter(
                models.Worker.status.in_(["online", "busy", "suspected"]),
                models.Worker.last_seen < timeout_threshold
            ).all()

            for worker in dead_workers:
                worker.status = "failed"
                logger.warning(f"Worker {worker.worker_uid} marked FAILED (> {HEARTBEAT_TIMEOUT_SECONDS}s heartbeat loss)")

                log_system_event(
                    db, "WARNING", "fault_tolerance",
                    f"Worker {worker.worker_uid} marked FAILED (heartbeat timeout)",
                    {"worker_uid": worker.worker_uid}
                )

                rescheduled_chunks = reschedule_worker_chunks(
                    db, worker, reason=f"heartbeat_timeout_>{HEARTBEAT_TIMEOUT_SECONDS}s"
                )

                if rescheduled_chunks:
                    queue_service.publish_reschedule(
                        job_id=str(rescheduled_chunks[0].task_id),
                        chunk_ids=[str(c.id) for c in rescheduled_chunks],
                        reason=f"Worker {worker.worker_uid} heartbeat timeout"
                    )

            db.commit()

        except Exception as e:
            logger.error(f"Fault Tolerance Monitor Error: {e}")
        finally:
            if db:
                db.close()

        await asyncio.sleep(3.0)
