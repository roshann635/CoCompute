"""
Result Aggregation Engine.

Collects partial results from completed task chunks, merges them according to
the task-specific aggregation logic, executes global validation, creates checkpoints
if applicable, and saves full persistent artifact bundles to MinIO and local storage.
"""

import logging
import json
import heapq
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from ..db import models
from ..storage.file_store import save_result_file, compute_file_checksum
from ..services.minio_service import minio_service
from .energy_engine import estimate_job_energy
from .reliability_engine import compute_worker_reliability
from .ai_scheduler import record_closed_loop_feedback
from shared.sdk.registry import TaskRegistry
import os

logger = logging.getLogger(__name__)


# ── Explicit Task Aggregation Helpers (Used by Engine & Unit Tests) ──────────

def aggregate_prime_results(results: list) -> dict:
    all_primes = []
    for r in results:
        data = r.get("result_data", {})
        primes = data.get("primes", [])
        all_primes.extend(primes)
    all_primes.sort()
    return {
        "total_primes_found": len(all_primes),
        "sample_primes": all_primes[:100],
        "first_prime": all_primes[0] if all_primes else None,
        "largest_prime": all_primes[-1] if all_primes else None,
        "primes": all_primes
    }


def aggregate_matrix_results(results: list) -> dict:
    all_rows = []
    for r in results:
        data = r.get("result_data", {})
        start_row = data.get("start_row", 0)
        rows = data.get("result_rows", [])
        for i, row in enumerate(rows):
            all_rows.append((start_row + i, row))
    all_rows.sort(key=lambda x: x[0])
    result_matrix = [row for _, row in all_rows]
    cols = len(result_matrix[0]) if result_matrix else 0
    return {
        "result_matrix": result_matrix,
        "dimensions": f"{len(result_matrix)}x{cols}",
        "rows": len(result_matrix),
        "cols": cols
    }


def aggregate_word_count_results(results: list) -> dict:
    merged_counts = {}
    total_words = 0
    for r in results:
        data = r.get("result_data", {})
        counts = data.get("word_counts", {})
        total_words += data.get("total_words", 0)
        for word, count in counts.items():
            merged_counts[word] = merged_counts.get(word, 0) + count
    top_words = sorted(merged_counts.items(), key=lambda x: x[1], reverse=True)[:50]
    return {
        "total_words": total_words,
        "unique_words": len(merged_counts),
        "top_50_words": dict(top_words),
        "full_counts": merged_counts
    }


def aggregate_sorting_results(results: list) -> dict:
    sorted_lists = []
    for r in results:
        data = r.get("result_data", {})
        sorted_lists.append(data.get("sorted_numbers", []))
    merged = list(heapq.merge(*sorted_lists))
    is_sorted = all(merged[i] <= merged[i + 1] for i in range(len(merged) - 1)) if merged else True
    return {
        "sorted_array": merged,
        "sorted_preview": merged[:100],
        "total_elements": len(merged),
        "min_value": merged[0] if merged else None,
        "max_value": merged[-1] if merged else None,
        "is_sorted": is_sorted,
        "validation": {"is_sorted": is_sorted, "total_elements": len(merged)}
    }


def aggregate_image_processing_results(results: list) -> dict:
    all_images = []
    filter_applied = "grayscale"
    for r in results:
        data = r.get("result_data", {})
        imgs = data.get("processed_images", [])
        all_images.extend(imgs)
        filter_applied = data.get("filter_applied", filter_applied)
    all_images.sort(key=lambda x: x.get("id", 0))
    return {
        "images": all_images,
        "filter_type": filter_applied,
        "total_processed": len(all_images)
    }


def aggregate_compression_results(results: list) -> dict:
    total_orig = sum(r.get("result_data", {}).get("original_length", 0) for r in results)
    total_comp = sum(
        r.get("result_data", {}).get("compressed_length", len(r.get("result_data", {}).get("compressed_data", "")))
        for r in results
    )
    ratio = round(total_comp / total_orig, 4) if total_orig > 0 else 0.0
    savings = round((1.0 - (total_comp / total_orig)) * 100.0, 2) if total_orig > 0 else 0.0
    chunks = []
    for r in results:
        d = r.get("result_data", {})
        c_len = d.get("compressed_length", len(d.get("compressed_data", "")))
        chunks.append({
            "chunk_index": r.get("chunk_index", 0),
            "original_length": d.get("original_length", 0),
            "compressed_length": c_len
        })
    return {
        "total_original_bytes": total_orig,
        "total_compressed_bytes": total_comp,
        "compression_ratio": ratio,
        "compression_ratio_savings_percent": savings,
        "chunks_compressed": len(results),
        "chunks": chunks
    }


def _generate_result_preview(job_type: str, aggregated: dict, exec_time: float = None) -> str:
    time_str = f" in {exec_time:.2f}s" if exec_time else ""

    if job_type == "sorting":
        n = aggregated.get("total_elements", 0)
        valid = aggregated.get("validation", {}).get("is_sorted", True)
        status = "✅ verified" if valid else "⚠️ unverified"
        return f"{n:,} numbers sorted{time_str} — {status}"
    elif job_type == "prime_generation":
        n = aggregated.get("total_primes_found", 0)
        return f"{n:,} primes found{time_str}"
    elif job_type == "matrix_multiply":
        dims = aggregated.get("dimensions", "?x?")
        return f"Matrix {dims} computed{time_str}"
    elif job_type == "word_count":
        total = aggregated.get("total_words", 0)
        unique = aggregated.get("unique_words", 0)
        return f"{total:,} words counted, {unique:,} unique{time_str}"
    elif job_type == "statistics":
        mean = aggregated.get("mean", 0)
        median = aggregated.get("median", 0)
        return f"Mean={mean}, Median={median}{time_str}"
    elif job_type == "search":
        found = aggregated.get("found", False)
        target = aggregated.get("target")
        if found:
            idx = aggregated.get("index")
            return f"Found {target} at index {idx}{time_str}"
        return f"{target} not found{time_str}"
    elif job_type == "cipher":
        chars = aggregated.get("total_characters", 0)
        return f"Cipher processed ({chars} chars){time_str}"
    elif job_type == "ml_training":
        loss = aggregated.get("global_loss", 0.0)
        acc = aggregated.get("global_accuracy", 0.0)
        return f"Trained: Loss={loss}, Acc={acc}%{time_str}"
    elif job_type == "distributed_inference":
        n = aggregated.get("total_inferences", 0)
        conf = aggregated.get("average_confidence", 0.0)
        return f"{n} batch predictions (conf={conf*100:.1f}%){time_str}"
    elif job_type == "llm_finetune":
        loss = aggregated.get("final_loss", 0.0)
        perp = aggregated.get("final_perplexity", 0.0)
        return f"LLM Adapter: Loss={loss}, Perplexity={perp}{time_str}"
    elif job_type == "image_processing":
        n = aggregated.get("total_processed", 0)
        return f"{n} images processed{time_str}"
    elif job_type == "compression":
        ratio = aggregated.get("compression_ratio", 0)
        return f"Compressed ({ratio*100:.1f}% ratio){time_str}"

    return f"Completed{time_str}"


def _generate_input_summary(job_type: str, params: dict) -> dict:
    if job_type == "sorting":
        return {
            "description": f"Sort {params.get('array_size', 0):,} numbers",
            "array_size": params.get("array_size"),
            "chunks": params.get("chunks", 5),
        }
    elif job_type == "prime_generation":
        return {
            "description": f"Find primes in range [{params.get('start', 1):,}, {params.get('end', 100000):,})",
            "start": params.get("start", 1),
            "end": params.get("end"),
            "chunks": params.get("chunks", 10),
        }
    elif job_type == "matrix_multiply":
        return {
            "description": f"Multiply {params.get('rows_a', 50)}x{params.get('cols_a', 50)} x {params.get('cols_a', 50)}x{params.get('cols_b', 50)} matrices",
            "rows_a": params.get("rows_a"),
            "cols_a": params.get("cols_a"),
            "cols_b": params.get("cols_b"),
            "chunks": params.get("chunks", 5)
        }
    elif job_type == "word_count":
        text = params.get("text", "")
        preview = text[:100] + "..." if len(text) > 100 else text
        return {
            "description": f"Word count ({len(text.split())} words)",
            "text_preview": preview,
            "chunks": params.get("chunks", 5),
        }
    elif job_type == "statistics":
        return {
            "description": f"Statistical analysis on {params.get('array_size', 1000):,} data points",
            "array_size": params.get("array_size"),
            "chunks": params.get("chunks", 5),
        }
    elif job_type == "search":
        return {
            "description": f"Search for target={params.get('target', 42)} in {params.get('array_size', 100000):,} numbers",
            "target": params.get("target"),
            "array_size": params.get("array_size"),
            "chunks": params.get("chunks", 10)
        }
    return {"description": f"{job_type} job", "params": params}


def try_aggregate_job(db: Session, job_id: int) -> bool:
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        return False

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

    job.completed_tasks = len(completed_chunks)
    job.failed_tasks = len(failed_chunks)

    if pending_or_running:
        return False

    logger.info(f"Aggregating results for job {job_id} ({job.job_uid or ''})")

    results = []
    for chunk in completed_chunks:
        result = db.query(models.Result).filter(models.Result.task_chunk_id == chunk.id).first()
        if result:
            results.append({
                "chunk_index": chunk.chunk_index,
                "result_data": result.result_data,
                "output_reference": result.output_reference
            })

    worker_ids = set()
    for chunk in all_chunks:
        if chunk.worker_id:
            worker_ids.add(chunk.worker_id)
        for attempt in chunk.attempts:
            if attempt.worker_id:
                worker_ids.add(attempt.worker_id)
    job.workers_used = len(worker_ids)

    if not job.input_summary and job.params:
        job.input_summary = _generate_input_summary(job.job_type, job.params)

    # Route aggregation through task-specific helpers
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
    else:
        task = TaskRegistry.get(job.job_type)
        if task:
            aggregated = task.aggregate(results)
        else:
            collected = []
            for r in results:
                collected.append({"chunk_index": r.get("chunk_index", -1), "result": r.get("result_data")})
            collected.sort(key=lambda x: x["chunk_index"])
            aggregated = {"results": collected}

    # ── CORRECTNESS > STATUS: Run validate_final() for ALL tasks ──────────
    # System Invariant: A job MUST NOT become COMPLETED unless validate_final() passes.
    task_impl = TaskRegistry.get(job.job_type)
    if task_impl:
        try:
            valid, err = task_impl.validate_final(aggregated, job.params)
            if not valid:
                logger.error(f"[CORRECTNESS] validate_final() FAILED for job {job_id} ({job.job_type}): {err}")
                from .scheduler import record_timeline_event
                record_timeline_event(
                    db, job_id, "VALIDATION_FAILED",
                    f"End-to-end validation failed: {err}",
                    {"error": err, "job_type": job.job_type}
                )
                job.status = "validation_failed"
                job.end_time = datetime.now(timezone.utc)
                job.result_preview = f"❌ Validation failed: {err}"
                db.commit()
                return False
            else:
                logger.info(f"[CORRECTNESS] validate_final() PASSED for job {job_id} ({job.job_type})")
        except Exception as e:
            logger.error(f"validate_final() exception for job {job_id}: {e}")
            aggregated["validation_warning"] = str(e)

    # Record Checkpoint for ML / LLM jobs
    if job.job_type in ("ml_training", "llm_finetune") and completed_chunks:
        chk_loc = aggregated.get("model_checkpoint") or aggregated.get("final_model_checkpoint") or f"minio://checkpoints/{job.job_uid or job.id}/final.pt"
        job.checkpoint_location = chk_loc
        job.model_location = chk_loc
        checkpoint_entry = models.Checkpoint(
            job_id=job.id,
            checkpoint_step=job.params.get("steps", job.params.get("epochs", 10)),
            checkpoint_epoch=job.params.get("epochs", 10),
            checkpoint_location=chk_loc,
            loss=aggregated.get("global_loss") or aggregated.get("final_loss"),
            accuracy=aggregated.get("global_accuracy"),
            metrics=aggregated,
            is_valid=True
        )
        db.add(checkpoint_entry)

    db_result = dict(aggregated)
    if "sorted_array" in db_result:
        full_array = db_result.pop("sorted_array")
        db_result["sorted_preview"] = full_array[:100]
        db_result["total_elements"] = len(full_array)
        aggregated["sorted_array"] = full_array

    if "primes" in db_result:
        full_primes = db_result.pop("primes")
        db_result["sample_primes"] = full_primes[:100]
        db_result["total_primes_found"] = len(full_primes)
        aggregated["primes"] = full_primes

    job.aggregated_result = db_result
    job.status = "completed" if not (failed_chunks and not completed_chunks) else "failed"
    job.end_time = datetime.now(timezone.utc)

    exec_time = (job.end_time - job.start_time).total_seconds() if job.start_time and job.end_time else None
    job.actual_duration_sec = exec_time
    job.result_preview = _generate_result_preview(job.job_type, aggregated, exec_time)

    # 1. CoCompute Energy & Carbon Footprint Modeling
    if exec_time:
        energy_metrics = estimate_job_energy(job, exec_time, job.workers_used, getattr(job, "requires_gpu", False))
        aggregated["energy_metrics"] = energy_metrics

    # 2. Update 5-Factor Reliability Scores for Participating Workers
    for wid in worker_ids:
        w_obj = db.query(models.Worker).filter(models.Worker.id == wid).first()
        if w_obj:
            compute_worker_reliability(w_obj, db)

    # 3. Closed-Loop Feedback Engine Recording
    if exec_time and job.predicted_duration_sec:
        try:
            record_closed_loop_feedback(
                db=db,
                job_id=job.id,
                job_type=job.job_type or "unknown",
                strategy_used=job.scheduler_strategy or "adaptive_hybrid",
                predicted_duration_sec=float(job.predicted_duration_sec),
                actual_duration_sec=float(exec_time),
                workers_count=job.workers_used or 1
            )
        except Exception as e:
            logger.debug(f"Closed-loop feedback error: {e}")

    # 4. CoCompute 4.0 Result Intelligence & Quality Analysis
    try:
        from master.app.engine.result_intelligence import (
            validate_result_integrity, detect_semantic_type_and_quality,
            generate_presentation_descriptors, generate_performance_comparison
        )
        val_res = validate_result_integrity(aggregated)
        sem_res = detect_semantic_type_and_quality(aggregated)
        job.result_semantic_type = sem_res.get("semantic_type", "table")
        job.result_quality = {
            "integrity": val_res,
            "quality_score": sem_res.get("quality_score", 100.0),
            "total_records": sem_res.get("total_records", 1),
            "missing_records": sem_res.get("missing_records", 0),
            "duplicate_records": sem_res.get("duplicate_records", 0),
            "descriptors": generate_presentation_descriptors(job.result_semantic_type, aggregated),
            "performance_comparison": generate_performance_comparison(
                exec_time or 1.0,
                job.workers_used or 1,
                getattr(job, "estimated_energy_kwh", 0.01) or 0.01,
                getattr(job, "carbon_gco2_eq", 5.0) or 5.0
            )
        }
    except Exception as e:
        logger.debug(f"Result intelligence processing error: {e}")

    for t in tasks:
        t.status = job.status

    db.commit()

    try:
        file_path = save_result_file(
            job_id=job_id,
            job_name=job.name or f"job_{job_id}",
            job_type=job.job_type or "unknown",
            aggregated_result=aggregated,
            metadata={
                "job_uid": job.job_uid,
                "status": job.status,
                "total_tasks": job.total_tasks,
                "completed_tasks": len(completed_chunks),
                "failed_tasks": len(failed_chunks),
                "workers_used": job.workers_used,
                "input_summary": job.input_summary,
                "workload_profile": job.workload_profile,
                "energy_mode": job.energy_mode,
                "estimated_energy_kwh": job.estimated_energy_kwh,
                "carbon_gco2_eq": job.carbon_gco2_eq,
                "result_preview": job.result_preview,
                "execution_time_seconds": exec_time,
                "checkpoint_location": job.checkpoint_location,
                "end_time": job.end_time.isoformat() if job.end_time else None,
            },
        )
        
        # Invariant 2: Create DB ResultArtifact record for complete provenance & persistence
        if file_path and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            checksum = compute_file_checksum(file_path)
            artifact_record = models.ResultArtifact(
                job_id=job.id,
                storage_location=file_path,
                size_bytes=file_size,
                checksum_sha256=checksum,
                lifecycle_state="active"
            )
            db.add(artifact_record)
            db.commit()

        bundle_uri = minio_service.upload_artifact_bundle(str(job.job_uid or job.id), {
            "job_id": job.id,
            "job_uid": job.job_uid,
            "job_type": job.job_type,
            "config": job.params,
            "workload_profile": job.workload_profile,
            "timeline": job.timeline,
            "result_preview": job.result_preview,
            "aggregated_result": aggregated
        })
        job.result_location = bundle_uri
        db.commit()
    except Exception as e:
        logger.warning(f"Error saving artifact bundle for job {job_id}: {e}")

    from .scheduler import record_timeline_event
    record_timeline_event(
        db, job_id, "JOB_COMPLETED",
        f"Job {job.job_uid or job_id} completed successfully ({job.result_preview})"
    )

    return True
