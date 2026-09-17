"""
Test Suite: End-to-End Correctness & Universal Validation
Verifies multiset hash verification, dimension checking, corruption rejection, and Definition of Done.
"""

import pytest
import hashlib
import json
from collections import Counter
from shared.sdk.registry import (
    SortingTask, MatrixMultiplyTask, StatisticsTask, PrimeGenerationTask, TaskRegistry
)
from master.app.db import models


def test_sorting_multiset_hash_verification():
    """Verifies that SortingTask verifies multiset consistency and detects silent element corruption."""
    task = SortingTask()
    inp = {"array_size": 200, "seed": 42}
    chunks = task.partition(inp, chunks=4)
    
    assert len(chunks) == 4
    
    # Simulate partial executions
    partial_results = []
    for c in chunks:
        res = task.execute(c["payload"])
        valid, _ = task.validate_partial(res)
        assert valid is True
        partial_results.append({"chunk_index": c["chunk_index"], "result_data": res})
        
    aggregated = task.aggregate(partial_results)
    
    # 1. Valid result passes validate_final
    valid_final, err = task.validate_final(aggregated, inp)
    assert valid_final is True, f"Expected valid, got error: {err}"
    
    # 2. Corrupted result (element modified) MUST fail validate_final
    corrupted_agg = dict(aggregated)
    corrupted_array = list(corrupted_agg["sorted_array"])
    corrupted_array[0] = corrupted_array[0] + 999999
    corrupted_agg["sorted_array"] = sorted(corrupted_array)
    
    valid_corrupt, err_corrupt = task.validate_final(corrupted_agg, inp)
    assert valid_corrupt is False
    assert "multiset" in err_corrupt.lower() or "verification failed" in err_corrupt.lower()


def test_matrix_multiply_dimension_and_completeness():
    """Verifies MatrixMultiplyTask checks dimensions, row completeness, and reference calculations."""
    task = MatrixMultiplyTask()
    inp = {"rows_a": 4, "cols_a": 4, "cols_b": 4, "seed": 42}
    
    chunks = task.partition(inp, chunks=2)
    assert len(chunks) == 2
    
    partial_results = []
    for c in chunks:
        res = task.execute(c["payload"])
        valid, msg = task.validate_partial(res)
        assert valid is True
        partial_results.append({"chunk_index": c["chunk_index"], "result_data": res})
        
    aggregated = task.aggregate(partial_results)
    
    valid, err = task.validate_final(aggregated, inp)
    assert valid is True, f"Validation error: {err}"
    assert aggregated["rows"] == 4
    assert aggregated["cols"] == 4
    
    # Corrupted matrix result
    bad_agg = {"rows": 3, "cols": 4, "result_matrix": [[1, 2, 3, 4]] * 3}
    valid_bad, err_bad = task.validate_final(bad_agg, inp)
    assert valid_bad is False


def test_statistics_mergeable_summaries():
    """Verifies StatisticsTask merges count, sum, variance and validates final counts."""
    task = StatisticsTask()
    inp = {"array_size": 20, "seed": 42}
    chunks = task.partition(inp, chunks=2)
    
    partial_results = []
    for c in chunks:
        res = task.execute(c["payload"])
        valid, msg = task.validate_partial(res)
        assert valid is True
        partial_results.append({"chunk_index": c["chunk_index"], "result_data": res})
        
    aggregated = task.aggregate(partial_results)
    
    valid, err = task.validate_final(aggregated, inp)
    assert valid is True
    assert aggregated["count"] == 20


def test_prime_generation_validation():
    """Verifies PrimeGenerationTask verifies primality and range bounds."""
    task = PrimeGenerationTask()
    inp = {"start": 1, "end": 50}
    chunks = task.partition(inp, chunks=2)
    
    partial_results = []
    for c in chunks:
        res = task.execute(c["payload"])
        valid, msg = task.validate_partial(res)
        assert valid is True
        partial_results.append({"chunk_index": c["chunk_index"], "result_data": res})
        
    aggregated = task.aggregate(partial_results)
    
    valid, err = task.validate_final(aggregated, inp)
    assert valid is True
    assert 2 in aggregated["primes"]
    assert 47 in aggregated["primes"]
    assert 4 not in aggregated["primes"]
