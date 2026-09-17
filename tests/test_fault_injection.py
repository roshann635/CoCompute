"""
Test Suite: Fault Injection & Master Restart Recovery
Tests recovery_after_restart, stale attempt cancellation, worker reset, and cluster reconciliation.
"""

import pytest
from datetime import datetime, timezone
from master.app.engine.recovery import recover_after_restart
from master.app.engine.leadership import is_leader
from master.app.db import models


def test_master_restart_recovery_procedure(db_session):
    """Verifies recover_after_restart reclaims orphaned running/assigned chunks and resets offline workers."""
    incarnation_id = "master-reborn-01"
    
    # Setup worker with active reservations
    worker = models.Worker(
        worker_uid="W-BUSY-01",
        status="online",
        running_tasks=2,
        reserved_cpu_cores=4,
        reserved_ram_gb=8.0
    )
    db_session.add(worker)
    db_session.commit()
    
    # Setup job with stale assigned chunk from old master
    job = models.Job(name="Orphaned Job", job_type="sorting", status="running")
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, name="Sorting", type="sorting", status="running")
    db_session.add(task)
    db_session.commit()
    
    chunk = models.TaskChunk(
        task_id=task.id,
        chunk_index=0,
        status="running",
        worker_id=worker.id,
        version=1
    )
    db_session.add(chunk)
    db_session.commit()
    
    stale_attempt = models.ChunkAttempt(
        attempt_uid="ATT-0001-01",
        chunk_id=chunk.id,
        worker_id=worker.id,
        status="running",
        master_incarnation_id="old-dead-master"
    )
    db_session.add(stale_attempt)
    db_session.commit()
    
    # Run recovery
    report = recover_after_restart(db_session, incarnation_id, "master-host-1")
    assert report["status"] == "success"
    assert report["leadership_acquired"] is True
    assert report["workers_reset"] >= 1
    assert report["chunks_reclaimed"] >= 1
    assert report["attempts_cancelled"] >= 1
    
    # Verify worker was reset
    db_session.refresh(worker)
    assert worker.status == "offline"
    assert worker.running_tasks == 0
    assert worker.reserved_cpu_cores == 0
    assert worker.reserved_ram_gb == 0.0
    
    # Verify chunk was reset to pending with bumped version
    db_session.refresh(chunk)
    assert chunk.status == "pending"
    assert chunk.worker_id is None
    assert chunk.version == 2
    
    # Verify stale attempt was cancelled
    db_session.refresh(stale_attempt)
    assert stale_attempt.status == "cancelled_stale"
