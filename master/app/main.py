"""
CoCompute Master Node Application.

Implements:
  - REST API routes (Auth, Workers, Jobs, Projects, Metrics, Analytics, Benchmarks, Logs, Alerts, Files)
  - WebSocket worker connections with HMAC token authentication (GAP 7)
  - Immediate SUSPECTED fault detection on WebSocketDisconnect (< 1s) (GAP 4)
  - Result ingestion with Duplicate Attempt Protection & SHA-256 Checksum Verification (GAPs 5 & 6)
  - Live real-time dashboard WebSocket push streaming
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .db.database import engine, Base, get_db
from .db import models
from .api import workers, jobs, metrics, auth, analytics, logs, alerts, files, projects, benchmarks, marketplace, simulation
from .network.ws_manager import manager
from .network.discovery import start_discovery_server
from .engine.scheduler import (
    unified_scheduler_loop, fault_tolerance_loop,
    get_active_algorithm, set_active_algorithm,
    reschedule_worker_chunks
)
from .engine.fault_detector import fault_detector
from .engine.ai_scheduler import periodic_training_loop
from .engine.straggler_detector import straggler_watchdog_loop
from .engine.aggregator import try_aggregate_job
from .engine.analytics import get_cluster_alerts
from .engine.metrics_engine import (
    cache_cluster_snapshot, record_metric_point,
    get_redis_client, update_worker_metrics
)
from .services.auth_service import verify_worker_token
from .services.integrity import verify_checksum
from .services.queue_service import queue_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CoCompute Master Node",
    description="Intelligent Distributed Computing Framework for Dynamic Resource-Aware Task Scheduling",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ──────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(workers.router, prefix="/api/v1/workers", tags=["workers"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(marketplace.router)
app.include_router(marketplace.credits_router)
app.include_router(simulation.router)
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(benchmarks.router, prefix="/api/v1/benchmarks", tags=["benchmarks"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(files.router, prefix="/api/v1/files", tags=["file-storage"])

# ── Dashboard live WebSocket connections ─────────────────────────────────────
_dashboard_connections: dict[str, WebSocket] = {}


async def _broadcast_to_dashboards(payload: dict):
    disconnected = []
    for cid, ws in _dashboard_connections.items():
        try:
            await ws.send_json(payload)
        except Exception:
            disconnected.append(cid)
    for cid in disconnected:
        _dashboard_connections.pop(cid, None)


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("  CoCompute Master Node v2.0 Starting...")
    logger.info("=" * 60)

    # Initialize Redis Metrics Engine & Queues
    redis_client = get_redis_client()
    if redis_client:
        logger.info("Metrics & Queue Engine: Redis connected.")
    else:
        logger.warning("Metrics & Queue Engine: Redis unavailable. Running in local fallback mode.")

    # Start UDP Discovery Server
    discovery_ip = os.getenv("MASTER_DISCOVERY_IP", "0.0.0.0")
    asyncio.create_task(start_discovery_server(discovery_ip, 8000))

    # Start CIE Unified Scheduler
    asyncio.create_task(unified_scheduler_loop())

    # Start Fault Tolerance Monitor
    asyncio.create_task(fault_tolerance_loop())

    # Start periodic AI model training
    asyncio.create_task(periodic_training_loop())

    # Start Straggler Watchdog & Speculative Execution Engine (CoCompute 3.0)
    asyncio.create_task(straggler_watchdog_loop())

    # Start dashboard broadcast loop
    asyncio.create_task(_dashboard_broadcast_loop())

    logger.info("All CoCompute Master background services initialized (including CoCompute 3.0 Intelligence Engines).")


async def _dashboard_broadcast_loop():
    from .engine.analytics import get_cluster_efficiency
    from .db.database import SessionLocal

    while True:
        if _dashboard_connections:
            db = None
            try:
                db = SessionLocal()
                online_workers = db.query(models.Worker).filter(models.Worker.status.in_(["online", "idle"])).all()
                offline_count = db.query(models.Worker).filter(models.Worker.status == "offline").count()
                total_nodes = db.query(models.Worker).count()
                active_cores = sum(w.cpu_cores or 0 for w in online_workers)
                agg_ram = sum(w.ram_total or 0 for w in online_workers)
                avg_cpu = sum(w.cpu_utilization or 0 for w in online_workers) / max(len(online_workers), 1)

                running_chunks = db.query(models.TaskChunk).filter(
                    models.TaskChunk.status.in_(["assigned", "running"])
                ).count()
                completed_chunks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "completed").count()
                failed_chunks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "failed").count()
                pending_chunks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "pending").count()

                active_alerts = get_cluster_alerts(db)

                workers_payload = [
                    {
                        "id": w.id,
                        "worker_uid": w.worker_uid,
                        "hostname": w.hostname,
                        "status": w.status,
                        "cpu_cores": w.cpu_cores,
                        "cpu_utilization": w.cpu_utilization,
                        "ram_total": w.ram_total,
                        "ram_usage": w.ram_usage,
                        "disk_usage": w.disk_usage,
                        "gpu_count": w.gpu_count,
                        "gpu_model": w.gpu_model,
                        "vram_total": w.vram_total,
                        "gpu_utilization": w.gpu_utilization,
                        "running_tasks": w.running_tasks,
                        "reliability_score": w.reliability_score,
                        "platform": w.platform,
                        "last_seen": w.last_seen.isoformat() if w.last_seen else None,
                    }
                    for w in db.query(models.Worker).all()
                ]

                payload = {
                    "type": "CLUSTER_UPDATE",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cluster": {
                        "total_nodes": total_nodes,
                        "online_nodes": len(online_workers),
                        "offline_nodes": offline_count,
                        "active_cores": active_cores,
                        "aggregated_ram": round(agg_ram, 1),
                        "avg_cpu_usage": round(avg_cpu, 1),
                        "efficiency": get_cluster_efficiency(db),
                        "tasks": {
                            "running": running_chunks,
                            "completed": completed_chunks,
                            "failed": failed_chunks,
                            "pending": pending_chunks,
                            "queue_length": pending_chunks + running_chunks,
                        },
                    },
                    "workers": workers_payload,
                    "alerts": active_alerts,
                    "scheduler_algorithm": get_active_algorithm(),
                }
                await _broadcast_to_dashboards(payload)

                cache_cluster_snapshot(payload.get("cluster", {}))
                record_metric_point(payload.get("cluster", {}))
            except Exception as e:
                logger.error(f"Dashboard broadcast error: {e}")
            finally:
                if db:
                    db.close()
        await asyncio.sleep(2.5)


@app.get("/")
def root():
    return {
        "name": "CoCompute Master Node",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


# ── Scheduler Config ─────────────────────────────────────────────────────────
@app.get("/api/v1/scheduler/config")
def get_scheduler_config():
    from .engine.scheduler import HIGH_UTILIZATION_THRESHOLD, HIGH_RAM_THRESHOLD
    return {
        "algorithm": get_active_algorithm(),
        "valid_algorithms": [
            "round_robin", "least_loaded", "capacity_based", "gpu_aware",
            "network_aware", "priority_based", "fair_share", "ai_predictive"
        ],
        "high_utilization_threshold": HIGH_UTILIZATION_THRESHOLD,
        "high_ram_threshold": HIGH_RAM_THRESHOLD,
    }


@app.post("/api/v1/scheduler/config")
def set_scheduler_config(body: dict):
    algorithm = body.get("algorithm")
    if not algorithm:
        raise HTTPException(status_code=400, detail="'algorithm' field is required")
    try:
        set_active_algorithm(algorithm)
        return {"message": f"Scheduler algorithm set to '{algorithm}'", "algorithm": algorithm}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# WORKER WEBSOCKET ENDPOINT (WITH TOKEN AUTH & DISCONNECT SUSPECTED)
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/worker/{worker_uid}")
async def websocket_endpoint(
    websocket: WebSocket,
    worker_uid: str,
    token: Optional[str] = Query(None)
):
    # GAP 7: Worker Token Authentication
    if token and not verify_worker_token(worker_uid, token):
        logger.warning(f"Rejected worker connection {worker_uid}: Invalid worker token")
        await websocket.close(code=4001, reason="Invalid worker token")
        return

    await manager.connect(websocket, worker_uid)
    db: Session = next(get_db())

    db_worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if db_worker:
        db_worker.status = "online"
        db_worker.last_seen = datetime.now(timezone.utc)
        db.commit()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "METRICS":
                m = data.get("data", {})
                db_worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
                if db_worker:
                    db_worker.last_seen = datetime.now(timezone.utc)
                    db_worker.status = "online"
                    db_worker.cpu_utilization = m.get("cpu_usage", 0.0)
                    db_worker.ram_usage = m.get("ram_usage", 0.0)
                    db_worker.disk_usage = m.get("disk_usage", 0.0)
                    db_worker.running_tasks = m.get("running_tasks", 0)
                    db_worker.gpu_utilization = m.get("gpu_utilization", 0.0)
                    db_worker.vram_usage = m.get("vram_usage", 0.0)
                    db_worker.gpu_temperature = m.get("gpu_temperature")

                    update_worker_metrics(worker_uid, m)

                    new_metric = models.Metric(
                        worker_id=db_worker.id,
                        cpu_usage=m.get("cpu_usage"),
                        ram_usage=m.get("ram_usage"),
                        disk_usage=m.get("disk_usage"),
                        network_tx=m.get("network_tx"),
                        network_rx=m.get("network_rx"),
                        running_tasks=m.get("running_tasks", 0),
                        gpu_utilization=m.get("gpu_utilization"),
                        vram_usage=m.get("vram_usage"),
                        gpu_temperature=m.get("gpu_temperature")
                    )
                    db.add(new_metric)
                    db.commit()

            elif data.get("type") == "RESULT":
                chunk_id = data.get("chunk_id")
                attempt_id = data.get("attempt_id")
                result_data = data.get("result_data", {})
                checksum = data.get("checksum")

                db_chunk = db.query(models.TaskChunk).filter(models.TaskChunk.id == chunk_id).first()
                if not db_chunk:
                    continue

                # GAP 5: Duplicate Attempt Rejection
                if db_chunk.accepted_attempt_id is not None and (attempt_id and db_chunk.accepted_attempt_id != attempt_id):
                    logger.info(f"[DuplicateGuard] Late result from attempt {attempt_id} for chunk {chunk_id} discarded. Accepted: {db_chunk.accepted_attempt_id}")
                    continue

                if db_chunk.status == "completed":
                    logger.info(f"[DuplicateGuard] Chunk {chunk_id} already COMPLETED — ignoring late result.")
                    continue

                # Stale worker protection
                db_worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
                if not db_worker or db_chunk.worker_id != db_worker.id:
                    logger.warning(f"[DuplicateGuard] Ignored result for chunk {chunk_id} from unassigned worker {worker_uid}")
                    continue

                # GAP 6: Standalone SHA-256 Checksum Verification
                raw_result = result_data.get("result")
                if checksum and not verify_checksum(raw_result, checksum):
                    logger.error(f"[Integrity] Checksum mismatch for chunk {chunk_id} from {worker_uid}. Rescheduling.")
                    rescheduled = reschedule_worker_chunks(db, db_worker, reason="checksum_mismatch")
                    if rescheduled:
                        queue_service.publish_reschedule(str(db_chunk.task_id), [str(db_chunk.id)], "checksum_mismatch")
                    db.commit()
                    continue

                now = datetime.now(timezone.utc)
                status_str = result_data.get("status", "success")
                exec_time = None
                if db_chunk.start_time:
                    exec_time = (now - db_chunk.start_time).total_seconds()

                db_chunk.end_time = now
                db_chunk.checksum = checksum

                if status_str == "success":
                    db_chunk.status = "completed"
                    # Mark accepted attempt (GAP 5)
                    db_chunk.accepted_attempt_id = attempt_id or f"ATT-{chunk_id}-{db_chunk.attempt_count}"
                else:
                    db_chunk.status = "failed"

                # Update ChunkAttempt
                current_attempt = db.query(models.ChunkAttempt).filter(
                    models.ChunkAttempt.chunk_id == chunk_id,
                    models.ChunkAttempt.worker_id == db_worker.id
                ).order_by(models.ChunkAttempt.attempt_number.desc()).first()

                if current_attempt:
                    current_attempt.status = "completed" if status_str == "success" else "failed"
                    current_attempt.completed_at = now
                    current_attempt.duration_seconds = exec_time
                    current_attempt.checksum = checksum
                    if status_str != "success":
                        current_attempt.failure_reason = result_data.get("error", "execution_error")
                    else:
                        summary = json.dumps(raw_result)[:500] if raw_result is not None else "success"
                        current_attempt.result_summary = summary

                # Save Result
                existing_res = db.query(models.Result).filter(models.Result.task_chunk_id == chunk_id).first()
                if existing_res:
                    existing_res.result_data = raw_result
                    existing_res.checksum = checksum
                    existing_res.execution_time_seconds = exec_time
                else:
                    db.add(models.Result(
                        task_chunk_id=chunk_id,
                        result_data=raw_result,
                        checksum=checksum,
                        execution_time_seconds=exec_time
                    ))

                if db_worker:
                    if status_str == "success":
                        db_worker.total_tasks_completed += 1
                    else:
                        db_worker.total_tasks_failed += 1
                    tot = db_worker.total_tasks_completed + db_worker.total_tasks_failed
                    db_worker.reliability_score = db_worker.total_tasks_completed / max(tot, 1)

                db.commit()

                # Trigger Aggregation check
                task = db.query(models.Task).filter(models.Task.id == db_chunk.task_id).first()
                if task:
                    try_aggregate_job(db, task.job_id)

            elif data.get("type") in ("PULL_CHUNK", "STEAL_CHUNK"):
                # Dynamic Work Stealing: worker proactively pulls the next available chunk
                db_worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
                if db_worker and getattr(db_worker, "trust_status", "trusted") != "rejected":
                    pending_chunk = db.query(models.TaskChunk).filter(models.TaskChunk.status == "pending").first()
                    if pending_chunk:
                        task = db.query(models.Task).filter(models.Task.id == pending_chunk.task_id).first()
                        job = db.query(models.Job).filter(models.Job.id == task.job_id).first() if task else None

                        pending_chunk.attempt_count = (pending_chunk.attempt_count or 0) + 1
                        attempt_uid = f"ATT-{pending_chunk.id:04d}-{pending_chunk.attempt_count:02d}"

                        attempt = models.ChunkAttempt(
                            attempt_uid=attempt_uid,
                            chunk_id=pending_chunk.id,
                            worker_id=db_worker.id,
                            attempt_number=pending_chunk.attempt_count,
                            status="assigned"
                        )
                        db.add(attempt)
                        pending_chunk.worker_id = db_worker.id
                        pending_chunk.status = "assigned"
                        pending_chunk.assigned_at = datetime.now(timezone.utc)
                        db_worker.running_tasks = (db_worker.running_tasks or 0) + 1
                        db.commit()

                        await websocket.send_json({
                            "action": "EXECUTE",
                            "chunk_id": pending_chunk.id,
                            "chunk_uid": pending_chunk.chunk_uid or f"CHUNK-{pending_chunk.id}",
                            "attempt_id": attempt_uid,
                            "job_id": job.id if job else None,
                            "job_uid": job.job_uid if job else "",
                            "task_type": job.job_type if job else "generic_python",
                            "payload": pending_chunk.input_data or {}
                        })


    except WebSocketDisconnect:
        manager.disconnect(worker_uid)
        logger.warning(f"WebSocket disconnected for worker {worker_uid}")
        # GAP 4: Immediate SUSPECTED state (< 1s) and Redis Pub/Sub notification
        await fault_detector.mark_suspected(db, worker_uid, reason="WebSocketDisconnect")

    except Exception as e:
        logger.error(f"WebSocket error for {worker_uid}: {e}")
        manager.disconnect(worker_uid)
        await fault_detector.mark_suspected(db, worker_uid, reason=str(e))
    finally:
        db.close()


# ── Dashboard Live WS ────────────────────────────────────────────────────────
@app.websocket("/ws/live")
async def dashboard_live_ws(websocket: WebSocket):
    import uuid
    client_id = str(uuid.uuid4())
    await websocket.accept()
    _dashboard_connections[client_id] = websocket
    logger.info(f"Dashboard client {client_id} connected to /ws/live")

    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        logger.info(f"Dashboard client {client_id} disconnected")
    except Exception as e:
        logger.debug(f"Dashboard WS {client_id} closed: {e}")
    finally:
        _dashboard_connections.pop(client_id, None)
