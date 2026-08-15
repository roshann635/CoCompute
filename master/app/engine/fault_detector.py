"""
CoCompute CIE Fault Detector.

Provides immediate detection of worker disconnections and health degradation.
Transitions worker immediately to SUSPECTED state upon WebSocketDisconnect (< 1s),
publishes rescheduling events to Redis Pub/Sub, and manages failure confirmation timeouts.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..db import models
from .scheduler import reschedule_worker_chunks, record_timeline_event
from ..services.queue_service import queue_service

logger = logging.getLogger(__name__)


class FaultDetector:
    """
    Real-time fault detector reacting instantaneously to worker disconnection events.
    """

    @classmethod
    async def mark_suspected(cls, db: Session, worker_uid: str, reason: str = "WebSocketDisconnect") -> List[Dict[str, Any]]:
        """
        Immediately marks worker as SUSPECTED (< 1s) upon WebSocketDisconnect or error,
        queries all affected chunks, reschedules them, and publishes to Redis Pub/Sub channel.
        """
        worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
        if not worker:
            return []

        logger.warning(f"[FaultDetector] Immediate SUSPECTED for worker {worker_uid} (reason: {reason})")
        worker.status = "suspected"
        worker.running_tasks = 0

        # Reschedule all incomplete chunks assigned to this worker
        rescheduled_chunks = reschedule_worker_chunks(db, worker, reason=reason)
        affected_info = []

        if rescheduled_chunks:
            for chunk in rescheduled_chunks:
                task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
                job_id = task.job_id if task else 0
                affected_info.append({
                    "job_id": str(job_id),
                    "chunk_id": str(chunk.id),
                    "chunk_uid": chunk.chunk_uid or f"CHUNK-{chunk.id}",
                    "worker_uid": worker_uid
                })

            # Publish event to Redis
            if affected_info:
                queue_service.publish_reschedule(
                    job_id=affected_info[0]["job_id"],
                    chunk_ids=[c["chunk_id"] for c in affected_info],
                    reason=f"Worker {worker_uid} disconnected ({reason})"
                )

        db.commit()
        return affected_info

    @classmethod
    async def mark_failed(cls, db: Session, worker_uid: str, reason: str = "HeartbeatTimeout") -> None:
        """
        Confirms worker failure and transitions SUSPECTED -> FAILED.
        """
        worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
        if not worker:
            return
        worker.status = "failed"
        db.commit()
        logger.error(f"[FaultDetector] Worker {worker_uid} confirmed FAILED ({reason})")


# Singleton instance
fault_detector = FaultDetector()
