from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from ..db import database, models
from ..schemas import worker as schemas
from ..core.security import validate_worker_key

router = APIRouter()


@router.post("/register", response_model=schemas.WorkerResponse)
def register_worker(worker: schemas.WorkerCreate, db: Session = Depends(database.get_db)):
    """Register or re-register a worker node. Requires a valid API key."""
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
