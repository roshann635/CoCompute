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
        db_worker.cpu_model = worker.cpu_model
        db_worker.cpu_frequency = worker.cpu_frequency
        db_worker.mac_address = worker.mac_address
        db_worker.agent_version = worker.agent_version
        db_worker.python_version = worker.python_version
        # GPU Specs
        db_worker.gpu_count = worker.gpu_count or 0
        db_worker.gpu_model = worker.gpu_model
        db_worker.vram_total = worker.vram_total or 0.0
        db_worker.cuda_available = worker.cuda_available or False
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
            cpu_model=worker.cpu_model,
            cpu_frequency=worker.cpu_frequency,
            mac_address=worker.mac_address,
            agent_version=worker.agent_version,
            python_version=worker.python_version,
            gpu_count=worker.gpu_count or 0,
            gpu_model=worker.gpu_model,
            vram_total=worker.vram_total or 0.0,
            cuda_available=worker.cuda_available or False,
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


@router.get("/trust/pending")
def get_pending_workers(db: Session = Depends(database.get_db)):
    """List workers awaiting enrollment approval."""
    pending = db.query(models.Worker).filter(models.Worker.trust_status == "pending").all()
    return [
        {
            "worker_uid": w.worker_uid,
            "hostname": w.hostname,
            "ip_address": w.ip_address,
            "cpu_model": w.cpu_model,
            "cpu_cores": w.cpu_cores,
            "ram_total": w.ram_total,
            "gpu_model": w.gpu_model,
            "trust_status": w.trust_status,
            "enrolled_at": w.enrolled_at.isoformat() if w.enrolled_at else None
        }
        for w in pending
    ]


@router.post("/{worker_uid}/approve")
def approve_worker(worker_uid: str, db: Session = Depends(database.get_db)):
    """Approve a worker for cluster task execution."""
    worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.trust_status = "trusted"
    worker.lifecycle_state = "healthy"
    db.commit()
    return {"worker_uid": worker_uid, "trust_status": "trusted", "message": f"Worker {worker_uid} approved successfully."}


@router.post("/{worker_uid}/reject")
def reject_worker(worker_uid: str, db: Session = Depends(database.get_db)):
    """Reject a worker from receiving cluster tasks."""
    worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.trust_status = "rejected"
    db.commit()
    return {"worker_uid": worker_uid, "trust_status": "rejected", "message": f"Worker {worker_uid} enrollment rejected."}

