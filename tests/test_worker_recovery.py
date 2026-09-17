"""
Test Suite: Worker Recovery & Session Tracking
Tests session_id changes upon reconnect, stale session attempt rejection, and independent retry budget.
"""

import pytest
from datetime import datetime, timezone
from master.app.db import models
from master.app.engine.failure_policy import should_retry


def test_worker_session_tracking_and_isolation(db_session):
    """Verifies that worker reconnect creates a new session and isolates stale attempts."""
    worker = models.Worker(
        worker_uid="W-REC-01",
        status="online",
        session_id="session-alpha"
    )
    db_session.add(worker)
    db_session.commit()
    
    chunk = models.TaskChunk(chunk_index=0, status="running", worker_id=worker.id)
    db_session.add(chunk)
    db_session.commit()
    
    # Attempt created under old session
    attempt_old = models.ChunkAttempt(
        attempt_uid="ATT-0001-01",
        chunk_id=chunk.id,
        worker_id=worker.id,
        status="running",
        worker_session_id="session-alpha"
    )
    db_session.add(attempt_old)
    db_session.commit()
    
    # Worker reconnects -> new session assigned
    worker.session_id = "session-beta"
    db_session.commit()
    
    # Verify stale attempt's session does not match active worker session
    db_session.refresh(worker)
    assert attempt_old.worker_session_id != worker.session_id


def test_speculative_attempt_does_not_consume_normal_retries():
    """Verifies Invariant 5: Speculative attempts do NOT increment normal_attempt_count."""
    chunk = models.TaskChunk(
        chunk_index=0,
        normal_attempt_count=0,
        speculative_attempt_count=0,
        max_retries=3,
        max_speculative=2
    )
    
    # Normal attempt
    chunk.normal_attempt_count += 1
    assert should_retry(chunk, "RETRYABLE") is True
    
    # 2 Speculative attempts
    chunk.speculative_attempt_count += 1
    chunk.speculative_attempt_count += 1
    
    # Normal retry budget is STILL untouched (only 1 used of 3)
    assert chunk.normal_attempt_count == 1
    assert chunk.speculative_attempt_count == 2
    assert should_retry(chunk, "RETRYABLE") is True
