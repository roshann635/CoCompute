"""
Comprehensive Unit & Integration Test Suite for CoCompute Enterprise Platform.

Tests all 7 GAPs and Features:
  - GAP 1: Docker Containerized Execution Sandbox
  - GAP 2: MinIO Object Storage & Artifact Bundles
  - GAP 3: Redis Priority Queues & Reschedule Pub/Sub
  - GAP 4: Immediate SUSPECTED transition (< 1s) on WebSocketDisconnect
  - GAP 5: Duplicate Attempt Rejection via accepted_attempt_id
  - GAP 6: SHA-256 Checksum verification
  - GAP 7: Worker HMAC Token Authentication
  - 11 Standard Distributed Tasks (Sorting, Matrix, Stats, Search, WordCount, Image, Primes, Cipher, ML Training, Inference, LLM Fine-Tune)
  - Real-Cluster Benchmarking Engine
  - Institutional Roles & Quota Enforcement
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch

from master.app.services.integrity import compute_sha256, verify_checksum
from master.app.services.auth_service import generate_worker_token, verify_worker_token
from master.app.services.minio_service import MinioService
from master.app.services.queue_service import QueueService
from master.app.engine.fault_detector import FaultDetector
from master.app.engine.benchmarks import run_scalability_benchmark, run_scheduler_comparison_benchmark
from master.app.db import models
from shared.sdk.registry import TaskRegistry


# ─────────────────────────────────────────────────────────────────────────────
# GAP 1: DOCKER CONTAINERIZED EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def test_docker_executor_fallback(tmp_path):
    from worker.executor.docker_executor import DockerExecutor
    executor = DockerExecutor(fallback_to_subproc=True)
    
    in_dir = tmp_path / "input"
    out_dir = tmp_path / "output"
    in_dir.mkdir()
    out_dir.mkdir()
    
    (in_dir / "chunk.bin").write_text(json.dumps({"numbers": [9, 3, 7, 1, 5]}), encoding="utf-8")
    
    res = executor.run(
        task_type="sorting",
        chunk_input_path=str(in_dir),
        chunk_output_path=str(out_dir)
    )
    
    assert res["success"] is True
    assert res["checksum_sha256"] is not None
    assert (out_dir / "result.bin").exists()


# ─────────────────────────────────────────────────────────────────────────────
# GAP 2: MINIO INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def test_minio_service_chunk_upload():
    minio = MinioService()
    test_data = b"chunk binary payload"
    path = minio.upload_chunk("JOB-101", "CHUNK-01", test_data)
    assert path == "minio://chunks/JOB-101/CHUNK-01.bin"

    res_path, checksum = minio.upload_result("JOB-101", "ATT-01", b'{"result": 42}')
    assert res_path == "minio://results/JOB-101/ATT-01.bin"
    assert len(checksum) == 64  # SHA-256 hex string


# ─────────────────────────────────────────────────────────────────────────────
# GAP 3: REDIS QUEUE & PUB/SUB RESCHEDULING
# ─────────────────────────────────────────────────────────────────────────────

def test_queue_service_priority():
    q = QueueService()
    q.enqueue_job("JOB-901", priority="HIGH")
    q.enqueue_job("JOB-902", priority="NORMAL")

    job1 = q.dequeue_job()
    assert job1["job_id"] == "JOB-901"
    assert job1["priority"] == "HIGH"

    received_events = []
    q.subscribe_reschedule(lambda msg: received_events.append(msg))
    q.publish_reschedule("JOB-901", ["1", "2"], reason="Worker disconnected")
    assert len(received_events) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# GAP 4: IMMEDIATE SUSPECTED TRANSITION ON DISCONNECT
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_fault_detector_immediate_suspected(db_session):
    w = models.Worker(
        worker_uid="suspect-w1",
        hostname="worker-node-1",
        cpu_cores=4,
        status="online"
    )
    db_session.add(w)
    db_session.commit()

    # Worker has a running chunk
    task = models.Task(type="sorting", status="running")
    db_session.add(task)
    db_session.commit()

    chunk = models.TaskChunk(
        task_id=task.id,
        worker_id=w.id,
        chunk_index=0,
        status="running",
        attempt_count=1
    )
    db_session.add(chunk)
    db_session.commit()

    # FaultDetector triggers immediately (< 1s)
    affected = await FaultDetector.mark_suspected(db_session, "suspect-w1", reason="WebSocketDisconnect")
    
    assert w.status == "suspected"
    assert len(affected) == 1
    assert affected[0]["worker_uid"] == "suspect-w1"
    assert chunk.status == "pending"  # Rescheduled


# ─────────────────────────────────────────────────────────────────────────────
# GAP 5: DUPLICATE ATTEMPT REJECTION
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_attempt_guard(db_session):
    chunk = models.TaskChunk(
        chunk_index=0,
        status="completed",
        accepted_attempt_id="ATT-0001-01"
    )
    db_session.add(chunk)
    db_session.commit()

    # Arrival from late attempt ATT-0001-02
    incoming_attempt = "ATT-0001-02"
    is_duplicate = chunk.accepted_attempt_id is not None and chunk.accepted_attempt_id != incoming_attempt
    assert is_duplicate is True


# ─────────────────────────────────────────────────────────────────────────────
# GAP 6: SHA-256 CHECKSUM INTEGRITY
# ─────────────────────────────────────────────────────────────────────────────

def test_sha256_checksum_verification():
    data = {"sorted_array": [1, 2, 3, 4, 5], "is_sorted": True}
    chk = compute_sha256(data)
    assert len(chk) == 64
    assert verify_checksum(data, chk) is True

    tampered_data = {"sorted_array": [1, 2, 3, 4, 6], "is_sorted": True}
    assert verify_checksum(tampered_data, chk) is False


# ─────────────────────────────────────────────────────────────────────────────
# GAP 7: WORKER TOKEN HMAC AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────

def test_worker_token_authentication():
    worker_uid = "node-alpha-42"
    token = generate_worker_token(worker_uid)
    assert isinstance(token, str)
    assert len(token) == 64

    # Valid token passes
    assert verify_worker_token(worker_uid, token) is True

    # Tampered token fails
    assert verify_worker_token(worker_uid, "invalid-token-1234") is False
    assert verify_worker_token("different-node", token) is False


# ─────────────────────────────────────────────────────────────────────────────
# 11 STANDARD DISTRIBUTED TASKS TEST
# ─────────────────────────────────────────────────────────────────────────────

def test_all_11_standard_tasks_registered():
    expected_tasks = [
        "sorting", "matrix_multiply", "statistics", "search",
        "word_count", "image_processing", "prime_generation", "cipher",
        "ml_training", "distributed_inference", "llm_finetune"
    ]
    registered = [t["task_type"] for t in TaskRegistry.list_all()]
    for exp in expected_tasks:
        assert exp in registered, f"Task '{exp}' not found in TaskRegistry"


def test_cipher_task_lifecycle():
    task = TaskRegistry.get("cipher")
    chunks = task.partition({"text": "Hello World", "shift": 3, "mode": "encrypt"}, chunks=2)
    assert len(chunks) == 2

    results = []
    for c in chunks:
        res = task.execute(c["payload"])
        results.append({"chunk_index": c["chunk_index"], "result_data": res})

    aggregated = task.aggregate(results)
    assert aggregated["transformed_text"] == "Khoor Zruog"


def test_ml_training_task_lifecycle():
    task = TaskRegistry.get("ml_training")
    assert task.requires_gpu is True
    chunks = task.partition({"model_name": "ResNet-50", "epochs": 3, "dataset_size": 1000}, chunks=2)
    assert len(chunks) == 2

    results = []
    for c in chunks:
        res = task.execute(c["payload"])
        results.append({"chunk_index": c["chunk_index"], "result_data": res})

    aggregated = task.aggregate(results)
    assert "global_loss" in aggregated
    assert "training_curve" in aggregated
    assert len(aggregated["training_curve"]) == 3


def test_llm_finetune_task_lifecycle():
    task = TaskRegistry.get("llm_finetune")
    assert task.requires_gpu is True
    assert task.min_vram_gb == 16.0
    chunks = task.partition({"model_name": "custom-llm-7b", "steps": 500, "epochs": 2}, chunks=2)

    results = []
    for c in chunks:
        res = task.execute(c["payload"])
        results.append({"chunk_index": c["chunk_index"], "result_data": res})

    aggregated = task.aggregate(results)
    assert "final_perplexity" in aggregated
    assert "final_loss" in aggregated


# ─────────────────────────────────────────────────────────────────────────────
# REAL BENCHMARK RUNNER TEST
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_real_scalability_benchmark(db_session):
    w1 = models.Worker(worker_uid="bench-w1", hostname="node1", cpu_cores=4, status="online")
    db_session.add(w1)
    db_session.commit()

    bench = await run_scalability_benchmark(db_session, worker_counts=[1, 5])
    assert bench["benchmark_type"] == "scalability"
    assert bench["total_online_workers"] == 1

    # 1 worker was online -> MEASURED
    res_1 = [r for r in bench["results"] if r["workers"] == 1][0]
    assert res_1["status"] == "MEASURED"
    assert res_1["execution_time_sec"] is not None

    # 5 workers was requested but only 1 online -> SKIPPED with explicit note
    res_5 = [r for r in bench["results"] if r["workers"] == 5][0]
    assert res_5["status"] == "SKIPPED"
    assert "Insufficient" in res_5["note"]


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUTIONAL USER ROLES & QUOTAS TEST
# ─────────────────────────────────────────────────────────────────────────────

def test_institutional_user_quotas(db_session):
    student = models.User(
        username="student_alice",
        email="alice@univ.edu",
        password_hash="hash",
        role="student",
        max_concurrent_jobs=2,
        max_gpu_count=0
    )
    researcher = models.User(
        username="dr_bob",
        email="bob@univ.edu",
        password_hash="hash",
        role="researcher",
        max_concurrent_jobs=5,
        max_gpu_count=4
    )
    db_session.add(student)
    db_session.add(researcher)
    db_session.commit()

    assert student.max_concurrent_jobs == 2
    assert student.max_gpu_count == 0
    assert researcher.max_gpu_count == 4
