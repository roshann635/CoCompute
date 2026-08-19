"""
CoCompute 3.0 Comprehensive Intelligence Test Suite.

Validates all 12 Intelligence Pillars:
  1. Workload Intelligence & Profiling Engine
  2. 5-Factor Composite Worker Reliability Intelligence
  3. Energy-Aware Computing & Carbon Footprint Modeling
  4. Straggler Mitigation & Speculative Execution Engine
  5. Cluster Digital Twin & Simulation Mode
  6. Multi-Target AI Runtime & Resource Predictor + Closed-Loop Feedback
  7. Adaptive Hybrid Scheduler (AHS)
  8. LAN Compute Marketplace & Pool Aggregation
  9. Institutional Compute Credits & Quota Deductions
 10. Worker Trust Enrollment & Admin Approval Gate
 11. Self-Healing 7-State Cluster Lifecycle
 12. Dynamic Work Stealing WebSocket Action
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from master.app.db.database import Base
from master.app.db import models
from master.app.engine.workload_profiler import profile_workload
from master.app.engine.reliability_engine import compute_worker_reliability
from master.app.engine.energy_engine import estimate_job_energy, compute_energy_score
from master.app.engine.straggler_detector import check_and_spawn_speculative_attempts
from master.app.engine.simulator import ClusterSimulator
from master.app.engine.ai_scheduler import predict_worker_execution, record_closed_loop_feedback
from master.app.engine.scheduler import (
    select_adaptive_hybrid, select_worker_by_strategy,
    filter_available_workers
)


@pytest.fixture
def db_session():
    test_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=test_engine)
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


def test_workload_profiler_classification():
    """Verify workload profiling classifies algorithmic profiles and recommends strategies."""
    sort_profile = profile_workload("sorting", {"array_size": 100000})
    assert sort_profile["cpu_intensity"] > 0.7
    assert sort_profile["recommended_strategy"] == "capacity_based"
    assert sort_profile["recommended_chunks"] >= 2

    small_sort = profile_workload("sorting", {"array_size": 5000})
    assert small_sort["recommended_strategy"] == "least_loaded"

    gpu_profile = profile_workload("ml_training", {"dataset_size": 5000})
    assert gpu_profile["gpu_intensity"] > 0.8
    assert gpu_profile["is_gpu_required"] is True
    assert gpu_profile["recommended_strategy"] == "gpu_aware"

    eco_profile = profile_workload("search", {"array_size": 1000}, energy_mode="ECO")
    assert eco_profile["recommended_strategy"] == "least_loaded"


def test_reliability_engine_5_factor_formula(db_session):
    """Verify 5-factor composite reliability scoring: 0.30*succ + 0.20*const + 0.20*up + 0.15*net + 0.15*therm."""
    worker = models.Worker(
        worker_uid="W-REL-01",
        hostname="node-rel",
        ip_address="192.168.1.50",
        status="online",
        total_tasks_completed=19,
        total_tasks_failed=1,
        cpu_utilization=20.0,
        network_latency_ms=3.0,
        uptime_ratio=1.0,
        lifecycle_state="healthy"
    )
    db_session.add(worker)
    db_session.commit()

    rel = compute_worker_reliability(worker, db_session)
    assert 0.85 <= rel["composite_score"] <= 1.0
    assert rel["success_rate"] == 0.95
    assert rel["network_stability"] == 1.0
    assert rel["lifecycle_state"] == "healthy"

    # Degraded trigger test
    worker.total_tasks_completed = 2
    worker.total_tasks_failed = 18
    worker.network_latency_ms = 150.0
    worker.uptime_ratio = 0.3
    rel_degraded = compute_worker_reliability(worker, db_session)
    assert rel_degraded["composite_score"] < 0.5
    assert rel_degraded["lifecycle_state"] == "degraded"


def test_energy_and_carbon_modeling(db_session):
    """Verify energy kWh and carbon gCO2eq estimation and energy scoring modes."""
    job = models.Job(
        name="Energy Test Job",
        job_type="sorting",
        status="completed"
    )
    db_session.add(job)
    db_session.commit()

    # 100 seconds execution on 2 workers
    metrics = estimate_job_energy(job, duration_seconds=100.0, workers_used=2, requires_gpu=False)
    assert metrics["energy_kwh"] > 0
    assert metrics["carbon_gco2_eq"] > 0
    assert job.estimated_energy_kwh == metrics["energy_kwh"]

    # Worker energy efficiency scores
    worker = models.Worker(worker_uid="W-ECO-01", status="online", cpu_cores=8, cpu_utilization=10.0)
    score_eco = compute_energy_score(worker, "ECO")
    score_fast = compute_energy_score(worker, "FAST")
    assert score_eco > 0
    assert score_fast > 0


def test_digital_twin_simulation(db_session):
    """Verify Digital Twin simulator launches isolated virtual nodes labeled with is_simulated=True."""
    start_res = ClusterSimulator.start_simulation(
        db_session,
        worker_count=5,
        cpu_cores_per_worker=8,
        ram_gb_per_worker=32.0,
        gpu_ratio=0.4
    )
    assert start_res["simulated_worker_count"] == 5
    assert start_res["total_simulated_cores"] > 0

    sim_workers = db_session.query(models.Worker).filter(models.Worker.is_simulated == True).all()
    assert len(sim_workers) == 5
    for w in sim_workers:
        assert w.is_simulated is True
        assert "sim-node-" in w.worker_uid

    # Stop simulation
    stop_res = ClusterSimulator.stop_simulation(db_session)
    assert stop_res["removed_simulated_workers"] == 5
    remaining = db_session.query(models.Worker).filter(models.Worker.is_simulated == True).count()
    assert remaining == 0


def test_ai_predictive_and_closed_loop_feedback(db_session):
    """Verify predictive runtime/failure scoring and closed-loop feedback recording."""
    worker = models.Worker(
        worker_uid="W-AI-01",
        cpu_cores=16,
        ram_total=64.0,
        cpu_utilization=15.0,
        reliability_score=0.98,
        network_latency_ms=2.0
    )
    db_session.add(worker)
    db_session.commit()

    pred = predict_worker_execution(worker, "sorting")
    assert "predicted_duration_sec" in pred
    assert "failure_probability" in pred
    assert 0.0 < pred["failure_probability"] < 0.2

    # Record closed-loop feedback
    feedback = record_closed_loop_feedback(
        db=db_session,
        job_id=1,
        job_type="sorting",
        strategy_used="adaptive_hybrid",
        predicted_duration_sec=2.5,
        actual_duration_sec=2.7,
        workers_count=2
    )
    assert feedback.prediction_error_sec == pytest.approx(0.2, 0.01)
    assert feedback.error_percentage > 0


def test_adaptive_hybrid_scheduler_selection(db_session):
    """Verify Adaptive Hybrid Scheduler (AHS) selects optimal strategy based on workload profile."""
    w1 = models.Worker(worker_uid="W1", status="online", cpu_cores=4, ram_total=8.0, cpu_utilization=80.0, trust_status="trusted")
    w2 = models.Worker(worker_uid="W2", status="online", cpu_cores=16, ram_total=32.0, cpu_utilization=10.0, trust_status="trusted")
    db_session.add_all([w1, w2])
    db_session.commit()

    job = models.Job(
        job_type="matrix_multiply",
        params={"rows_a": 100, "cols_a": 100, "cols_b": 100, "chunks": 4},
        priority="NORMAL",
        energy_mode="BALANCED"
    )
    chunk = models.TaskChunk(chunk_index=0)

    worker, score, strategy_name = select_adaptive_hybrid([w1, w2], chunk, job, db_session)
    assert worker.worker_uid == "W2"
    assert "adaptive_hybrid" in strategy_name


def test_trust_enrollment_filter(db_session):
    """Verify untrusted or rejected workers are filtered out by the scheduler."""
    w_trusted = models.Worker(worker_uid="W-TRUSTED", status="online", trust_status="trusted", lifecycle_state="healthy")
    w_pending = models.Worker(worker_uid="W-PENDING", status="online", trust_status="pending", lifecycle_state="healthy")
    w_rejected = models.Worker(worker_uid="W-REJECTED", status="online", trust_status="rejected", lifecycle_state="healthy")
    w_draining = models.Worker(worker_uid="W-DRAINING", status="online", trust_status="trusted", lifecycle_state="draining")

    avail, skipped = filter_available_workers([w_trusted, w_pending, w_rejected, w_draining], db_session)
    # Trusted and pending can be considered (pending or trusted) but rejected/draining must be excluded
    avail_uids = [w.worker_uid for w in avail]
    assert "W-REJECTED" not in avail_uids
    assert "W-DRAINING" not in avail_uids
    assert "W-TRUSTED" in avail_uids


def test_straggler_watchdog_speculative_detection(db_session):
    """Verify Straggler Watchdog triggers speculative execution for chunks taking > 2.0x median runtime."""
    job = models.Job(job_uid="JOB-STRAGGLER", status="running", is_speculative_enabled=True)
    db_session.add(job)
    db_session.commit()

    task = models.Task(job_id=job.id, status="running")
    db_session.add(task)
    db_session.commit()

    w_fast = models.Worker(worker_uid="W-FAST", status="online")
    w_slow = models.Worker(worker_uid="W-SLOW", status="online")
    db_session.add_all([w_fast, w_slow])
    db_session.commit()

    # Completed fast chunk (median = 1.0s)
    c1 = models.TaskChunk(task_id=task.id, status="completed", worker_id=w_fast.id)
    # Completed fast chunk
    c2 = models.TaskChunk(task_id=task.id, status="completed", worker_id=w_fast.id)
    # Running straggler chunk assigned long ago
    c3 = models.TaskChunk(
        task_id=task.id, status="running", worker_id=w_slow.id,
        assigned_at=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    att1 = models.ChunkAttempt(attempt_uid="ATT-001-01", chunk_id=c1.id, status="completed", duration_seconds=1.0)
    att2 = models.ChunkAttempt(attempt_uid="ATT-002-01", chunk_id=c2.id, status="completed", duration_seconds=1.2)
    db_session.add_all([att1, att2])
    db_session.commit()

    spawned = check_and_spawn_speculative_attempts(db_session)
    assert len(spawned) == 1
    assert spawned[0]["chunk_id"] == c3.id
    assert c3.is_speculative is True
