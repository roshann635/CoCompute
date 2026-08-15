from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..db import database, models
from ..schemas import job as schemas
from ..engine.jobs import generate_job_chunks
from ..engine.aggregator import _generate_input_summary
from ..core.security import get_current_user
from ..services.queue_service import queue_service

router = APIRouter()


@router.post("/submit", response_model=schemas.JobResponse)
def submit_job(
    job_in: schemas.JobCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Submit a new job for distributed execution with institutional quota verification."""
    # 1. Enforce Concurrent Job Quota
    active_jobs = db.query(models.Job).filter(
        models.Job.user_id == current_user.id,
        models.Job.status.in_(["pending", "running", "aggregating"])
    ).count()

    max_concurrent = current_user.max_concurrent_jobs or 5
    if active_jobs >= max_concurrent:
        raise HTTPException(
            status_code=429,
            detail=f"Resource quota exceeded: You have {active_jobs} active jobs (max allowed: {max_concurrent})."
        )

    # 2. Enforce GPU Quota
    if job_in.requires_gpu and (current_user.max_gpu_count or 0) <= 0:
        raise HTTPException(
            status_code=403,
            detail="Your user role/quota does not have permission to submit GPU-accelerated jobs."
        )

    # 3. Validate job type (All 11 standard tasks + custom)
    valid_types = [
        "sorting", "matrix_multiply", "statistics", "search",
        "word_count", "image_processing", "prime_generation", "cipher",
        "ml_training", "distributed_inference", "llm_finetune",
        "compression", "generic_python"
    ]
    if job_in.job_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Unsupported job type '{job_in.job_type}'. Valid types: {valid_types}")

    # 4. Generate task chunks via SDK / Generator
    try:
        task_data_list = generate_job_chunks(job_in.job_type, job_in.params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate job chunks: {str(e)}")

    # 5. Generate input summary for dashboard display
    input_summary = _generate_input_summary(job_in.job_type, job_in.params)

    now = datetime.now(timezone.utc)
    strategy = job_in.scheduler_strategy or "capacity_based"
    priority = job_in.priority or current_user.priority or "NORMAL"

    initial_timeline = [
        {
            "timestamp": now.isoformat(),
            "event_type": "JOB_SUBMITTED",
            "message": f"Job '{job_in.name}' submitted by {current_user.username} ({current_user.role})",
            "details": {"job_type": job_in.job_type, "strategy": strategy, "priority": priority}
        },
        {
            "timestamp": now.isoformat(),
            "event_type": "INPUT_VALIDATED",
            "message": f"Input parameters validated: {input_summary.get('description', '')}",
            "details": input_summary
        },
        {
            "timestamp": now.isoformat(),
            "event_type": "CHUNKS_CREATED",
            "message": f"Partitioned workload into {len(task_data_list)} parallel chunk(s)",
            "details": {"total_chunks": len(task_data_list)}
        }
    ]

    # Create Job record
    db_job = models.Job(
        user_id=current_user.id,
        project_id=job_in.project_id,
        name=job_in.name,
        description=job_in.description,
        job_type=job_in.job_type,
        scheduler_strategy=strategy,
        priority=priority,
        status="pending",
        total_tasks=len(task_data_list),
        requires_gpu=job_in.requires_gpu or False,
        min_vram_gb=job_in.min_vram_gb or 0.0,
        params=job_in.params,
        input_summary=input_summary,
        timeline=initial_timeline,
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    db_job.job_uid = f"JOB-{db_job.id:03d}"

    # Create Task record
    db_task = models.Task(
        job_id=db_job.id,
        type=job_in.job_type,
        payload_ref={"description": f"{job_in.job_type} distributed task"},
        status="pending"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # Create TaskChunk records
    for chunk_data in task_data_list:
        chunk_index = chunk_data["chunk_index"]
        chunk_uid = f"CHUNK-{chunk_index + 1:03d}"
        input_ref = f"minio://chunks/{db_job.job_uid}/{chunk_uid}.bin"
        db_chunk = models.TaskChunk(
            task_id=db_task.id,
            chunk_uid=chunk_uid,
            chunk_index=chunk_index,
            data_payload=chunk_data["payload"],
            input_reference=input_ref,
            status="pending"
        )
        db.add(db_chunk)

    db.commit()
    db.refresh(db_job)

    # Enqueue into Redis Priority Queue (GAP 3)
    queue_service.enqueue_job(str(db_job.id), priority=priority, metadata={"job_uid": db_job.job_uid, "user": current_user.username})

    return db_job


@router.get("/", response_model=list[schemas.JobResponse])
def list_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """List all jobs."""
    return db.query(models.Job).order_by(models.Job.submission_time.desc()).offset(skip).limit(limit).all()


@router.get("/{job_id}", response_model=schemas.JobDetailResponse)
def get_job(job_id: int, db: Session = Depends(database.get_db)):
    """Get job details including progress, parameters, and timeline."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/timeline", response_model=schemas.JobTimelineResponse)
def get_job_timeline(job_id: int, db: Session = Depends(database.get_db)):
    """Get chronological event timeline for a job."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return schemas.JobTimelineResponse(
        job_id=job.id,
        job_uid=job.job_uid,
        job_name=job.name,
        status=job.status,
        events=job.timeline or []
    )


@router.get("/{job_id}/result", response_model=schemas.JobResultResponse)
def get_job_result(job_id: int, db: Session = Depends(database.get_db)):
    """Get the aggregated result for a completed job."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tasks = db.query(models.Task).filter(models.Task.job_id == job_id).all()
    task_ids = [t.id for t in tasks]
    total_chunks = db.query(models.TaskChunk).filter(models.TaskChunk.task_id.in_(task_ids)).count() if task_ids else 0
    completed = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids), models.TaskChunk.status == "completed"
    ).count() if task_ids else 0
    failed = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids), models.TaskChunk.status == "failed"
    ).count() if task_ids else 0

    exec_time = None
    if job.start_time and job.end_time:
        exec_time = round((job.end_time - job.start_time).total_seconds(), 3)

    return schemas.JobResultResponse(
        job_id=job.id,
        job_uid=job.job_uid,
        job_name=job.name,
        status=job.status,
        aggregated_result=job.aggregated_result,
        input_summary=job.input_summary,
        result_preview=job.result_preview,
        chunks_completed=completed,
        chunks_failed=failed,
        total_chunks=total_chunks,
        workers_used=job.workers_used or 0,
        total_execution_time_seconds=exec_time,
        checkpoint_location=job.checkpoint_location,
        model_location=job.model_location
    )


@router.get("/{job_id}/provenance", response_model=schemas.JobProvenanceResponse)
def get_job_provenance(job_id: int, db: Session = Depends(database.get_db)):
    """
    Get full chunk-by-chunk provenance for a job.
    Shows which worker executed which chunk, attempt history, and accepted attempts.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    tasks = db.query(models.Task).filter(models.Task.job_id == job_id).all()
    task_ids = [t.id for t in tasks]

    all_chunks = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids)
    ).order_by(models.TaskChunk.chunk_index).all() if task_ids else []

    chunks_data = []
    completed_count = 0
    failed_count = 0

    for chunk in all_chunks:
        worker_uid = None
        if chunk.worker_id:
            worker = db.query(models.Worker).filter(models.Worker.id == chunk.worker_id).first()
            worker_uid = worker.worker_uid if worker else None

        attempts = db.query(models.ChunkAttempt).filter(
            models.ChunkAttempt.chunk_id == chunk.id
        ).order_by(models.ChunkAttempt.attempt_number).all()

        attempts_data = []
        for attempt in attempts:
            attempt_worker = db.query(models.Worker).filter(
                models.Worker.id == attempt.worker_id
            ).first()
            attempts_data.append({
                "attempt_number": attempt.attempt_number,
                "attempt_uid": attempt.attempt_uid,
                "worker_uid": attempt_worker.worker_uid if attempt_worker else None,
                "status": attempt.status,
                "assigned_at": attempt.assigned_at.isoformat() if attempt.assigned_at else None,
                "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
                "duration_seconds": attempt.duration_seconds,
                "failure_reason": attempt.failure_reason,
                "checksum": attempt.checksum,
                "result_summary": attempt.result_summary,
            })

        if chunk.status == "completed":
            completed_count += 1
        elif chunk.status == "failed":
            failed_count += 1

        chunks_data.append(schemas.ChunkProvenanceItem(
            chunk_id=chunk.id,
            chunk_uid=chunk.chunk_uid,
            chunk_index=chunk.chunk_index,
            status=chunk.status,
            worker_uid=worker_uid,
            attempt_count=chunk.attempt_count,
            accepted_attempt_id=chunk.accepted_attempt_id,
            attempts=attempts_data,
        ))

    exec_time = None
    if job.start_time and job.end_time:
        exec_time = round((job.end_time - job.start_time).total_seconds(), 3)

    return schemas.JobProvenanceResponse(
        job_id=job.id,
        job_uid=job.job_uid,
        job_name=job.name,
        job_type=job.job_type,
        status=job.status,
        input_summary=job.input_summary,
        result_preview=job.result_preview,
        workers_used=job.workers_used or 0,
        total_chunks=len(all_chunks),
        completed_chunks=completed_count,
        failed_chunks=failed_count,
        total_execution_time_seconds=exec_time,
        chunks=chunks_data
    )
