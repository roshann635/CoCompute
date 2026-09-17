"""
CoCompute Hardening: Full Provenance & Traceability API

Provides chunk -> attempt -> worker lineage, Definition of Done status,
validation results, checksums, and timing traces.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from ..db.database import get_db
from ..db import models

router = APIRouter(prefix="/jobs", tags=["provenance"])


@router.get("/{job_id}/provenance", response_model=Dict[str, Any])
def get_job_provenance(job_id: int, db: Session = Depends(get_db)):
    """
    Returns complete provenance lineage for a given job.
    Includes all task chunks, attempts, worker assignments, timing,
    checksums, validation outcomes, artifacts, and Definition of Done compliance.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    tasks_provenance = []
    all_chunks_accepted = True
    total_chunks = 0
    completed_chunks = 0
    total_attempts = 0

    for task in job.tasks:
        chunks_data = []
        for chunk in task.chunks:
            total_chunks += 1
            chunk_attempts = []
            
            for att in chunk.attempts:
                total_attempts += 1
                worker_info = None
                if att.worker:
                    worker_info = {
                        "worker_id": att.worker.id,
                        "worker_uid": att.worker.worker_uid,
                        "hostname": att.worker.hostname,
                        "ip_address": att.worker.ip_address,
                        "reliability_score": att.worker.reliability_score,
                    }

                chunk_attempts.append({
                    "attempt_uid": att.attempt_uid,
                    "attempt_number": att.attempt_number,
                    "status": att.status,
                    "is_speculative": att.is_speculative,
                    "master_incarnation_id": att.master_incarnation_id,
                    "worker_session_id": att.worker_session_id,
                    "assigned_at": att.assigned_at.isoformat() if att.assigned_at else None,
                    "started_at": att.started_at.isoformat() if att.started_at else None,
                    "completed_at": att.completed_at.isoformat() if att.completed_at else None,
                    "duration_seconds": att.duration_seconds,
                    "checksum_sha256": att.checksum_sha256,
                    "failure_reason": att.failure_reason,
                    "worker": worker_info,
                })

            is_accepted = chunk.accepted_attempt_id is not None
            if is_accepted:
                completed_chunks += 1
            else:
                all_chunks_accepted = False

            chunks_data.append({
                "chunk_id": chunk.id,
                "chunk_uid": chunk.chunk_uid,
                "chunk_index": chunk.chunk_index,
                "status": chunk.status,
                "version": chunk.version,
                "accepted_attempt_id": chunk.accepted_attempt_id,
                "normal_attempt_count": chunk.normal_attempt_count,
                "speculative_attempt_count": chunk.speculative_attempt_count,
                "is_speculative": chunk.is_speculative,
                "attempts": chunk_attempts,
            })

        tasks_provenance.append({
            "task_id": task.id,
            "name": task.name,
            "type": task.type,
            "status": task.status,
            "chunks": chunks_data,
        })

    artifacts_data = []
    for art in job.artifacts:
        artifacts_data.append({
            "id": art.id,
            "storage_location": art.storage_location,
            "size_bytes": art.size_bytes,
            "checksum_sha256": art.checksum_sha256,
            "lifecycle_state": art.lifecycle_state,
            "created_at": art.created_at.isoformat() if art.created_at else None,
        })

    # Definition of Done Verification
    is_definition_of_done = (
        job.status == "completed" and
        total_chunks > 0 and
        completed_chunks == total_chunks and
        all_chunks_accepted and
        len(artifacts_data) > 0
    )

    return {
        "job_id": job.id,
        "job_uid": job.job_uid,
        "job_type": job.job_type,
        "status": job.status,
        "definition_of_done": is_definition_of_done,
        "metrics": {
            "total_chunks": total_chunks,
            "completed_chunks": completed_chunks,
            "total_attempts": total_attempts,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "start_time": job.start_time.isoformat() if job.start_time else None,
            "end_time": job.end_time.isoformat() if job.end_time else None,
            "actual_duration_sec": job.actual_duration_sec,
        },
        "quality_and_validation": job.result_quality,
        "tasks": tasks_provenance,
        "artifacts": artifacts_data,
    }
