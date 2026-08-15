import pytest
from datetime import datetime, timedelta
from master.app.db import models

# Patch datetime in analytics to return naive UTC datetimes during testing
# to avoid subtraction issues with SQLite's naive datetime results.
class MockDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.utcnow()

import master.app.engine.analytics
master.app.engine.analytics.datetime = MockDatetime

from master.app.engine.analytics import (
    compute_job_speedup,
    get_cluster_throughput,
    get_worker_rankings,
    get_failure_statistics,
    get_scheduler_comparison,
    get_cluster_efficiency,
    detect_sla_breaches,
    get_cluster_alerts,
    get_resource_utilization_history
)

@pytest.fixture
def seed_data(db_session):
    # Create user
    user = models.User(username="testuser", email="test@example.com", password_hash="hash")
    db_session.add(user)
    db_session.commit()
    
    # Create worker (using naive utcnow)
    worker = models.Worker(
        worker_uid="worker_uid_1",
        hostname="node1",
        status="online",
        cpu_cores=4,
        ram_total=8.0,
        reliability_score=0.9,
        total_tasks_completed=10,
        total_tasks_failed=1,
        created_at=datetime.utcnow()
    )
    db_session.add(worker)
    db_session.commit()
    
    return user, worker


def test_compute_job_speedup(db_session, seed_data):
    user, worker = seed_data
    now = datetime.utcnow()
    
    # Create job with 100 seconds wall clock duration
    job = models.Job(
        name="speedup_job",
        job_type="prime_generation",
        status="completed",
        user_id=user.id,
        start_time=now - timedelta(seconds=100),
        end_time=now
    )
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, type="prime_generation", status="completed")
    db_session.add(task)
    db_session.commit()
    
    # Chunk 1: running for 60s
    chunk1 = models.TaskChunk(
        task_id=task.id,
        worker_id=worker.id,
        chunk_index=0,
        status="completed",
        start_time=now - timedelta(seconds=90),
        end_time=now - timedelta(seconds=30)
    )
    # Chunk 2: running for 40s
    chunk2 = models.TaskChunk(
        task_id=task.id,
        worker_id=worker.id,
        chunk_index=1,
        status="completed",
        start_time=now - timedelta(seconds=60),
        end_time=now - timedelta(seconds=20)
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    stats = compute_job_speedup(db_session, job.id)
    # Sequential estimation: 60 + 40 = 100s. Wall clock: 100s. Speedup = 1.0. Efficiency = 1.0.
    assert stats["speedup"] == 1.0
    assert stats["efficiency"] == 1.0
    assert stats["workers_used"] == 1


def test_get_cluster_throughput(db_session, seed_data):
    user, worker = seed_data
    now = datetime.utcnow()
    
    job = models.Job(
        name="throughput_job",
        job_type="sorting",
        status="completed",
        user_id=user.id,
        start_time=now - timedelta(minutes=10),
        end_time=now - timedelta(minutes=5)
    )
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, type="sorting", status="completed", created_at=now - timedelta(minutes=10))
    db_session.add(task)
    db_session.commit()
    
    chunk = models.TaskChunk(
        task_id=task.id,
        worker_id=worker.id,
        chunk_index=0,
        status="completed",
        start_time=now - timedelta(minutes=9),
        end_time=now - timedelta(minutes=6)
    )
    db_session.add(chunk)
    db_session.commit()
    
    stats = get_cluster_throughput(db_session, hours=1)
    assert stats["period_hours"] == 1
    assert stats["jobs_completed"] == 1
    assert stats["chunks_completed"] == 1
    assert stats["jobs_per_hour"] == 1.0


def test_get_worker_rankings(db_session, seed_data):
    user, worker1 = seed_data
    now = datetime.utcnow()
    
    # Create another worker to verify ordering
    worker2 = models.Worker(
        worker_uid="worker_uid_2",
        hostname="node2",
        status="online",
        cpu_cores=2,
        ram_total=4.0,
        reliability_score=0.5,
        total_tasks_completed=2,
        total_tasks_failed=2,
        created_at=now
    )
    db_session.add(worker2)
    db_session.commit()
    
    # Add completed task chunks to both workers to establish average execution time
    task = models.Task(job_id=None, type="generic_python", status="completed")
    db_session.add(task)
    db_session.commit()
    
    # Worker 1: 10s task
    chunk1 = models.TaskChunk(
        task_id=task.id,
        worker_id=worker1.id,
        chunk_index=0,
        status="completed",
        start_time=now - timedelta(seconds=10),
        end_time=now
    )
    # Worker 2: 10s task
    chunk2 = models.TaskChunk(
        task_id=task.id,
        worker_id=worker2.id,
        chunk_index=1,
        status="completed",
        start_time=now - timedelta(seconds=10),
        end_time=now
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    rankings = get_worker_rankings(db_session)
    assert len(rankings) == 2
    # worker1 score = 10 * 10 * 0.9 / 10 = 9.0
    # worker2 score = 2 * 10 * 0.5 / 10 = 1.0
    # worker1 should be first.
    assert rankings[0]["worker_uid"] == "worker_uid_1"
    assert rankings[0]["composite_score"] > rankings[1]["composite_score"]


def test_get_failure_statistics(db_session, seed_data):
    user, worker = seed_data
    
    job = models.Job(name="failing_job", job_type="word_count", status="failed", user_id=user.id)
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, type="word_count", status="failed")
    db_session.add(task)
    db_session.commit()
    
    chunk1 = models.TaskChunk(
        task_id=task.id,
        worker_id=worker.id,
        chunk_index=0,
        status="failed",
        attempt_count=3
    )
    chunk2 = models.TaskChunk(
        task_id=task.id,
        worker_id=worker.id,
        chunk_index=1,
        status="completed",
        attempt_count=1
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    stats = get_failure_statistics(db_session)
    assert stats["total_chunks"] == 2
    assert stats["failed_chunks"] == 1
    assert stats["completed_chunks"] == 1
    assert stats["chunk_failure_rate"] == 50.0
    assert stats["avg_retries_on_failure"] == 3.0


def test_get_scheduler_comparison(db_session, seed_data):
    user, worker = seed_data
    now = datetime.utcnow()
    
    task = models.Task(job_id=None, type="prime_generation", status="completed")
    db_session.add(task)
    db_session.commit()
    
    chunk = models.TaskChunk(
        task_id=task.id,
        worker_id=worker.id,
        chunk_index=0,
        status="completed",
        start_time=now - timedelta(seconds=30),
        end_time=now
    )
    db_session.add(chunk)
    db_session.commit()
    
    decision = models.SchedulerDecision(
        chunk_id=chunk.id,
        worker_id=worker.id,
        algorithm="resource_aware",
        score=78.5,
        decision_reason="Highest weighted score"
    )
    db_session.add(decision)
    db_session.commit()
    
    comparison = get_scheduler_comparison(db_session)
    assert "resource_aware" in comparison
    assert comparison["resource_aware"]["total_assignments"] == 1
    assert comparison["resource_aware"]["avg_score"] == 78.5
    assert comparison["resource_aware"]["avg_execution_time"] == 30.0


def test_get_cluster_efficiency(db_session, seed_data):
    user, worker = seed_data
    
    task = models.Task(job_id=None, type="generic_python", status="completed")
    db_session.add(task)
    db_session.commit()
    
    chunk1 = models.TaskChunk(task_id=task.id, status="completed", chunk_index=0)
    chunk2 = models.TaskChunk(task_id=task.id, status="failed", chunk_index=1)
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    efficiency = get_cluster_efficiency(db_session)
    assert efficiency == 45.0


def test_detect_sla_breaches(db_session, seed_data):
    user, worker = seed_data
    now = datetime.utcnow()
    
    job = models.Job(name="sla_job", job_type="compression", status="running", user_id=user.id)
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, type="compression", status="running")
    db_session.add(task)
    db_session.commit()
    
    chunk = models.TaskChunk(
        task_id=task.id,
        worker_id=worker.id,
        chunk_index=0,
        status="running",
        start_time=now - timedelta(minutes=10)
    )
    db_session.add(chunk)
    db_session.commit()
    
    breaches = detect_sla_breaches(db_session, sla_seconds=300)
    assert len(breaches) == 1
    assert breaches[0]["chunk_id"] == chunk.id
    assert breaches[0]["worker_uid"] == worker.worker_uid
    assert breaches[0]["running_for_seconds"] >= 600.0


def test_get_cluster_alerts(db_session, seed_data):
    user, worker = seed_data
    now = datetime.utcnow()
    
    worker_off = models.Worker(
        worker_uid="offline_worker",
        hostname="offline_node",
        status="offline",
        last_seen=now - timedelta(minutes=2),
        cpu_cores=1,
        ram_total=2.0
    )
    db_session.add(worker_off)
    
    job = models.Job(
        name="failed_job_alert",
        job_type="generic_python",
        status="failed",
        total_tasks=5,
        failed_tasks=3,
        end_time=now - timedelta(minutes=30),
        user_id=user.id
    )
    db_session.add(job)
    db_session.commit()
    
    worker_busy = models.Worker(
        worker_uid="busy_worker",
        hostname="busy_node",
        status="online",
        cpu_utilization=95.0,
        ram_usage=10.0,
        cpu_cores=2,
        ram_total=4.0
    )
    db_session.add(worker_busy)
    db_session.commit()
    
    alerts = get_cluster_alerts(db_session)
    alert_types = [a["type"] for a in alerts]
    assert "worker_disconnected" in alert_types
    assert "job_failed" in alert_types
    assert "high_utilization" in alert_types
    
    severities = [a["severity"] for a in alerts]
    for i in range(len(severities) - 1):
        if severities[i] == "warning":
            assert severities[i+1] != "error"


def test_get_resource_utilization_history(db_session, seed_data):
    user, worker = seed_data
    now = datetime.utcnow()
    
    m1 = models.Metric(
        worker_id=worker.id,
        cpu_usage=20.0,
        ram_usage=30.0,
        disk_usage=40.0,
        network_tx=1.5,
        network_rx=2.5,
        running_tasks=0,
        timestamp=now - timedelta(minutes=10)
    )
    m2 = models.Metric(
        worker_id=worker.id,
        cpu_usage=50.0,
        ram_usage=60.0,
        disk_usage=40.0,
        network_tx=3.0,
        network_rx=4.0,
        running_tasks=1,
        timestamp=now - timedelta(minutes=5)
    )
    db_session.add_all([m1, m2])
    db_session.commit()
    
    history = get_resource_utilization_history(db_session, worker_id=worker.id, hours=1)
    assert len(history) == 2
    assert history[0]["cpu"] == 20.0
    assert history[1]["cpu"] == 50.0
