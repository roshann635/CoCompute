from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..db import database, models
from ..schemas import job as schemas
from ..engine.jobs import generate_job_chunks
from ..core.security import get_current_user

router = APIRouter()


@router.post("/submit", response_model=schemas.JobResponse)
def submit_job(
    job_in: schemas.JobCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Submit a new job for distributed execution."""
    # Validate job type
    valid_types = ["prime_generation", "matrix_multiply", "word_count", "generic_python"]
    if job_in.job_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Unsupported job type. Valid types: {valid_types}")

    # Generate task chunks
    try:
        task_data_list = generate_job_chunks(job_in.job_type, job_in.params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate job chunks: {str(e)}")

    # Create Job record
    db_job = models.Job(
        user_id=current_user.id,
        name=job_in.name,
        description=job_in.description,
        job_type=job_in.job_type,
        status="pending",
        total_tasks=len(task_data_list),
        params=job_in.params
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

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
        db_chunk = models.TaskChunk(
            task_id=db_task.id,
            chunk_index=chunk_data["chunk_index"],
            data_payload=chunk_data["payload"],
            status="pending"
        )
        db.add(db_chunk)

    db.commit()
    return db_job


@router.get("/", response_model=list[schemas.JobResponse])
def list_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """List all jobs."""
    return db.query(models.Job).order_by(models.Job.submission_time.desc()).offset(skip).limit(limit).all()


@router.get("/{job_id}", response_model=schemas.JobDetailResponse)
def get_job(job_id: int, db: Session = Depends(database.get_db)):
    """Get job details including progress and parameters."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/result", response_model=schemas.JobResultResponse)
def get_job_result(job_id: int, db: Session = Depends(database.get_db)):
    """Get the aggregated result for a completed job."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get chunk stats
    tasks = db.query(models.Task).filter(models.Task.job_id == job_id).all()
    task_ids = [t.id for t in tasks]
    total_chunks = db.query(models.TaskChunk).filter(models.TaskChunk.task_id.in_(task_ids)).count() if task_ids else 0
    completed = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids), models.TaskChunk.status == "completed"
    ).count() if task_ids else 0
    failed = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids), models.TaskChunk.status == "failed"
    ).count() if task_ids else 0

    # Total execution time
    exec_time = None
    if job.start_time and job.end_time:
        exec_time = round((job.end_time - job.start_time).total_seconds(), 3)

    return schemas.JobResultResponse(
        job_id=job.id,
        job_name=job.name,
        status=job.status,
        aggregated_result=job.aggregated_result,
        chunks_completed=completed,
        chunks_failed=failed,
        total_chunks=total_chunks,
        total_execution_time_seconds=exec_time
    )
