"""
Phase 9 — ML / LLM Orchestration Automated Acceptance Tests.
CoCompute Hardening Plan v3.1 Master Engineering Specification.

Acceptance Criteria:
1. DistributedTrainingTask: Loss curve convergence, shard synchronization, checkpoint persistence.
2. DistributedInferenceTask: Ordered prediction merge, average confidence, batch completeness.
3. LLMFineTuningTask: Step logging, perplexity tracking, step checkpoints.
4. GPU-Aware Execution: Worker filtering on CUDA availability and VRAM threshold.
"""

import pytest
from shared.sdk.registry import TaskRegistry, DistributedTrainingTask, DistributedInferenceTask, LLMFineTuningTask
from master.app.engine.scheduler import filter_available_workers, select_gpu_aware
from master.app.db import models


def test_distributed_training_task_lifecycle():
    task = TaskRegistry.get("ml_training")
    assert task is not None
    assert isinstance(task, DistributedTrainingTask)
    assert task.requires_gpu is True
    assert task.min_vram_gb >= 8.0

    # 1. Partition
    input_data = {"model_name": "ResNet-50", "epochs": 5, "batch_size": 32, "dataset_size": 2000}
    chunks = task.partition(input_data, chunks=4)
    assert len(chunks) == 4

    # 2. Execute
    results = []
    for chunk in chunks:
        res = task.execute(chunk["payload"])
        valid, err = task.validate_partial(res)
        assert valid is True, f"Partial validation failed: {err}"
        assert "final_loss" in res
        assert "final_accuracy" in res
        assert "checkpoint_ref" in res
        assert res["checkpoint_ref"].startswith("minio://checkpoints/")
        results.append({"chunk_index": chunk["chunk_index"], "result_data": res})

    # 3. Aggregate
    aggregated = task.aggregate(results)
    assert "global_loss" in aggregated
    assert "global_accuracy" in aggregated
    assert "training_curve" in aggregated
    assert len(aggregated["training_curve"]) == 5
    assert aggregated["shards_synchronized"] == 4
    assert aggregated["model_checkpoint"] == "minio://models/final_model.pt"

    # 4. Validate Final
    valid_final, err_final = task.validate_final(aggregated, input_data)
    assert valid_final is True, f"Final validation failed: {err_final}"


def test_distributed_inference_task_lifecycle():
    task = TaskRegistry.get("distributed_inference")
    assert task is not None
    assert isinstance(task, DistributedInferenceTask)
    assert task.requires_gpu is True

    # 1. Partition
    input_data = {"model": "vit-base-patch16", "batch_count": 60}
    chunks = task.partition(input_data, chunks=3)
    assert len(chunks) == 3

    # 2. Execute
    results = []
    for chunk in chunks:
        res = task.execute(chunk["payload"])
        valid, err = task.validate_partial(res)
        assert valid is True, f"Partial validation failed: {err}"
        assert "predictions" in res
        assert len(res["predictions"]) == 20
        results.append({"chunk_index": chunk["chunk_index"], "result_data": res})

    # 3. Aggregate
    aggregated = task.aggregate(results)
    assert aggregated["total_inferences"] == 60
    assert "average_confidence" in aggregated
    assert len(aggregated["predictions"]) == 60

    # Invariant: Predictions must be sorted by item_id
    item_ids = [p["item_id"] for p in aggregated["predictions"]]
    assert item_ids == list(range(60))

    # 4. Validate Final
    valid_final, err_final = task.validate_final(aggregated, input_data)
    assert valid_final is True, f"Final validation failed: {err_final}"


def test_llm_finetuning_task_lifecycle():
    task = TaskRegistry.get("llm_finetune")
    assert task is not None
    assert isinstance(task, LLMFineTuningTask)
    assert task.requires_gpu is True
    assert task.min_vram_gb >= 16.0

    # 1. Partition
    input_data = {"model_name": "custom-llm-7b", "epochs": 3, "dataset_size": 1000, "steps": 500}
    chunks = task.partition(input_data, chunks=2)
    assert len(chunks) == 2

    # 2. Execute
    results = []
    for chunk in chunks:
        res = task.execute(chunk["payload"])
        valid, err = task.validate_partial(res)
        assert valid is True, f"Partial validation failed: {err}"
        assert "final_loss" in res
        assert "final_perplexity" in res
        assert "checkpoint_location" in res
        assert res["checkpoint_location"].startswith("minio://checkpoints/llm_finetune/")
        results.append({"chunk_index": chunk["chunk_index"], "result_data": res})

    # 3. Aggregate
    aggregated = task.aggregate(results)
    assert "final_loss" in aggregated
    assert "final_perplexity" in aggregated
    assert "training_curve" in aggregated
    assert aggregated["shards_synchronized"] == 2
    assert aggregated["final_model_checkpoint"] == "minio://models/llm_final_adapter.pt"

    # 4. Validate Final
    valid_final, err_final = task.validate_final(aggregated, input_data)
    assert valid_final is True, f"Final validation failed: {err_final}"


def test_gpu_aware_scheduling_and_vram_filtering(db_session):
    w_cpu = models.Worker(
        worker_uid="W-CPU-ONLY",
        status="online",
        cpu_cores=16,
        ram_total=32.0,
        gpu_count=0,
        cuda_available=False,
        vram_total=0.0
    )
    w_gpu_low = models.Worker(
        worker_uid="W-GPU-LOW",
        status="online",
        cpu_cores=8,
        ram_total=16.0,
        gpu_count=1,
        cuda_available=True,
        vram_total=6.0,
        gpu_utilization=10.0
    )
    w_gpu_high = models.Worker(
        worker_uid="W-GPU-HIGH",
        status="online",
        cpu_cores=16,
        ram_total=64.0,
        gpu_count=2,
        cuda_available=True,
        vram_total=24.0,
        gpu_utilization=15.0
    )
    db_session.add_all([w_cpu, w_gpu_low, w_gpu_high])
    db_session.commit()

    all_workers = [w_cpu, w_gpu_low, w_gpu_high]

    # For an ML training task requiring GPU and 8GB VRAM:
    available, skipped = filter_available_workers(all_workers, db_session, requires_gpu=True, min_vram_gb=8.0)
    assert len(available) == 1
    assert available[0].worker_uid == "W-GPU-HIGH"
    assert len(skipped) == 2
