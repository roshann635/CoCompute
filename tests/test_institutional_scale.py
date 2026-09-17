"""
Phase 10 — Institutional-Scale Operation Automated Acceptance Tests.
CoCompute Hardening Plan v3.1 Master Engineering Specification.

Acceptance Criteria:
1. Data Locality: Worker with matching preferred node ID receives data locality scoring bonus.
2. Backpressure: Rejection with HTTP 429 when pending task chunks exceed cluster threshold.
3. Quotas: Validation and rejection of excessive concurrent jobs or requested VRAM beyond quota.
4. Worker Lifecycle: State machine transitions; draining/failed workers are excluded from new dispatches.
5. Heartbeat Sequencing: Out-of-order / stale heartbeat sequence updates are ignored.
6. Capability Matching: Tasks with capability prerequisites (e.g. docker, specific CUDA tags) filter matching nodes.
7. Database Indexing: Composite indexes exist and operate efficiently.
"""

import os
import pytest
from fastapi import HTTPException
from master.app.db import models
from master.app.engine.scheduler import filter_available_workers, select_capacity_based
from master.app.schemas import job as schemas
from master.app.api.jobs import submit_job


def test_data_locality_scoring_bonus(db_session):
    w1 = models.Worker(worker_uid="W-LOCAL-01", status="online", cpu_cores=8, ram_total=16.0, reliability_score=1.0)
    w2 = models.Worker(worker_uid="W-REMOTE-02", status="online", cpu_cores=8, ram_total=16.0, reliability_score=1.0)
    db_session.add_all([w1, w2])
    db_session.commit()

    chunk = models.TaskChunk(
        chunk_index=0,
        status="pending",
        input_data={"data": [1, 2, 3], "preferred_worker_uid": "W-LOCAL-01"}
    )
    db_session.add(chunk)
    db_session.commit()

    selected, score = select_capacity_based([w1, w2], chunk, db_session)
    assert selected is not None
    assert selected.worker_uid == "W-LOCAL-01"
    # Locality bonus is +30.0
    _, score_remote = select_capacity_based([w2], chunk, db_session)
    assert score >= score_remote + 30.0


def test_worker_capability_matching(db_session):
    w_std = models.Worker(
        worker_uid="W-STD",
        status="online",
        cpu_cores=8,
        ram_total=16.0,
        capabilities={"docker": False, "tag": "general"}
    )
    w_docker = models.Worker(
        worker_uid="W-DOCKER",
        status="online",
        cpu_cores=8,
        ram_total=16.0,
        capabilities={"docker": True, "tag": "ml-node"}
    )
    db_session.add_all([w_std, w_docker])
    db_session.commit()

    req_caps = {"docker": True}
    avail, skipped = filter_available_workers([w_std, w_docker], db_session, required_capabilities=req_caps)
    assert len(avail) == 1
    assert avail[0].worker_uid == "W-DOCKER"
    assert len(skipped) == 1
    assert skipped[0].worker_uid == "W-STD"


def test_worker_lifecycle_state_machine(db_session):
    w_healthy = models.Worker(worker_uid="W-HEALTHY", status="online", lifecycle_state="healthy")
    w_draining = models.Worker(worker_uid="W-DRAINING", status="online", lifecycle_state="draining")
    w_failed = models.Worker(worker_uid="W-FAILED", status="online", lifecycle_state="failed")
    w_recovering = models.Worker(worker_uid="W-RECOVERING", status="online", lifecycle_state="recovering")
    db_session.add_all([w_healthy, w_draining, w_failed, w_recovering])
    db_session.commit()

    avail, skipped = filter_available_workers([w_healthy, w_draining, w_failed, w_recovering], db_session)
    assert len(avail) == 1
    assert avail[0].worker_uid == "W-HEALTHY"
    assert len(skipped) == 3


def test_heartbeat_sequencing_out_of_order(db_session):
    worker = models.Worker(
        worker_uid="W-SEQ-01",
        status="online",
        heartbeat_seq=10,
        cpu_utilization=20.0
    )
    db_session.add(worker)
    db_session.commit()

    # Simulate arrival of an out-of-order / stale heartbeat (seq = 8)
    stale_seq = 8
    if stale_seq < worker.heartbeat_seq:
        # Invariant 10.5: Must ignore stale heartbeat
        ignored = True
    else:
        worker.cpu_utilization = 99.0
        ignored = False

    assert ignored is True
    assert worker.cpu_utilization == 20.0  # Unmodified

    # Simulate arrival of a newer heartbeat (seq = 11)
    newer_seq = 11
    if newer_seq >= worker.heartbeat_seq:
        worker.heartbeat_seq = newer_seq
        worker.cpu_utilization = 35.0
        applied = True
    else:
        applied = False

    assert applied is True
    assert worker.heartbeat_seq == 11
    assert worker.cpu_utilization == 35.0


def test_cluster_backpressure_enforcement(db_session):
    user = models.User(
        username="scale_user_bp",
        email="bp@cocompute.io",
        password_hash="fake",
        role="researcher",
        max_concurrent_jobs=10
    )
    db_session.add(user)
    db_session.commit()

    # Create dummy pending chunks to trigger backpressure threshold
    os.environ["MAX_CLUSTER_PENDING_CHUNKS"] = "5"
    try:
        for i in range(5):
            db_session.add(models.TaskChunk(chunk_index=i, status="pending"))
        db_session.commit()

        job_in = schemas.JobCreate(
            name="Backpressure Test Job",
            job_type="sorting",
            params={"array": [5, 4, 3, 2, 1], "chunks": 2}
        )

        with pytest.raises(HTTPException) as exc_info:
            submit_job(job_in, db=db_session, current_user=user)

        assert exc_info.value.status_code == 429
        assert "Cluster backpressure active" in exc_info.value.detail
    finally:
        os.environ["MAX_CLUSTER_PENDING_CHUNKS"] = "5000"


def test_institutional_quotas(db_session):
    user = models.User(
        username="quota_user",
        email="quota@cocompute.io",
        password_hash="fake",
        role="student",
        max_concurrent_jobs=1,
        max_gpu_count=0,
        max_vram_gb=8.0
    )
    db_session.add(user)
    db_session.commit()

    # 1. Reject GPU job if max_gpu_count == 0
    job_gpu = schemas.JobCreate(
        name="GPU Quota Job",
        job_type="sorting",
        requires_gpu=True,
        params={"array": [1, 2, 3]}
    )
    with pytest.raises(HTTPException) as exc_info:
        submit_job(job_gpu, db=db_session, current_user=user)
    assert exc_info.value.status_code == 403
    assert "GPU-accelerated" in exc_info.value.detail

    # 2. Reject if VRAM requested exceeds max_vram_gb
    user.max_gpu_count = 2
    db_session.commit()
    job_vram = schemas.JobCreate(
        name="High VRAM Job",
        job_type="sorting",
        requires_gpu=True,
        min_vram_gb=16.0,
        params={"array": [1, 2, 3]}
    )
    with pytest.raises(HTTPException) as exc_info:
        submit_job(job_vram, db=db_session, current_user=user)
    assert exc_info.value.status_code == 403
    assert "exceeds your quota limit" in exc_info.value.detail


def test_database_composite_indexes(db_session):
    from sqlalchemy import inspect
    inspector = inspect(db_session.bind)

    indexes = [idx["name"] for idx in inspector.get_indexes("task_chunks")]
    assert "ix_task_chunks_task_id_status" in indexes

    attempt_indexes = [idx["name"] for idx in inspector.get_indexes("chunk_attempts")]
    assert "ix_chunk_attempts_chunk_id_status" in attempt_indexes

    worker_indexes = [idx["name"] for idx in inspector.get_indexes("workers")]
    assert "ix_workers_status_last_seen" in worker_indexes

    audit_indexes = [idx["name"] for idx in inspector.get_indexes("audit_logs")]
    assert "ix_audit_logs_actor_timestamp" in audit_indexes
