import pytest
from shared.sdk import (
    TaskRegistry,
    SortingTask,
    MatrixMultiplyTask,
    StatisticsTask,
    SearchTask,
    PrimeGenerationTask,
    WordCountTask,
    CompressionTask
)
from shared.protocol import compute_checksum, verify_checksum
from master.app.engine.scheduler import filter_available_workers, resource_aware_select
from master.app.db import models


def test_task_registry_discovery():
    tasks = TaskRegistry.list_all()
    types = [t["task_type"] for t in tasks]
    assert "sorting" in types
    assert "matrix_multiply" in types
    assert "statistics" in types
    assert "search" in types
    assert "prime_generation" in types
    assert "word_count" in types
    assert "compression" in types


def test_sorting_task_lifecycle():
    task = TaskRegistry.get("sorting")
    assert task is not None

    # 1. Partition
    chunks = task.partition({"array_size": 100, "seed": 42}, chunks=4)
    assert len(chunks) == 4
    total_elements = sum(len(c["payload"]["numbers"]) for c in chunks)
    assert total_elements == 100

    # 2. Execute
    results = []
    for c in chunks:
        res = task.execute(c["payload"])
        valid, msg = task.validate_partial(res)
        assert valid is True
        results.append({"chunk_index": c["chunk_index"], "result_data": res})

    # 3. Aggregate (K-Way Merge)
    aggregated = task.aggregate(results)
    assert aggregated["total_elements"] == 100
    assert aggregated["is_sorted"] is True

    # 4. Final Validation
    valid, msg = task.validate_final(aggregated, {"array_size": 100})
    assert valid is True


def test_statistics_task_lifecycle():
    task = TaskRegistry.get("statistics")
    assert task is not None

    chunks = task.partition({"array_size": 500, "seed": 42}, chunks=5)
    results = []
    for c in chunks:
        res = task.execute(c["payload"])
        valid, _ = task.validate_partial(res)
        assert valid is True
        results.append({"chunk_index": c["chunk_index"], "result_data": res})

    aggregated = task.aggregate(results)
    assert aggregated["count"] == 500
    assert aggregated["mean"] > 0
    assert aggregated["std_dev"] >= 0
    assert aggregated["min"] <= aggregated["max"]


def test_search_task_lifecycle():
    task = TaskRegistry.get("search")
    assert task is not None

    chunks = task.partition({"array_size": 1000, "target": 999, "seed": 42}, chunks=5)
    results = []
    for c in chunks:
        res = task.execute(c["payload"])
        results.append({"chunk_index": c["chunk_index"], "result_data": res})

    aggregated = task.aggregate(results)
    assert aggregated["target"] == 999
    assert aggregated["found"] is True
    assert aggregated["index"] is not None


def test_checksum_integrity_verification():
    data = {"numbers": [1, 2, 3, 4, 5], "status": "success"}
    chk = compute_checksum(data)
    assert chk.startswith("sha256:")

    # Verify identical data produces matching checksum
    assert verify_checksum(data, chk) is True

    # Verify tampered data fails
    tampered = {"numbers": [1, 2, 3, 4, 6], "status": "success"}
    assert verify_checksum(tampered, chk) is False


def test_gpu_aware_worker_filtering(db_session):
    w_cpu = models.Worker(
        worker_uid="cpu-worker-01",
        hostname="cpu-host",
        cpu_cores=8,
        ram_total=16.0,
        gpu_count=0,
        cuda_available=False,
        status="online"
    )
    w_gpu = models.Worker(
        worker_uid="gpu-worker-01",
        hostname="gpu-host",
        cpu_cores=16,
        ram_total=32.0,
        gpu_count=1,
        gpu_model="RTX 4090",
        vram_total=24.0,
        cuda_available=True,
        status="online"
    )
    db_session.add(w_cpu)
    db_session.add(w_gpu)
    db_session.commit()

    all_workers = [w_cpu, w_gpu]

    # CPU Job: both should be available
    avail_cpu, _ = filter_available_workers(all_workers, db_session, requires_gpu=False)
    assert len(avail_cpu) == 2

    # GPU Job: only GPU worker should be available
    avail_gpu, skipped_gpu = filter_available_workers(all_workers, db_session, requires_gpu=True, min_vram_gb=12.0)
    assert len(avail_gpu) == 1
    assert avail_gpu[0].worker_uid == "gpu-worker-01"
    assert len(skipped_gpu) == 1
