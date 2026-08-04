"""
Analytics Engine.

Computes performance metrics for the CoCompute cluster:
  - Speedup: T_sequential / T_parallel
  - Efficiency: Speedup / N_workers
  - Throughput: tasks_completed / time_period
  - Worker reliability: successful / total tasks
  - Failure statistics
  - Worker performance rankings
  - Scheduler comparison data
  - SLA breach detection (FR-15)
  - Cluster alerts aggregation (FR-15)
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..db import models

logger = logging.getLogger(__name__)


def compute_job_speedup(db: Session, job_id: int) -> dict:
    """
    Compute speedup for a single job.
    Speedup = sum(individual chunk durations) / actual wall-clock time
    Efficiency = Speedup / number_of_workers_used
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job or not job.start_time or not job.end_time:
        return {"speedup": 0.0, "efficiency": 0.0, "workers_used": 0}

    wall_clock = (job.end_time - job.start_time).total_seconds()
    if wall_clock <= 0:
        wall_clock = 0.001

    tasks = db.query(models.Task).filter(models.Task.job_id == job_id).all()
    task_ids = [t.id for t in tasks]
    chunks = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids),
        models.TaskChunk.status == "completed"
    ).all()

    sequential_time = 0.0
    worker_ids = set()
    for chunk in chunks:
        if chunk.start_time and chunk.end_time:
            sequential_time += (chunk.end_time - chunk.start_time).total_seconds()
        if chunk.worker_id:
            worker_ids.add(chunk.worker_id)

    num_workers = len(worker_ids) if worker_ids else 1
    speedup = sequential_time / wall_clock if wall_clock > 0 else 0.0
    efficiency = speedup / num_workers if num_workers > 0 else 0.0

    return {
        "job_id": job_id,
        "job_name": job.name,
        "speedup": round(speedup, 3),
        "efficiency": round(efficiency, 3),
        "workers_used": num_workers,
        "wall_clock_seconds": round(wall_clock, 3),
        "sequential_estimate_seconds": round(sequential_time, 3)
    }


def get_cluster_throughput(db: Session, hours: int = 24) -> dict:
    """Compute cluster throughput over the last N hours."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    completed_jobs = db.query(models.Job).filter(
        models.Job.status == "completed",
        models.Job.end_time >= since
    ).count()

    tasks = db.query(models.Task).filter(models.Task.created_at >= since).all()
    task_ids = [t.id for t in tasks]
    completed_chunks = db.query(models.TaskChunk).filter(
        models.TaskChunk.task_id.in_(task_ids) if task_ids else False,
        models.TaskChunk.status == "completed"
    ).count() if task_ids else 0

    return {
        "period_hours": hours,
        "jobs_completed": completed_jobs,
        "chunks_completed": completed_chunks,
        "jobs_per_hour": round(completed_jobs / max(hours, 1), 2),
        "chunks_per_hour": round(completed_chunks / max(hours, 1), 2)
    }


def get_worker_rankings(db: Session) -> list:
    """Rank workers by performance (completed tasks, reliability, speed)."""
    workers = db.query(models.Worker).all()
    rankings = []

    for w in workers:
        chunks = db.query(models.TaskChunk).filter(
            models.TaskChunk.worker_id == w.id,
            models.TaskChunk.status == "completed",
            models.TaskChunk.start_time.isnot(None),
            models.TaskChunk.end_time.isnot(None)
        ).all()

        avg_time = 0.0
        if chunks:
            times = [(c.end_time - c.start_time).total_seconds() for c in chunks]
            avg_time = sum(times) / len(times)

        rankings.append({
            "worker_uid": w.worker_uid,
            "hostname": w.hostname,
            "status": w.status,
            "tasks_completed": w.total_tasks_completed,
            "tasks_failed": w.total_tasks_failed,
            "reliability_score": round(w.reliability_score, 3),
            "avg_execution_seconds": round(avg_time, 3),
            "cpu_cores": w.cpu_cores,
            "ram_total": w.ram_total,
            "composite_score": round(
                (w.total_tasks_completed * 10) * w.reliability_score / max(avg_time, 0.001), 2
            )
        })

    rankings.sort(key=lambda x: x["composite_score"], reverse=True)
    return rankings


def get_failure_statistics(db: Session) -> dict:
    """Compute failure statistics across the cluster."""
    total_chunks = db.query(models.TaskChunk).count()
    failed_chunks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "failed").count()
    completed_chunks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "completed").count()

    total_jobs = db.query(models.Job).count()
    failed_jobs = db.query(models.Job).filter(models.Job.status == "failed").count()

    failed = db.query(models.TaskChunk).filter(models.TaskChunk.status == "failed").all()
    avg_retries = sum(c.attempt_count for c in failed) / max(len(failed), 1)

    return {
        "total_chunks": total_chunks,
        "completed_chunks": completed_chunks,
        "failed_chunks": failed_chunks,
        "chunk_failure_rate": round(failed_chunks / max(total_chunks, 1) * 100, 2),
        "total_jobs": total_jobs,
        "failed_jobs": failed_jobs,
        "avg_retries_on_failure": round(avg_retries, 2)
    }


def get_scheduler_comparison(db: Session) -> dict:
    """
    Compare scheduling algorithms by analyzing SchedulerDecision records.
    """
    decisions = db.query(models.SchedulerDecision).all()

    algo_stats = {}
    for d in decisions:
        algo = d.algorithm
        if algo not in algo_stats:
            algo_stats[algo] = {"count": 0, "total_score": 0.0, "execution_times": []}
        algo_stats[algo]["count"] += 1
        algo_stats[algo]["total_score"] += (d.score or 0.0)

        chunk = db.query(models.TaskChunk).filter(
            models.TaskChunk.id == d.chunk_id,
            models.TaskChunk.status == "completed"
        ).first()
        if chunk and chunk.start_time and chunk.end_time:
            algo_stats[algo]["execution_times"].append(
                (chunk.end_time - chunk.start_time).total_seconds()
            )

    result = {}
    for algo, stats in algo_stats.items():
        exec_times = stats["execution_times"]
        result[algo] = {
            "total_assignments": stats["count"],
            "avg_score": round(stats["total_score"] / max(stats["count"], 1), 3),
            "avg_execution_time": round(sum(exec_times) / max(len(exec_times), 1), 3) if exec_times else None,
            "completed_tasks": len(exec_times)
        }

    return result


def get_cluster_efficiency(db: Session) -> float:
    """
    Compute overall cluster efficiency as a percentage.
    """
    total = db.query(models.TaskChunk).count()
    completed = db.query(models.TaskChunk).filter(models.TaskChunk.status == "completed").count()

    workers = db.query(models.Worker).filter(models.Worker.status == "online").all()
    avg_reliability = sum(w.reliability_score for w in workers) / max(len(workers), 1) if workers else 0.5

    completion_rate = completed / max(total, 1)
    efficiency = completion_rate * avg_reliability * 100

    return round(min(efficiency, 100.0), 1)


def get_resource_utilization_history(db: Session, worker_id: int | None = None, hours: int = 1) -> list:
    """Get historical metrics for charts."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = db.query(models.Metric).filter(models.Metric.timestamp >= since)
    if worker_id:
        query = query.filter(models.Metric.worker_id == worker_id)

    metrics = query.order_by(models.Metric.timestamp.asc()).limit(500).all()

    return [
        {
            "timestamp": m.timestamp.isoformat() if m.timestamp else "",
            "cpu": round(m.cpu_usage, 1) if m.cpu_usage else 0,
            "ram": round(m.ram_usage, 1) if m.ram_usage else 0,
            "disk": round(m.disk_usage, 1) if m.disk_usage else 0,
            "network_tx": round(m.network_tx, 2) if m.network_tx else 0,
            "network_rx": round(m.network_rx, 2) if m.network_rx else 0,
            "worker_id": m.worker_id
        }
        for m in metrics
    ]


# ─────────────────────────────────────────────────────
# FR-15: SLA Breach Detection & Cluster Alerts
# ─────────────────────────────────────────────────────

SLA_BREACH_SECONDS = 300  # 5-minute default SLA per chunk


def detect_sla_breaches(db: Session, sla_seconds: int = SLA_BREACH_SECONDS) -> list:
    """
    FR-15: Detect task chunks that have been running longer than the SLA limit.
    Returns a list of alert dicts for breaching chunks.
    """
    now = datetime.now(timezone.utc)
    breach_threshold = now - timedelta(seconds=sla_seconds)

    breaching = db.query(models.TaskChunk).filter(
        models.TaskChunk.status.in_(["assigned", "running"]),
        models.TaskChunk.start_time.isnot(None),
        models.TaskChunk.start_time < breach_threshold
    ).all()

    results = []
    for chunk in breaching:
        running_for = (now - chunk.start_time).total_seconds() if chunk.start_time else 0
        worker = db.query(models.Worker).filter(models.Worker.id == chunk.worker_id).first()
        task = db.query(models.Task).filter(models.Task.id == chunk.task_id).first()
        job = db.query(models.Job).filter(models.Job.id == task.job_id).first() if task else None

        results.append({
            "type": "sla_breach",
            "severity": "warning",
            "chunk_id": chunk.id,
            "job_id": job.id if job else None,
            "job_name": job.name if job else "Unknown",
            "worker_uid": worker.worker_uid if worker else None,
            "worker_hostname": worker.hostname if worker else "Unknown",
            "running_for_seconds": round(running_for, 1),
            "sla_seconds": sla_seconds,
            "message": (
                f"Chunk #{chunk.id} running {round(running_for)}s "
                f"(SLA: {sla_seconds}s) on '{worker.hostname if worker else 'unknown'}'"
            ),
            "timestamp": now.isoformat()
        })
    return results


def get_cluster_alerts(db: Session) -> list:
    """
    FR-15: Aggregate all active cluster alerts:
      1. Worker disconnections (offline in last 10 min)
      2. Failed jobs (last hour)
      3. SLA-breaching task chunks
      4. High-utilization workers (skipped by FR-14 scheduler)
    Returns alerts sorted by severity: error > warning > info.
    """
    alerts = []
    now = datetime.now(timezone.utc)

    # ── 1: Worker disconnections ──
    recently_threshold = now - timedelta(minutes=10)
    offline_workers = db.query(models.Worker).filter(
        models.Worker.status == "offline",
        models.Worker.last_seen >= recently_threshold
    ).all()

    for w in offline_workers:
        disconnected_ago = (now - w.last_seen).total_seconds() if w.last_seen else 0
        alerts.append({
            "id": f"disconnect_{w.worker_uid}",
            "type": "worker_disconnected",
            "severity": "error",
            "worker_uid": w.worker_uid,
            "worker_hostname": w.hostname,
            "message": f"Worker '{w.hostname or w.worker_uid[:8]}' disconnected {round(disconnected_ago)}s ago",
            "timestamp": w.last_seen.isoformat() if w.last_seen else now.isoformat(),
            "metadata": {
                "cpu_cores": w.cpu_cores,
                "ram_total": w.ram_total,
                "tasks_completed": w.total_tasks_completed
            }
        })

    # ── 2: Failed jobs (last hour) ──
    one_hour_ago = now - timedelta(hours=1)
    failed_jobs = db.query(models.Job).filter(
        models.Job.status == "failed",
        models.Job.end_time >= one_hour_ago
    ).all()

    for job in failed_jobs:
        alerts.append({
            "id": f"job_failed_{job.id}",
            "type": "job_failed",
            "severity": "error",
            "job_id": job.id,
            "job_name": job.name,
            "message": f"Job '{job.name}' (#{job.id}) failed — {job.failed_tasks}/{job.total_tasks} chunks failed",
            "timestamp": job.end_time.isoformat() if job.end_time else now.isoformat(),
            "metadata": {
                "total_tasks": job.total_tasks,
                "failed_tasks": job.failed_tasks,
                "job_type": job.job_type
            }
        })

    # ── 3: SLA breaches ──
    sla_alerts = detect_sla_breaches(db)
    alerts.extend(sla_alerts)

    # ── 4: High-utilization workers ──
    try:
        from ..engine.scheduler import HIGH_UTILIZATION_THRESHOLD, HIGH_RAM_THRESHOLD
        online_workers = db.query(models.Worker).filter(models.Worker.status == "online").all()
        for w in online_workers:
            cpu = w.cpu_utilization or 0.0
            ram = w.ram_usage or 0.0
            if cpu > HIGH_UTILIZATION_THRESHOLD or ram > HIGH_RAM_THRESHOLD:
                alerts.append({
                    "id": f"high_util_{w.worker_uid}",
                    "type": "high_utilization",
                    "severity": "warning",
                    "worker_uid": w.worker_uid,
                    "worker_hostname": w.hostname,
                    "message": (
                        f"Worker '{w.hostname}' overloaded "
                        f"(CPU: {cpu:.0f}%, RAM: {ram:.0f}%) — scheduler bypassing (FR-14)"
                    ),
                    "timestamp": now.isoformat(),
                    "metadata": {"cpu": cpu, "ram": ram}
                })
    except ImportError:
        pass

    severity_order = {"error": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a.get("severity", "info"), 2))
    return alerts
