"""
Result Aggregation Engine.

Collects partial results from completed task chunks, merges them according to
the job type, validates consistency, and stores the final aggregated result.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..db import models
from ..storage.file_store import save_result_file

logger = logging.getLogger(__name__)


def aggregate_prime_results(results: list[dict]) -> dict:
    """Merge prime generation results: sum counts, combine sample primes."""
    total_primes = 0
    sample_primes = []
    for r in results:
        data = r.get("result_data", {})
        if isinstance(data, dict):
            total_primes += data.get("primes_found", 0)
            sample_primes.extend(data.get("primes", [])[:20])
    sample_primes.sort()
    return {
        "total_primes_found": total_primes,
        "sample_primes": sample_primes[:100]
    }


def aggregate_matrix_results(results: list[dict]) -> dict:
    """Merge matrix multiplication results: reassemble rows by start_row index."""
    all_rows = []
    for r in results:
        data = r.get("result_data", {})
        if isinstance(data, dict):
            start_row = data.get("start_row", 0)
            rows = data.get("result_rows", [])
            for i, row in enumerate(rows):
                all_rows.append((start_row + i, row))

    all_rows.sort(key=lambda x: x[0])
    result_matrix = [row for _, row in all_rows]
    return {
        "result_matrix": result_matrix,
        "dimensions": f"{len(result_matrix)}x{len(result_matrix[0]) if result_matrix else 0}"
    }


def aggregate_word_count_results(results: list[dict]) -> dict:
    """Merge word count results: combine all word count dicts (reduce phase)."""
    merged_counts = {}
    total_words = 0
    for r in results:
        data = r.get("result_data", {})
        if isinstance(data, dict):
            counts = data.get("word_counts", {})
            total_words += data.get("total_words", 0)
            for word, count in counts.items():
                merged_counts[word] = merged_counts.get(word, 0) + count

    # Sort by frequency
    top_words = sorted(merged_counts.items(), key=lambda x: x[1], reverse=True)[:50]
    return {
        "total_words": total_words,
        "unique_words": len(merged_counts),
        "top_50_words": dict(top_words),
        "full_counts": merged_counts
    }


def aggregate_generic_results(results: list[dict]) -> dict:
    """Merge generic Python results: collect all results into a list."""
    collected = []
    for r in results:
        collected.append({
            "chunk_index": r.get("chunk_index", -1),
            "result": r.get("result_data")
        })
    collected.sort(key=lambda x: x["chunk_index"])
    return {"results": collected}


def aggregate_sorting_results(results: list[dict]) -> dict:
    """Merge sorting results: combine and sort the lists."""
    import heapq
    sorted_lists = []
    for r in results:
        data = r.get("result_data", {})
        if isinstance(data, dict):
            nums = data.get("sorted_numbers", [])
            sorted_lists.append(nums)
    merged = list(heapq.merge(*sorted_lists))
    return {
        "sorted_array": merged[:100],  # preview first 100
        "total_elements": len(merged),
        "is_sorted": all(merged[i] <= merged[i+1] for i in range(len(merged)-1))
    }


def aggregate_image_processing_results(results: list[dict]) -> dict:
    """Merge image processing results: reassemble images by ID."""
    all_images = []
    for r in results:
        data = r.get("result_data", {})
        if isinstance(data, dict):
            imgs = data.get("processed_images", [])
            all_images.extend(imgs)
    all_images.sort(key=lambda x: x.get("id", 0))
    return {
        "images": all_images,
        "total_processed": len(all_images)
    }


def aggregate_compression_results(results: list[dict]) -> dict:
    """Merge compression results: calculate saving ratio and collect chunk summaries."""
    chunks_info = []
    total_compressed_bytes = 0
    total_original_bytes = 0
    for r in results:
        data = r.get("result_data", {})
        if isinstance(data, dict):
            comp_data = data.get("compressed_data", "")
            orig_len = data.get("original_length", 0)
            comp_len = len(comp_data)
            total_compressed_bytes += comp_len
            total_original_bytes += orig_len
            chunks_info.append({
                "chunk_index": r.get("chunk_index", -1),
                "original_length": orig_len,
                "compressed_length": comp_len
            })
    chunks_info.sort(key=lambda x: x["chunk_index"])
    ratio = round((1 - (total_compressed_bytes / max(total_original_bytes, 1))) * 100, 2)
    return {
        "chunks": chunks_info,
        "total_original_bytes": total_original_bytes,
        "total_compressed_bytes": total_compressed_bytes,
        "compression_ratio_savings_percent": ratio
    }


def try_aggregate_job(db: Session, job_id: int) -> bool:
    """
    Attempt to aggregate results for a job.
    Called when a chunk completes. Checks if all chunks are done.
    Returns True if aggregation was performed.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return False

    # Get all chunks for this job
    tasks = db.query(models.Task).filter(models.Task.job_id == job_id).all()
    task_ids = [t.id for t in tasks]

    if not task_ids:
        return False

    all_chunks = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids)
    ).all()

    completed_chunks = [c for c in all_chunks if c.status == "completed"]
    failed_chunks = [c for c in all_chunks if c.status == "failed"]
    pending_or_running = [c for c in all_chunks if c.status in ("pending", "assigned", "running")]

    # Update counts
    job.completed_tasks = len(completed_chunks)
    job.failed_tasks = len(failed_chunks)

    # If there are still chunks running/pending, don't aggregate yet
    if pending_or_running:
        return False

    # All chunks are terminal (completed or failed). Aggregate now.
    logger.info(f"Aggregating results for job {job_id} ({len(completed_chunks)} completed, {len(failed_chunks)} failed)")

    # Collect results
    results = []
    for chunk in completed_chunks:
        result = db.query(models.Result).filter(models.Result.task_chunk_id == chunk.id).first()
        if result:
            results.append({
                "chunk_index": chunk.chunk_index,
                "result_data": result.result_data
            })

    # Aggregate based on job type
    aggregated = {}
    try:
        if job.job_type == "prime_generation":
            aggregated = aggregate_prime_results(results)
        elif job.job_type == "matrix_multiply":
            aggregated = aggregate_matrix_results(results)
        elif job.job_type == "word_count":
            aggregated = aggregate_word_count_results(results)
        elif job.job_type == "sorting":
            aggregated = aggregate_sorting_results(results)
        elif job.job_type == "image_processing":
            aggregated = aggregate_image_processing_results(results)
        elif job.job_type == "compression":
            aggregated = aggregate_compression_results(results)
        elif job.job_type == "generic_python":
            aggregated = aggregate_generic_results(results)
        else:
            aggregated = aggregate_generic_results(results)
    except Exception as e:
        logger.error(f"Aggregation error for job {job_id}: {e}")
        aggregated = {"error": str(e), "partial_results": [r.get("result_data") for r in results]}

    # Store aggregated result
    job.aggregated_result = aggregated

    # Set final status
    if failed_chunks and not completed_chunks:
        job.status = "failed"
    elif failed_chunks:
        job.status = "completed"  # Partial success
        aggregated["warning"] = f"{len(failed_chunks)} chunks failed"
        job.aggregated_result = aggregated
    else:
        job.status = "completed"

    job.end_time = datetime.now(timezone.utc)

    # Update all tasks to completed
    for task in tasks:
        task.status = job.status

    db.commit()

    # Auto-save result to file storage for download
    try:
        save_result_file(
            job_id=job_id,
            job_name=job.name or f"job_{job_id}",
            job_type=job.job_type or "unknown",
            aggregated_result=aggregated,
            metadata={
                "status": job.status,
                "total_tasks": job.total_tasks,
                "completed_tasks": len(completed_chunks),
                "failed_tasks": len(failed_chunks),
                "end_time": job.end_time.isoformat() if job.end_time else None,
            },
        )
    except Exception as e:
        logger.warning(f"Failed to auto-save result file for job {job_id}: {e}")

    logger.info(f"Job {job_id} aggregation complete. Status: {job.status}")
    return True
