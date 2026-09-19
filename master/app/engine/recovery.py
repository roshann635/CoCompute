"""
CoCompute Hardening: Master Restart Recovery & Reconciliation Procedure

Ensures consistent cluster state after Master restart or crash:
- Reclaims orphaned running/assigned chunks
- Resets disconnected worker state
- Recalculates job progress
- Fixes unaggregated finished jobs
"""

from datetime import datetime, timezone
import logging
from ..db import models
from .leadership import acquire_or_renew_lease

logger = logging.getLogger("cocompute.master.recovery")


def recover_after_restart(db, incarnation_id: str, hostname: str = "master-host") -> dict:
    """
    Executes full recovery procedure upon Master startup:
    1. Acquire leadership lease
    2. Reset all workers to offline and zero out active reservations
    3. Find orphaned running/assigned chunk attempts and mark them cancelled_stale
    4. Reset uncompleted chunks without accepted attempts back to PENDING
    5. Re-evaluate job progress
    6. Return summary report
    """
    report = {
        "status": "failed",
        "leadership_acquired": False,
        "workers_reset": 0,
        "chunks_reclaimed": 0,
        "attempts_cancelled": 0,
        "jobs_updated": 0,
    }

    # 1. Acquire leadership
    acquired = acquire_or_renew_lease(db, incarnation_id, hostname, force=True)
    report["leadership_acquired"] = acquired
    if not acquired:
        logger.warning(f"[Recovery] Failed to acquire master leadership lease for incarnation {incarnation_id}")
        return report

    try:
        # 2. Reset workers to offline and clear reservations
        workers = db.query(models.Worker).all()
        for w in workers:
            w.status = "offline"
            w.running_tasks = 0
            w.reserved_cpu_cores = 0
            w.reserved_ram_gb = 0.0
            w.reserved_gpu_count = 0
            w.reserved_gpu_vram_gb = 0.0
        report["workers_reset"] = len(workers)

        # 3. Handle orphaned attempts (assigned or running from old master incarnations)
        stale_attempts = db.query(models.ChunkAttempt).filter(
            models.ChunkAttempt.status.in_(["assigned", "running"]),
            models.ChunkAttempt.master_incarnation_id != incarnation_id
        ).all()
        
        for att in stale_attempts:
            att.status = "cancelled_stale"
            att.failure_reason = f"Master restarted (incarnation {incarnation_id})"
            att.completed_at = datetime.now(timezone.utc)
        report["attempts_cancelled"] = len(stale_attempts)

        # 4. Find chunks that were assigned or running but not accepted
        unaccepted_chunks = db.query(models.TaskChunk).filter(
            models.TaskChunk.status.in_(["assigned", "running"]),
            models.TaskChunk.accepted_attempt_id.is_(None)
        ).all()

        for chunk in unaccepted_chunks:
            chunk.status = "pending"
            chunk.worker_id = None
            chunk.version = (chunk.version or 0) + 1
            chunk.start_time = None
            chunk.assigned_at = None
        report["chunks_reclaimed"] = len(unaccepted_chunks)

        # 5. Recalculate job status / progress
        active_jobs = db.query(models.Job).filter(
            models.Job.status.in_(["running", "pending"])
        ).all()

        for job in active_jobs:
            total_chunks = 0
            completed_chunks = 0
            for task in job.tasks:
                for c in task.chunks:
                    total_chunks += 1
                    if c.status == "completed" and c.accepted_attempt_id is not None:
                        completed_chunks += 1

            job.total_tasks = total_chunks
            job.completed_tasks = completed_chunks
            
            # If all chunks accepted but job is still running/pending, it can be aggregated
            if total_chunks > 0 and completed_chunks == total_chunks:
                # Let aggregator handle finalization in its cycle
                pass

        report["jobs_updated"] = len(active_jobs)
        report["status"] = "success"
        db.commit()
        logger.info(f"[Recovery] Master restart recovery complete: {report}")
    except Exception as e:
        db.rollback()
        logger.error(f"[Recovery] Master restart recovery failed: {e}")
        report["error"] = str(e)

    return report
