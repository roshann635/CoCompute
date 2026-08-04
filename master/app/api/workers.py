from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..db import database, models
from ..schemas import worker as schemas
from ..core.security import validate_worker_key
from ..engine.analytics import get_resource_utilization_history

router = APIRouter()


@router.post("/register", response_model=schemas.WorkerResponse)
def register_worker(worker: schemas.WorkerCreate, db: Session = Depends(database.get_db)):
    """Register or re-register a worker node. Requires a valid API key (FR-13)."""
    if not validate_worker_key(worker.api_key):
        raise HTTPException(status_code=403, detail="Invalid worker API key")

    db_worker = db.query(models.Worker).filter(
        models.Worker.worker_uid == worker.worker_uid
    ).first()

    if db_worker:
        # Update existing worker
        db_worker.status = "online"
        db_worker.ip_address = worker.ip_address
        db_worker.hostname = worker.hostname
        db_worker.cpu_cores = worker.cpu_cores
        db_worker.ram_total = worker.ram_total
        db_worker.disk_total = worker.disk_total
        db_worker.platform = worker.platform
        db_worker.last_seen = datetime.now(timezone.utc)
    else:
        # Create new worker
        db_worker = models.Worker(
            worker_uid=worker.worker_uid,
            ip_address=worker.ip_address,
            hostname=worker.hostname,
            cpu_cores=worker.cpu_cores,
            ram_total=worker.ram_total,
            disk_total=worker.disk_total,
            platform=worker.platform,
            status="online"
        )
        db.add(db_worker)

    db.commit()
    db.refresh(db_worker)
    return db_worker


@router.get("/", response_model=list[schemas.WorkerResponse])
def get_workers(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """List all registered workers."""
    workers = db.query(models.Worker).offset(skip).limit(limit).all()
    return workers


@router.get("/{worker_uid}", response_model=schemas.WorkerResponse)
def get_worker(worker_uid: str, db: Session = Depends(database.get_db)):
    """Get a specific worker by UID."""
    worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker


@router.get("/{worker_uid}/history")
def get_worker_metric_history(
    worker_uid: str,
    hours: int = 1,
    db: Session = Depends(database.get_db)
):
    """
    FR-11 / FR-10: Get historical resource metrics for a specific worker.
    Powers the per-worker detail modal live charts on the dashboard.
    """
    worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    history = get_resource_utilization_history(db, worker_id=worker.id, hours=max(1, min(hours, 24)))
    return {
        "worker_uid": worker.worker_uid,
        "hostname": worker.hostname,
        "status": worker.status,
        "cpu_cores": worker.cpu_cores,
        "ram_total": worker.ram_total,
        "disk_total": worker.disk_total,
        "platform": worker.platform,
        "reliability_score": worker.reliability_score,
        "total_tasks_completed": worker.total_tasks_completed,
        "total_tasks_failed": worker.total_tasks_failed,
        "history": history
    }


@router.get("/{worker_uid}/tasks")
def get_worker_tasks(
    worker_uid: str,
    limit: int = 50,
    db: Session = Depends(database.get_db)
):
    """
    FR-11: Get the task execution history for a specific worker.
    Returns recent task chunks with their status, duration, and job info.
    """
    worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    chunks = db.query(models.TaskChunk).filter(
        models.TaskChunk.worker_id == worker.id
    ).order_by(models.TaskChunk.start_time.desc()).limit(limit).all()

    task_list = []
    for chunk in chunks:
        exec_time = None
        if chunk.start_time and chunk.end_time:
            exec_time = round((chunk.end_time - chunk.start_time).total_seconds(), 3)

        task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
        job = db.query(models.Job).filter(models.Job.id == task.job_id).first() if task else None

        task_list.append({
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "status": chunk.status,
            "attempt_count": chunk.attempt_count,
            "start_time": chunk.start_time.isoformat() if chunk.start_time else None,
            "end_time": chunk.end_time.isoformat() if chunk.end_time else None,
            "execution_time_seconds": exec_time,
            "job_id": job.id if job else None,
            "job_name": job.name if job else None,
            "job_type": job.job_type if job else None,
        })

    return {"worker_uid": worker_uid, "hostname": worker.hostname, "tasks": task_list}


@router.delete("/{worker_uid}")
def deregister_worker(worker_uid: str, db: Session = Depends(database.get_db)):
    """Gracefully deregister a worker node."""
    worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.status = "offline"
    worker.running_tasks = 0

    # Requeue any tasks assigned to this worker
    orphaned = db.query(models.TaskChunk).filter(
        models.TaskChunk.worker_id == worker.id,
        models.TaskChunk.status.in_(["assigned", "running"])
    ).all()
    for chunk in orphaned:
        chunk.status = "pending"
        chunk.worker_id = None

    db.commit()
    return {"message": f"Worker {worker_uid} deregistered", "requeued_tasks": len(orphaned)}
