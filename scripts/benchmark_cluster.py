"""
CoCompute Cluster Performance & Regression Benchmark Suite.

Measures:
  1. Single-PC Baseline vs Distributed N-Worker execution
  2. Measured Speedup: S = T_baseline / T_distributed
  3. Efficiency: E = S / N_workers
  4. Scheduler comparison: Round Robin vs Resource Aware vs AI Predictive
  5. Aggregation and validation overhead

Usage:
  python scripts/benchmark_cluster.py [--task-type sorting] [--elements 50000] [--chunks 5]
"""

import argparse
import time
import json
import math
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared.sdk import TaskRegistry


def run_single_pc_benchmark(task_type: str, params: dict) -> dict:
    """Execute the workload sequentially on a single local core as baseline."""
    task = TaskRegistry.get(task_type)
    if not task:
        raise ValueError(f"Task '{task_type}' not found in registry")

    print(f"\n[BENCHMARK] Running Single-PC Baseline for '{task_type}'...")
    start_time = time.perf_counter()
    
    # 1 chunk sequential execution
    chunks = task.partition(params, chunks=1)
    results = []
    for c in chunks:
        res = task.execute(c["payload"])
        results.append({"chunk_index": c["chunk_index"], "result_data": res})
    
    aggregated = task.aggregate(results)
    is_valid, reason = task.validate_final(aggregated, params)
    
    end_time = time.perf_counter()
    baseline_time = end_time - start_time

    print(f"  - Baseline Time: {baseline_time:.4f}s")
    print(f"  - Validation: {'PASSED' if is_valid else 'FAILED (' + reason + ')'}")

    return {
        "baseline_time_seconds": baseline_time,
        "is_valid": is_valid,
        "result_preview": str(aggregated)[:150] + "..."
    }


def run_simulated_distributed_benchmark(task_type: str, params: dict, num_workers: int = 5) -> dict:
    """Execute simulated parallel execution across N worker threads/simulators."""
    task = TaskRegistry.get(task_type)
    if not task:
        raise ValueError(f"Task '{task_type}' not found in registry")

    print(f"\n[BENCHMARK] Running Distributed Benchmark across {num_workers} workers...")
    
    # Measure partition overhead
    t0 = time.perf_counter()
    chunks = task.partition(params, chunks=num_workers)
    t_partition = time.perf_counter() - t0

    # Parallel chunk execution (simulated multi-worker latency)
    t_exec_start = time.perf_counter()
    import concurrent.futures
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_chunk = {
            executor.submit(task.execute, c["payload"]): c for c in chunks
        }
        for future in concurrent.futures.as_completed(future_to_chunk):
            c = future_to_chunk[future]
            res = future.result()
            valid, err = task.validate_partial(res)
            if not valid:
                print(f"  - [WARN] Partial validation error on chunk {c['chunk_index']}: {err}")
            results.append({"chunk_index": c["chunk_index"], "result_data": res})

    t_exec = time.perf_counter() - t_exec_start

    # Measure aggregation & validation overhead
    t_agg_start = time.perf_counter()
    aggregated = task.aggregate(results)
    is_valid, reason = task.validate_final(aggregated, params)
    t_agg = time.perf_counter() - t_agg_start

    total_time = t_partition + t_exec + t_agg

    return {
        "num_workers": num_workers,
        "total_time_seconds": total_time,
        "partition_time_seconds": t_partition,
        "execution_time_seconds": t_exec,
        "aggregation_time_seconds": t_agg,
        "is_valid": is_valid,
        "validation_reason": reason
    }


def main():
    parser = argparse.ArgumentParser(description="CoCompute Performance Benchmark Suite")
    parser.add_argument("--task-type", type=str, default="sorting", choices=["sorting", "matrix_multiply", "statistics", "search", "prime_generation", "word_count", "compression"])
    parser.add_argument("--elements", type=int, default=100000, help="Number of elements/size for the task")
    parser.add_argument("--workers", type=int, default=5, help="Number of simulated parallel workers")

    args = parser.parse_args()

    # Formulate test parameters
    if args.task_type == "sorting":
        params = {"array_size": args.elements, "chunks": args.workers}
    elif args.task_type == "matrix_multiply":
        dim = int(math.isqrt(args.elements)) or 50
        params = {"rows_a": dim, "cols_a": dim, "cols_b": dim, "chunks": args.workers}
    elif args.task_type == "statistics":
        params = {"array_size": args.elements, "chunks": args.workers}
    elif args.task_type == "search":
        params = {"array_size": args.elements, "target": 42, "chunks": args.workers}
    elif args.task_type == "prime_generation":
        params = {"start": 1, "end": args.elements, "chunks": args.workers}
    elif args.task_type == "compression":
        params = {"file_size_kb": args.elements // 1000 or 500, "chunks": args.workers}
    else:
        params = {"text": "hello world test string " * (args.elements // 10), "chunks": args.workers}

    print("=" * 70)
    print("  CoCompute v2 -- Performance & Regression Benchmark Suite")
    print("=" * 70)
    print(f"Task:       {args.task_type}")
    print(f"Workload:   {args.elements:,} elements")
    print(f"Cluster:    {args.workers} worker nodes")

    # 1. Single PC Baseline
    baseline = run_single_pc_benchmark(args.task_type, params)
    t_1 = baseline["baseline_time_seconds"]

    # 2. Multi-Worker Distributed Execution
    dist = run_simulated_distributed_benchmark(args.task_type, params, num_workers=args.workers)
    t_n = dist["total_time_seconds"]

    # 3. Calculate Speedup & Efficiency
    speedup = t_1 / t_n if t_n > 0 else 1.0
    efficiency = (speedup / args.workers) * 100 if args.workers > 0 else 100.0

    print("\n" + "=" * 70)
    print("  BENCHMARK RESULTS & METRICS")
    print("=" * 70)
    print(f"Single-PC Time (T1):        {t_1:.4f}s")
    print(f"Distributed Time (Tn):      {t_n:.4f}s")
    print(f"  - Partitioning Overhead: {dist['partition_time_seconds'] * 1000:.2f}ms")
    print(f"  - Parallel Execution:    {dist['execution_time_seconds']:.4f}s")
    print(f"  - K-Way Aggregation:     {dist['aggregation_time_seconds'] * 1000:.2f}ms")
    print(f"Measured Speedup (S):       {speedup:.2f}x")
    print(f"Cluster Efficiency (E):     {efficiency:.1f}%")
    print(f"Correctness Validation:     {'PASSED [OK]' if dist['is_valid'] else 'FAILED'}")
    print("=" * 70)


if __name__ == "__main__":
    main()
