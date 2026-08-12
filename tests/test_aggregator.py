import pytest
from master.app.db import models
from master.app.engine.aggregator import (
    aggregate_prime_results,
    aggregate_matrix_results,
    aggregate_word_count_results,
    aggregate_sorting_results,
    aggregate_image_processing_results,
    aggregate_compression_results,
    try_aggregate_job
)

def test_aggregate_prime_results():
    results = [
        {"result_data": {"primes_found": 3, "primes": [2, 3, 5]}},
        {"result_data": {"primes_found": 2, "primes": [7, 11]}}
    ]
    aggregated = aggregate_prime_results(results)
    assert aggregated["total_primes_found"] == 5
    assert aggregated["sample_primes"] == [2, 3, 5, 7, 11]


def test_aggregate_matrix_results():
    results = [
        {"result_data": {"start_row": 0, "result_rows": [[1, 2], [3, 4]]}},
        {"result_data": {"start_row": 2, "result_rows": [[5, 6]]}}
    ]
    aggregated = aggregate_matrix_results(results)
    assert aggregated["result_matrix"] == [[1, 2], [3, 4], [5, 6]]
    assert aggregated["dimensions"] == "3x2"


def test_aggregate_word_count_results():
    results = [
        {"result_data": {"word_counts": {"hello": 2, "world": 1}, "total_words": 3}},
        {"result_data": {"word_counts": {"hello": 1, "test": 3}, "total_words": 4}}
    ]
    aggregated = aggregate_word_count_results(results)
    assert aggregated["total_words"] == 7
    assert aggregated["unique_words"] == 3
    assert aggregated["full_counts"]["hello"] == 3
    assert aggregated["full_counts"]["test"] == 3
    assert aggregated["full_counts"]["world"] == 1


def test_aggregate_sorting_results():
    results = [
        {"result_data": {"sorted_numbers": [1, 3, 5]}},
        {"result_data": {"sorted_numbers": [2, 4, 6]}}
    ]
    aggregated = aggregate_sorting_results(results)
    assert aggregated["total_elements"] == 6
    assert aggregated["is_sorted"] is True
    assert aggregated["sorted_array"] == [1, 2, 3, 4, 5, 6]


def test_aggregate_image_processing_results():
    results = [
        {"result_data": {"processed_images": [{"id": 1, "pixels": [[[0,0,0]]]}]}},
        {"result_data": {"processed_images": [{"id": 0, "pixels": [[[255,255,255]]]}]}}
    ]
    aggregated = aggregate_image_processing_results(results)
    assert aggregated["total_processed"] == 2
    # Should sort by image id
    assert aggregated["images"][0]["id"] == 0
    assert aggregated["images"][1]["id"] == 1


def test_aggregate_compression_results():
    results = [
        {"chunk_index": 0, "result_data": {"compressed_data": "aaaa", "original_length": 10}},
        {"chunk_index": 1, "result_data": {"compressed_data": "bb", "original_length": 10}}
    ]
    aggregated = aggregate_compression_results(results)
    assert aggregated["total_original_bytes"] == 20
    assert aggregated["total_compressed_bytes"] == 6
    assert aggregated["compression_ratio_savings_percent"] == 70.0


def test_try_aggregate_job_not_found(db_session):
    # If job doesn't exist, should return False
    assert try_aggregate_job(db_session, 9999) is False


def test_try_aggregate_job_pending_chunks(db_session):
    # Job exists, but has pending or running chunks -> should return False and not aggregate
    job = models.Job(name="test_job", job_type="prime_generation", status="pending")
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, type="prime_generation", status="pending")
    db_session.add(task)
    db_session.commit()
    
    chunk = models.TaskChunk(task_id=task.id, chunk_index=0, status="running")
    db_session.add(chunk)
    db_session.commit()
    
    assert try_aggregate_job(db_session, job.id) is False
    assert job.status == "pending"


def test_try_aggregate_job_success(db_session):
    # All chunks completed -> should aggregate and store result, return True
    job = models.Job(name="test_job", job_type="prime_generation", status="running")
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, type="prime_generation", status="running")
    db_session.add(task)
    db_session.commit()
    
    chunk1 = models.TaskChunk(task_id=task.id, chunk_index=0, status="completed")
    chunk2 = models.TaskChunk(task_id=task.id, chunk_index=1, status="completed")
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    # Store results for the chunks
    res1 = models.Result(task_chunk_id=chunk1.id, result_data={"primes_found": 2, "primes": [2, 3]})
    res2 = models.Result(task_chunk_id=chunk2.id, result_data={"primes_found": 1, "primes": [5]})
    db_session.add_all([res1, res2])
    db_session.commit()
    
    assert try_aggregate_job(db_session, job.id) is True
    assert job.status == "completed"
    assert job.aggregated_result["total_primes_found"] == 3
    assert job.aggregated_result["sample_primes"] == [2, 3, 5]


def test_try_aggregate_job_partial_failure(db_session):
    # One completed, one failed chunk -> should aggregate completed ones and mark job status correctly
    job = models.Job(name="test_job", job_type="prime_generation", status="running")
    db_session.add(job)
    db_session.commit()
    
    task = models.Task(job_id=job.id, type="prime_generation", status="running")
    db_session.add(task)
    db_session.commit()
    
    chunk1 = models.TaskChunk(task_id=task.id, chunk_index=0, status="completed")
    chunk2 = models.TaskChunk(task_id=task.id, chunk_index=1, status="failed")
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    
    res1 = models.Result(task_chunk_id=chunk1.id, result_data={"primes_found": 2, "primes": [2, 3]})
    db_session.add(res1)
    db_session.commit()
    
    assert try_aggregate_job(db_session, job.id) is True
    assert job.status == "completed"
    assert job.aggregated_result["total_primes_found"] == 2

