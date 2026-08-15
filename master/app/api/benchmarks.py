"""
Benchmarks API — real cluster scalability and scheduler strategy comparison benchmarks.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

from ..db import database, models
from ..engine.benchmarks import run_scalability_benchmark, run_scheduler_comparison_benchmark
from ..core.security import get_current_user

router = APIRouter()


@router.get("/scalability")
async def get_scalability_benchmark(db: Session = Depends(database.get_db)):
    """Retrieve the latest scalability benchmark or run a new one."""
    latest = db.query(models.BenchmarkRun).filter(
        models.BenchmarkRun.benchmark_type == "scalability"
    ).order_by(models.BenchmarkRun.created_at.desc()).first()

    if latest:
        return latest.results
    
    # Run new benchmark
    return await run_scalability_benchmark(db)


@router.post("/scalability/run")
async def execute_scalability_benchmark(
    body: Optional[Dict[str, Any]] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Trigger a new real-cluster scalability benchmark."""
    task_type = body.get("task_type", "sorting") if body else "sorting"
    worker_counts = body.get("worker_counts", [1, 5, 10, 25, 50, 100]) if body else [1, 5, 10, 25, 50, 100]
    return await run_scalability_benchmark(db, worker_counts=worker_counts, task_type=task_type)


@router.get("/schedulers")
async def get_scheduler_benchmark(db: Session = Depends(database.get_db)):
    """Retrieve the latest scheduler comparison benchmark or run a new one."""
    latest = db.query(models.BenchmarkRun).filter(
        models.BenchmarkRun.benchmark_type == "scheduler_comparison"
    ).order_by(models.BenchmarkRun.created_at.desc()).first()

    if latest:
        return latest.results

    return await run_scheduler_comparison_benchmark(db)


@router.post("/schedulers/run")
async def execute_scheduler_benchmark(
    body: Optional[Dict[str, Any]] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Trigger a real scheduler strategy comparison benchmark."""
    task_type = body.get("task_type", "sorting") if body else "sorting"
    return await run_scheduler_comparison_benchmark(db, task_type=task_type)
