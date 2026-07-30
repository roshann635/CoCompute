from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..db import database, models
from ..engine.analytics import (
    compute_job_speedup,
    get_cluster_throughput,
    get_worker_rankings,
    get_failure_statistics,
    get_scheduler_comparison,
    get_cluster_efficiency
)

router = APIRouter()


@router.get("/speedup")
def get_speedup_metrics(db: Session = Depends(database.get_db)):
    """Get speedup metrics for all completed jobs."""
    completed_jobs = db.query(models.Job).filter(models.Job.status == "completed").all()
    results = [compute_job_speedup(db, job.id) for job in completed_jobs]
    avg_speedup = sum(r["speedup"] for r in results) / max(len(results), 1)
    avg_efficiency = sum(r["efficiency"] for r in results) / max(len(results), 1)
    return {
        "avg_speedup": round(avg_speedup, 3),
        "avg_efficiency": round(avg_efficiency, 3),
        "per_job": results
    }


@router.get("/efficiency")
def get_efficiency(db: Session = Depends(database.get_db)):
    """Get current cluster efficiency."""
    return {"cluster_efficiency": get_cluster_efficiency(db)}


@router.get("/throughput")
def get_throughput(hours: int = Query(default=24, le=168), db: Session = Depends(database.get_db)):
    """Get cluster throughput over N hours."""
    return get_cluster_throughput(db, hours=hours)


@router.get("/workers/ranking")
def get_rankings(db: Session = Depends(database.get_db)):
    """Get worker performance rankings."""
    return {"rankings": get_worker_rankings(db)}


@router.get("/failures")
def get_failures(db: Session = Depends(database.get_db)):
    """Get failure statistics."""
    return get_failure_statistics(db)


@router.get("/comparison")
def get_comparison(db: Session = Depends(database.get_db)):
    """Compare scheduling algorithms performance."""
    return {"algorithms": get_scheduler_comparison(db)}
