"""
Speculative Execution & Straggler Mitigation Engine — CoCompute 3.0.

Periodically inspects running task chunks. If a chunk is taking unusually long
(e.g., execution duration > 2.0x median of completed chunks in that job),
the detector identifies it as a straggler and spawns a speculative duplicate attempt
on an idle fast worker.

The first valid checksum-verified attempt to complete wins; late duplicate results
are silently dropped by the `accepted_attempt_id` provenance guard.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from ..db import models

logger = logging.getLogger(__name__)

STRAGGLER_THRESHOLD_MULTIPLIER = 2.0
MIN_ELAPSED_SECONDS_BEFORE_SPECULATIVE = 3.0


def check_and_spawn_speculative_attempts(db: Session) -> List[Dict[str, Any]]:
    """
    Scans active running jobs for straggling chunks and creates speculative replicas.
    """
    active_jobs = db.query(models.Job).filter(
        models.Job.status == "running",
        models.Job.is_speculative_enabled == True
    ).all()

    spawned = []
    now = datetime.now(timezone.utc)

    for job in active_jobs:
        tasks = db.query(models.Task).filter(models.Task.job_id == job.id).all()
        task_ids = [t.id for t in tasks]
        if not task_ids:
            continue

        # Get completed chunks to compute median/average runtime
        completed_attempts = db.query(models.ChunkAttempt).join(models.TaskChunk).filter(
            models.TaskChunk.task_id.in_(task_ids),
            models.ChunkAttempt.status == "completed",
            models.ChunkAttempt.duration_seconds.isnot(None)
        ).all()

        durations = [a.duration_seconds for a in completed_attempts if a.duration_seconds and a.duration_seconds > 0]
        if len(durations) < 2:
            # Not enough baseline data yet
            continue

        durations.sort()
        median_duration = durations[len(durations) // 2]
        threshold_duration = max(MIN_ELAPSED_SECONDS_BEFORE_SPECULATIVE, median_duration * STRAGGLER_THRESHOLD_MULTIPLIER)

        # Inspect running chunks
        running_chunks = db.query(models.TaskChunk).filter(
            models.TaskChunk.task_id.in_(task_ids),
            models.TaskChunk.status == "running"
        ).all()

        for chunk in running_chunks:
            assigned_time = chunk.assigned_at
            if not assigned_time:
                continue
            if assigned_time.tzinfo is None:
                assigned_time = assigned_time.replace(tzinfo=timezone.utc)
            elapsed = (now - assigned_time).total_seconds()
            if elapsed > threshold_duration:
                # Check speculative retry budget (Invariant 5)
                if (chunk.speculative_attempt_count or 0) >= (chunk.max_speculative or 2):
                    logger.info(f"[Speculative] Chunk {chunk.id} has reached max speculative attempts ({chunk.max_speculative}).")
                    continue

                # Identify the slow worker
                slow_worker = db.query(models.Worker).filter(models.Worker.id == chunk.worker_id).first()
                slow_uid = slow_worker.worker_uid if slow_worker else "unknown"

                # Find a fast alternate worker
                fast_worker = db.query(models.Worker).filter(
                    models.Worker.status.in_(["online", "idle"]),
                    models.Worker.id != chunk.worker_id,
                    models.Worker.lifecycle_state != "draining",
                    models.Worker.trust_status != "rejected"
                ).order_by(models.Worker.reliability_score.desc(), models.Worker.running_tasks.asc()).first()

                if not fast_worker:
                    logger.debug(f"[Speculative] No alternate worker available for speculative execution of chunk {chunk.id}")
                    continue

                # ── Invariant 5: Independent Retry Budget ──────────────────
                chunk.speculative_attempt_count = (chunk.speculative_attempt_count or 0) + 1
                chunk.is_speculative = True
                spec_num = chunk.speculative_attempt_count
                attempt_uid = f"ATT-{chunk.id:04d}-S{spec_num:02d}"

                try:
                    from ..main import CURRENT_INCARNATION_ID
                except Exception:
                    CURRENT_INCARNATION_ID = "master-current"
                from ..network.ws_manager import manager

                attempt = models.ChunkAttempt(
                    attempt_uid=attempt_uid,
                    chunk_id=chunk.id,
                    worker_id=fast_worker.id,
                    attempt_number=(chunk.attempt_count or 0) + spec_num,
                    status="assigned",
                    is_speculative=True,
                    master_incarnation_id=CURRENT_INCARNATION_ID,
                    worker_session_id=fast_worker.session_id,
                    assigned_at=now
                )
                db.add(attempt)
                fast_worker.running_tasks = (fast_worker.running_tasks or 0) + 1

                logger.warning(
                    f"[Straggler Detected] Job {job.job_uid or job.id} Chunk {chunk.chunk_uid or chunk.id} "
                    f"on {slow_uid} has run for {elapsed:.1f}s (threshold: {threshold_duration:.1f}s). "
                    f"Dispatched speculative attempt {attempt_uid} to {fast_worker.worker_uid}!"
                )

                from .scheduler import record_timeline_event
                record_timeline_event(
                    db, job.id, "SPECULATIVE_EXECUTION_TRIGGERED",
                    f"Speculative attempt {attempt_uid} dispatched to {fast_worker.worker_uid} (Slow Worker: {slow_uid}, Elapsed: {elapsed:.1f}s)",
                    {"chunk_id": chunk.id, "slow_worker": slow_uid, "fast_worker": fast_worker.worker_uid, "speculative_attempt": attempt_uid}
                )

                # Dispatch over WebSocket
                msg = {
                    "action": "EXECUTE",
                    "protocol_version": "1.0",
                    "master_incarnation_id": CURRENT_INCARNATION_ID,
                    "chunk_id": chunk.id,
                    "chunk_uid": chunk.chunk_uid or f"CHUNK-{chunk.id}",
                    "attempt_id": attempt_uid,
                    "job_id": job.id,
                    "job_uid": job.job_uid or f"JOB-{job.id}",
                    "task_type": job.job_type or "generic_python",
                    "payload": chunk.input_data or {},
                    "is_speculative": True
                }

                try:
                    asyncio.create_task(manager.send_to_worker(fast_worker.worker_uid, msg))
                except Exception as e:
                    logger.error(f"[Speculative] Failed to dispatch speculative attempt: {e}")

                spawned.append({
                    "job_id": job.id,
                    "chunk_id": chunk.id,
                    "chunk_uid": chunk.chunk_uid,
                    "slow_worker_uid": slow_uid,
                    "fast_worker_uid": fast_worker.worker_uid,
                    "attempt_uid": attempt_uid,
                    "elapsed_sec": round(elapsed, 2),
                    "threshold_sec": round(threshold_duration, 2)
                })

    if spawned:
        db.commit()

    return spawned


async def straggler_watchdog_loop():
    """Background task running every 3 seconds to mitigate stragglers."""
    logger.info("Starting Straggler Mitigation Watchdog...")
    while True:
        db: Optional[Session] = None
        try:
            db = SessionLocal()
            check_and_spawn_speculative_attempts(db)
        except Exception as e:
            logger.error(f"Straggler watchdog loop error: {e}")
        finally:
            if db:
                db.close()
        await asyncio.sleep(3.0)
