from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from ..db import database, models
from ..engine.analytics import (
    get_resource_utilization_history,
    get_cluster_efficiency,
    get_failure_statistics
)

router = APIRouter()


@router.get("/cluster")
def get_cluster_metrics(db: Session = Depends(database.get_db)):
    """Real-time cluster overview metrics."""
    total_nodes = db.query(models.Worker).count()
    online_workers = db.query(models.Worker).filter(models.Worker.status == "online").all()
    offline_workers = db.query(models.Worker).filter(models.Worker.status == "offline").count()
    busy_workers = db.query(models.Worker).filter(models.Worker.status == "busy").count()

    active_cores = sum(w.cpu_cores or 0 for w in online_workers)
    aggregated_ram = sum(w.ram_total or 0 for w in online_workers)
    avg_cpu = sum(w.cpu_utilization or 0 for w in online_workers) / max(len(online_workers), 1)
    avg_ram = sum(w.ram_usage or 0 for w in online_workers) / max(len(online_workers), 1)

    # Real efficiency from analytics engine
    efficiency = get_cluster_efficiency(db)

    # Task stats
    running_tasks = db.query(models.TaskChunk).filter(
        models.TaskChunk.status.in_(["assigned", "running"])
    ).count()
    completed_tasks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "completed").count()
    failed_tasks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "failed").count()
    pending_tasks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "pending").count()

    # Job stats
    total_jobs = db.query(models.Job).count()
    running_jobs = db.query(models.Job).filter(models.Job.status == "running").count()
    completed_jobs = db.query(models.Job).filter(models.Job.status == "completed").count()
    failed_jobs = db.query(models.Job).filter(models.Job.status == "failed").count()

    # Real historical data from metrics table
    history = get_resource_utilization_history(db, hours=1)

    return {
        "total_nodes": total_nodes,
        "online_nodes": len(online_workers),
        "offline_nodes": offline_workers,
        "busy_nodes": busy_workers,
        "active_cores": active_cores,
        "aggregated_ram": round(aggregated_ram, 1),
        "avg_cpu_usage": round(avg_cpu, 1),
        "avg_ram_usage": round(avg_ram, 1),
        "efficiency": efficiency,
        "tasks": {
            "running": running_tasks,
            "completed": completed_tasks,
            "failed": failed_tasks,
            "pending": pending_tasks,
            "queue_length": pending_tasks + running_tasks
        },
        "jobs": {
            "total": total_jobs,
            "running": running_jobs,
            "completed": completed_jobs,
            "failed": failed_jobs
        },
        "history": history
    }


@router.get("/workers/{worker_id}/history")
def get_worker_metric_history(
    worker_id: int,
    hours: int = Query(default=1, le=24),
    db: Session = Depends(database.get_db)
):
    """Get historical metrics for a specific worker."""
    worker = db.query(models.Worker).filter(models.Worker.id == worker_id).first()
    if not worker:
        return {"error": "Worker not found"}

    history = get_resource_utilization_history(db, worker_id=worker_id, hours=hours)
    return {
        "worker_uid": worker.worker_uid,
        "hostname": worker.hostname,
        "history": history
    }


@router.get("/realtime")
def get_realtime_metrics():
    """
    Get real-time cluster metrics from Redis cache.
    Falls back to an empty response if Redis is unavailable.
    Sub-millisecond response times when Redis is connected.
    """
    from ..engine.metrics_engine import get_cached_snapshot, get_redis_health

    snapshot = get_cached_snapshot()
    if snapshot:
        return {"source": "redis_cache", "data": snapshot}
    return {"source": "unavailable", "data": None, "message": "No cached snapshot available. Data is served via /cluster endpoint."}


@router.get("/timeseries")
def get_timeseries_metrics(minutes: int = Query(default=60, le=1440)):
    """
    Get time-series cluster metrics (per-minute aggregates) from Redis.
    Returns up to `minutes` worth of historical data points.
    Max: 1440 minutes (24 hours).
    """
    from ..engine.metrics_engine import get_timeseries

    points = get_timeseries(minutes=minutes)
    return {
        "source": "redis_timeseries",
        "period_minutes": minutes,
        "data_points": len(points),
        "timeseries": points,
    }


@router.get("/redis/health")
def get_redis_health_status():
    """Get Redis connection health and status information."""
    from ..engine.metrics_engine import get_redis_health

    return get_redis_health()
