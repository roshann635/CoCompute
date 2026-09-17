"""
Test Suite: Scheduler Concurrency, Optimistic Locking & Atomic CAS
Tests concurrent scheduler assignments, resource reservation rollbacks, and atomic CAS result acceptance.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import update
from master.app.db import models


def test_optimistic_concurrency_on_chunk_assignment(db_session):
    """Verifies that two scheduler loops competing for the same pending chunk cannot double-assign it."""
    # Setup job and chunk
    job = models.Job(name="Test Concurrency Job", job_type="sorting", status="running")
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, name="Sorting", type="sorting", status="running")
    db_session.add(task)
    db_session.commit()
    
    chunk = models.TaskChunk(task_id=task.id, chunk_index=0, status="pending", version=0)
    db_session.add(chunk)
    db_session.commit()
    
    # Scheduler Loop 1 reads chunk at version 0
    s1_ver = chunk.version
    
    # Scheduler Loop 2 reads chunk at version 0
    s2_ver = chunk.version
    
    # Scheduler Loop 1 assigns chunk
    rows_s1 = db_session.execute(
        update(models.TaskChunk)
        .where(
            models.TaskChunk.id == chunk.id,
            models.TaskChunk.status == "pending",
            models.TaskChunk.version == s1_ver
        )
        .values(status="assigned", version=s1_ver + 1)
    ).rowcount
    db_session.commit()
    
    # Scheduler Loop 2 attempts to assign chunk with stale version 0 -> MUST FAIL
    rows_s2 = db_session.execute(
        update(models.TaskChunk)
        .where(
            models.TaskChunk.id == chunk.id,
            models.TaskChunk.status == "pending",
            models.TaskChunk.version == s2_ver
        )
        .values(status="assigned", version=s2_ver + 1)
    ).rowcount
    db_session.commit()
    
    assert rows_s1 == 1, "Scheduler 1 should successfully acquire chunk"
    assert rows_s2 == 0, "Scheduler 2 should lose optimistic lock race"


def test_atomic_cas_result_acceptance(db_session):
    """Verifies Invariant 1: Exactly-one attempt is accepted via database-level atomic CAS."""
    chunk = models.TaskChunk(chunk_index=0, status="running", version=1)
    db_session.add(chunk)
    db_session.commit()
    
    attempt_1 = "ATT-0001-01"
    attempt_2 = "ATT-0001-S01"  # Speculative duplicate
    
    # Worker 1 completes and attempts CAS acceptance
    rows_1 = db_session.execute(
        update(models.TaskChunk)
        .where(
            models.TaskChunk.id == chunk.id,
            models.TaskChunk.accepted_attempt_id.is_(None)
        )
        .values(
            accepted_attempt_id=attempt_1,
            status="completed",
            version=models.TaskChunk.version + 1
        )
    ).rowcount
    db_session.commit()
    
    # Worker 2 (speculative) completes slightly later and attempts CAS acceptance
    rows_2 = db_session.execute(
        update(models.TaskChunk)
        .where(
            models.TaskChunk.id == chunk.id,
            models.TaskChunk.accepted_attempt_id.is_(None)
        )
        .values(
            accepted_attempt_id=attempt_2,
            status="completed",
            version=models.TaskChunk.version + 1
        )
    ).rowcount
    db_session.commit()
    
    assert rows_1 == 1, "First attempt should win CAS"
    assert rows_2 == 0, "Second late/duplicate attempt MUST lose CAS"
    
    db_session.refresh(chunk)
    assert chunk.accepted_attempt_id == attempt_1
    assert chunk.status == "completed"
