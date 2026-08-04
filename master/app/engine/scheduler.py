"""
Unified Scheduler with Strategy Pattern.

Supports three scheduling algorithms:
  1. round_robin — simple rotation (baseline)
  2. resource_aware — weighted score based on CPU, RAM, and current load
  3. ai_predictive — ML-based prediction (falls back to resource_aware if model not available)

The active algorithm is set via the SCHEDULER_ALGORITHM environment variable.
All scheduling decisions are logged to the SchedulerDecision table for auditability.

FR-14: Dynamic Load Rebalancing — workers above HIGH_UTILIZATION_THRESHOLD are skipped
entirely (not just penalized) to avoid overloading active nodes.
"""
import asyncio
import os
import logging
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from ..db.database import SessionLocal
from ..db import models
from ..network.ws_manager import manager
from .round_robin import round_robin_select

logger = logging.getLogger(__name__)

SCHEDULER_ALGORITHM = os.getenv("SCHEDULER_ALGORITHM", "resource_aware")
MAX_RETRIES = 3
HEARTBEAT_TIMEOUT_SECONDS = 15

# FR-14: Workers above this CPU utilization threshold are skipped during scheduling
HIGH_UTILIZATION_THRESHOLD = float(os.getenv("HIGH_UTILIZATION_THRESHOLD", "85.0"))
# FR-14: Workers above this RAM usage percentage are also skipped
HIGH_RAM_THRESHOLD = float(os.getenv("HIGH_RAM_THRESHOLD", "90.0"))


def filter_available_workers(workers: list[models.Worker], db: Session) -> tuple[list[models.Worker], list[models.Worker]]:
    """
    FR-14: Filter out workers that exceed utilization thresholds.
    Returns (available_workers, skipped_workers).
    Workers above HIGH_UTILIZATION_THRESHOLD (CPU) or HIGH_RAM_THRESHOLD (RAM)
    are excluded entirely from scheduling — not just penalized.
    """
    available = []
    skipped = []
    for w in workers:
        cpu = w.cpu_utilization or 0.0
        ram = w.ram_usage or 0.0
        if cpu > HIGH_UTILIZATION_THRESHOLD or ram > HIGH_RAM_THRESHOLD:
            skipped.append(w)
            log_system_event(
                db, "WARNING", "scheduler",
                f"FR-14: Skipping overloaded worker {w.worker_uid} "
                f"(CPU={cpu:.1f}% > {HIGH_UTILIZATION_THRESHOLD}% threshold or "
                f"RAM={ram:.1f}% > {HIGH_RAM_THRESHOLD}% threshold)",
                {"worker_uid": w.worker_uid, "cpu": cpu, "ram": ram}
            )
        else:
            available.append(w)
    return available, skipped


# Runtime-configurable scheduler algorithm (can be changed via API)
_active_algorithm = SCHEDULER_ALGORITHM


def get_active_algorithm() -> str:
    return _active_algorithm


def set_active_algorithm(algorithm: str) -> None:
    global _active_algorithm
    valid = {"round_robin", "resource_aware", "ai_predictive"}
    if algorithm not in valid:
        raise ValueError(f"Unknown algorithm: {algorithm}. Valid: {valid}")
    _active_algorithm = algorithm
    logger.info(f"Scheduler algorithm changed to: {algorithm}")


def resource_aware_select(workers: list[models.Worker], chunk: models.TaskChunk, db: Session) -> tuple[models.Worker | None, float]:
    """
    Resource-aware scheduling using the Adaptive Resource-Aware formula:

    Score(w) = (CPU_cores * 10 + RAM_total * 2) * ReliabilityScore
               ÷ (ActiveTasks + 1)
               - (CPU_utilization * 0.5)
               - (RAM_usage * 0.3)

    Returns (best_worker, best_score).
    """
    best_worker = None
    best_score = -1.0

    for w in workers:
        # Base capacity score
        capacity = (w.cpu_cores * 10) + (w.ram_total * 2)

        # Reliability multiplier (0.0 – 1.0)
        reliability = w.reliability_score if w.reliability_score else 0.5

        # Active task penalty
        active_tasks = db.query(models.TaskChunk).filter(
            models.TaskChunk.worker_id == w.id,
            models.TaskChunk.status.in_(["assigned", "running"])
        ).count()

        # Current utilization penalty
        cpu_penalty = (w.cpu_utilization or 0) * 0.5
        ram_penalty = (w.ram_usage or 0) * 0.3

        score = (capacity * reliability) / (active_tasks + 1) - cpu_penalty - ram_penalty

        if score > best_score:
            best_score = score
            best_worker = w

    return best_worker, best_score


def log_decision(db: Session, chunk_id: int, worker_id: int, algorithm: str, score: float | None, reasoning: str):
    """Record a scheduling decision for audit."""
    decision = models.SchedulerDecision(
        chunk_id=chunk_id,
        worker_id=worker_id,
        algorithm=algorithm,
        score=score,
        reasoning=reasoning
    )
    db.add(decision)


def log_system_event(db: Session, level: str, source: str, message: str, metadata: dict | None = None):
    """Write to the Log table."""
    entry = models.Log(level=level, source=source, message=message, log_metadata=metadata)
    db.add(entry)


async def unified_scheduler_loop():
    """
    Main scheduler loop. Runs the selected algorithm every 2 seconds.
    """
    logger.info(f"Starting Unified Scheduler (algorithm={SCHEDULER_ALGORITHM})...")

    while True:
        db: Session | None = None
        try:
            db = SessionLocal()

            # 1. Get online workers
            all_workers = db.query(models.Worker).filter(models.Worker.status == "online").all()
            if not all_workers:
                await asyncio.sleep(2)
                continue

            # FR-14: Filter out overloaded workers before scheduling
            workers, skipped = filter_available_workers(all_workers, db)
            if skipped:
                logger.debug(f"FR-14: Skipped {len(skipped)} overloaded worker(s). {len(workers)} available.")

            if not workers:
                logger.warning("All online workers are over utilization threshold. No chunks will be dispatched.")
                db.commit()  # commit the warning logs
                await asyncio.sleep(2)
                continue

            # 2. Get pending chunks (batch of 50)
            pending_chunks = db.query(models.TaskChunk).filter(
                models.TaskChunk.status == "pending"
            ).limit(50).all()

            for chunk in pending_chunks:
                selected_worker = None
                score = None
                algorithm_used = get_active_algorithm()

                if algorithm_used == "round_robin":
                    selected_worker = round_robin_select(workers, chunk, db)
                    score = 0.0

                elif algorithm_used == "resource_aware":
                    selected_worker, score = resource_aware_select(workers, chunk, db)

                elif algorithm_used == "ai_predictive":
                    # Try AI first, fall back to resource_aware
                    try:
                        from .ai_scheduler import predict_best_worker
                        selected_worker = predict_best_worker(workers)
                        score = 0.0
                    except Exception:
                        selected_worker, score = resource_aware_select(workers, chunk, db)
                        algorithm_used = "resource_aware_fallback"

                else:
                    # Default fallback
                    selected_worker, score = resource_aware_select(workers, chunk, db)

                if selected_worker:
                    chunk.status = "assigned"
                    chunk.worker_id = selected_worker.id
                    chunk.start_time = datetime.now(timezone.utc)
                    chunk.attempt_count += 1

                    # Update the parent task & job to "running" if still pending
                    task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
                    if task and task.status == "pending":
                        task.status = "running"
                        job = db.query(models.Job).filter(models.Job.id == task.job_id).first()
                        if job and job.status == "pending":
                            job.status = "running"
                            job.start_time = datetime.now(timezone.utc)

                    # Log decision
                    log_decision(
                        db, chunk.id, selected_worker.id, algorithm_used, score,
                        f"Assigned to {selected_worker.worker_uid} (cores={selected_worker.cpu_cores}, ram={selected_worker.ram_total}GB)"
                    )

                    db.commit()

                    # Send task via WebSocket
                    payload = {
                        "type": "EXECUTE",
                        "chunk_id": chunk.id,
                        "task_payload": chunk.data_payload
                    }
                    await manager.send_personal_message(payload, selected_worker.worker_uid)
                    logger.info(
                        f"[{algorithm_used}] Assigned chunk {chunk.id} → {selected_worker.worker_uid} (score={score:.2f})"
                    )

        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
        finally:
            if db:
                db.close()

        await asyncio.sleep(2)


async def fault_tolerance_loop():
    """
    Background loop that:
    1. Detects workers that haven't sent a heartbeat within HEARTBEAT_TIMEOUT_SECONDS
    2. Marks them offline
    3. Requeues their assigned chunks (respecting max retry limit)
    """
    logger.info("Starting Fault Tolerance Monitor...")

    while True:
        db: Session | None = None
        try:
            db = SessionLocal()

            timeout_threshold = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
            dead_workers = db.query(models.Worker).filter(
                models.Worker.status == "online",
                models.Worker.last_seen < timeout_threshold
            ).all()

            for worker in dead_workers:
                logger.warning(f"Worker {worker.worker_uid} timed out. Marking offline.")
                worker.status = "offline"
                worker.running_tasks = 0

                log_system_event(db, "WARNING", "fault_tolerance",
                                 f"Worker {worker.worker_uid} marked offline (heartbeat timeout)")

                # Requeue their assigned chunks
                orphaned_chunks = db.query(models.TaskChunk).filter(
                    models.TaskChunk.worker_id == worker.id,
                    models.TaskChunk.status.in_(["assigned", "running"])
                ).all()

                for chunk in orphaned_chunks:
                    if chunk.attempt_count < MAX_RETRIES:
                        logger.info(f"Requeuing orphaned chunk {chunk.id} (attempt {chunk.attempt_count}/{MAX_RETRIES})")
                        chunk.status = "pending"
                        chunk.worker_id = None
                    else:
                        logger.error(f"Chunk {chunk.id} exceeded max retries ({MAX_RETRIES}). Marking failed.")
                        chunk.status = "failed"
                        chunk.end_time = datetime.now(timezone.utc)

                        # Update job failed count
                        task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
                        if task:
                            job = db.query(models.Job).filter(models.Job.id == task.job_id).first()
                            if job:
                                job.failed_tasks += 1

                        # Update worker reliability
                        worker.total_tasks_failed += 1
                        total = worker.total_tasks_completed + worker.total_tasks_failed
                        worker.reliability_score = worker.total_tasks_completed / max(total, 1)

                        log_system_event(db, "ERROR", "fault_tolerance",
                                         f"Chunk {chunk.id} failed permanently after {MAX_RETRIES} retries",
                                         {"chunk_id": chunk.id, "worker_uid": worker.worker_uid})

            if dead_workers:
                db.commit()

        except Exception as e:
            logger.error(f"Fault Tolerance Error: {e}")
        finally:
            if db:
                db.close()

        await asyncio.sleep(5)
