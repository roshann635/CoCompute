from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import asyncio
import logging
import os
import json

from .db.database import engine, Base, get_db
from .db import models
from .api import workers, jobs, metrics, auth, analytics, logs, alerts
from .network.ws_manager import manager
from .network.discovery import start_discovery_server
from .engine.scheduler import (
    unified_scheduler_loop, fault_tolerance_loop,
    get_active_algorithm, set_active_algorithm
)
from .engine.ai_scheduler import periodic_training_loop
from .engine.aggregator import try_aggregate_job
from .engine.analytics import get_cluster_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CoCompute Master Node",
    description="Collaborative Distributed Computing Framework for Intelligent Resource Sharing and Parallel Task Execution",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(workers.router, prefix="/api/v1/workers", tags=["workers"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(logs.router, prefix="/api/v1/logs", tags=["logs"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])

# ─── Dashboard live WebSocket connections ───
# Maps client_id → WebSocket for dashboard /ws/live connections
_dashboard_connections: dict[str, WebSocket] = {}


async def _broadcast_to_dashboards(payload: dict):
    """Push a message to all connected dashboard clients."""
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
    logger.info("  CoCompute Master Node Starting...")
    logger.info("=" * 60)

    # Start UDP Discovery Server
    logger.info("Starting UDP Discovery Server on port 9999...")
    discovery_ip = os.getenv("MASTER_DISCOVERY_IP", "0.0.0.0")
    asyncio.create_task(start_discovery_server(discovery_ip, 8000))

    # Start the SINGLE unified scheduler (fixes the dual-scheduler bug)
    asyncio.create_task(unified_scheduler_loop())

    # Start fault tolerance monitor
    asyncio.create_task(fault_tolerance_loop())

    # Start periodic AI model training
    asyncio.create_task(periodic_training_loop())

    # Start the dashboard live-push broadcast loop
    asyncio.create_task(_dashboard_broadcast_loop())

    logger.info("All background services started.")


async def _dashboard_broadcast_loop():
    """
    Periodically push cluster snapshot + alerts to all dashboard WebSocket clients.
    This provides the SRS-specified real-time WebSocket streaming for the dashboard (NFR 5.1).
    """
    from .engine.analytics import get_cluster_efficiency, get_resource_utilization_history
    from .db.database import SessionLocal

    logger.info("Starting Dashboard Live Broadcast Loop...")
    while True:
        if _dashboard_connections:
            db = None
            try:
                db = SessionLocal()
                online_workers = db.query(models.Worker).filter(models.Worker.status == "online").all()
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
            except Exception as e:
                logger.error(f"Dashboard broadcast error: {e}")
            finally:
                if db:
                    db.close()
        await asyncio.sleep(3)


@app.get("/")
def root():
    return {
        "name": "CoCompute Master Node",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


# ─────────────────────────────────────────────
# Scheduler Runtime Configuration (FR-14 toggle)
# ─────────────────────────────────────────────

@app.get("/api/v1/scheduler/config")
def get_scheduler_config():
    """Get current scheduler algorithm and thresholds."""
    from .engine.scheduler import HIGH_UTILIZATION_THRESHOLD, HIGH_RAM_THRESHOLD
    return {
        "algorithm": get_active_algorithm(),
        "valid_algorithms": ["round_robin", "resource_aware", "ai_predictive"],
        "high_utilization_threshold": HIGH_UTILIZATION_THRESHOLD,
        "high_ram_threshold": HIGH_RAM_THRESHOLD,
    }


@app.post("/api/v1/scheduler/config")
def set_scheduler_config(body: dict):
    """
    Runtime toggle for the scheduler algorithm.
    Allows the dashboard to switch between round_robin, resource_aware, and ai_predictive.
    """
    algorithm = body.get("algorithm")
    if not algorithm:
        raise HTTPException(status_code=400, detail="'algorithm' field is required")
    try:
        set_active_algorithm(algorithm)
        return {"message": f"Scheduler algorithm set to '{algorithm}'", "algorithm": algorithm}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────
# Worker WebSocket (existing)
# ─────────────────────────────────────────────

@app.websocket("/ws/worker/{worker_uid}")
async def websocket_endpoint(websocket: WebSocket, worker_uid: str):
    db: Session = next(get_db())
    await manager.connect(websocket, worker_uid)

    # Mark worker as online
    db_worker = db.query(models.Worker).filter(models.Worker.worker_uid == worker_uid).first()
    if db_worker:
        db_worker.status = "online"
        db_worker.last_seen = datetime.now(timezone.utc)
        db.commit()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "METRICS":
                # --- Heartbeat / Metrics Update ---
                m = data.get("data", {})

                db_worker = db.query(models.Worker).filter(
                    models.Worker.worker_uid == worker_uid
                ).first()
                if db_worker:
                    db_worker.last_seen = datetime.now(timezone.utc)
                    db_worker.status = "online"
                    db_worker.cpu_utilization = m.get("cpu_usage", 0)
                    db_worker.ram_usage = m.get("ram_usage", 0)
                    db_worker.disk_usage = m.get("disk_usage", 0)
                    db_worker.running_tasks = m.get("running_tasks", 0)

                    # Store metric record
                    new_metric = models.Metric(
                        worker_id=db_worker.id,
                        cpu_usage=m.get("cpu_usage"),
                        ram_usage=m.get("ram_usage"),
                        disk_usage=m.get("disk_usage"),
                        network_tx=m.get("network_tx"),
                        network_rx=m.get("network_rx"),
                        running_tasks=m.get("running_tasks", 0)
                    )
                    db.add(new_metric)

                    # Store health record
                    health = models.NodeHealthRecord(
                        worker_id=db_worker.id,
                        cpu_usage=m.get("cpu_usage", 0),
                        ram_usage=m.get("ram_usage", 0),
                        disk_usage=m.get("disk_usage", 0),
                        temperature=m.get("temperature"),
                        network_speed=m.get("network_speed"),
                        running_tasks=m.get("running_tasks", 0),
                        is_healthy=True
                    )
                    db.add(health)
                    db.commit()

            elif data.get("type") == "RESULT":
                # --- Task Result Submission ---
                chunk_id = data.get("chunk_id")
                result_data = data.get("result_data", {})

                db_chunk = db.query(models.TaskChunk).filter(
                    models.TaskChunk.id == chunk_id
                ).first()

                if db_chunk:
                    status = result_data.get("status")
                    db_chunk.end_time = datetime.now(timezone.utc)

                    # Calculate execution time
                    exec_time = None
                    if db_chunk.start_time and db_chunk.end_time:
                        exec_time = (db_chunk.end_time - db_chunk.start_time).total_seconds()

                    if status == "success":
                        db_chunk.status = "completed"
                    else:
                        db_chunk.status = "failed"

                    # Save result
                    new_result = models.Result(
                        task_chunk_id=chunk_id,
                        result_data=result_data.get("result"),
                        error_log=result_data.get("error"),
                        execution_time_seconds=exec_time
                    )
                    db.add(new_result)

                    # Update worker stats
                    worker = db.query(models.Worker).filter(
                        models.Worker.id == db_chunk.worker_id
                    ).first()
                    if worker:
                        if status == "success":
                            worker.total_tasks_completed += 1
                        else:
                            worker.total_tasks_failed += 1
                        total = worker.total_tasks_completed + worker.total_tasks_failed
                        worker.reliability_score = worker.total_tasks_completed / max(total, 1)

                    db.commit()

                    # Try to aggregate results for the parent job
                    db_task = db.query(models.Task).filter(
                        models.Task.id == db_chunk.task_id
                    ).first()
                    if db_task:
                        try_aggregate_job(db, db_task.job_id)

    except WebSocketDisconnect:
        manager.disconnect(worker_uid)
        db_worker = db.query(models.Worker).filter(
            models.Worker.worker_uid == worker_uid
        ).first()
        if db_worker:
            db_worker.status = "offline"
            db_worker.running_tasks = 0
            db.commit()
        logger.info(f"Worker {worker_uid} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for {worker_uid}: {e}")
        manager.disconnect(worker_uid)
    finally:
        db.close()


# ─────────────────────────────────────────────
# Dashboard Live WebSocket (push-based, FR-10 / NFR)
# ─────────────────────────────────────────────

@app.websocket("/ws/live")
async def dashboard_live_ws(websocket: WebSocket):
    """
    WebSocket endpoint for the dashboard to receive real-time cluster updates.
    Pushes CLUSTER_UPDATE messages every ~3 seconds without polling.
    """
    import uuid
    client_id = str(uuid.uuid4())
    await websocket.accept()
    _dashboard_connections[client_id] = websocket
    logger.info(f"Dashboard client {client_id} connected to /ws/live")

    try:
        # Keep connection alive; the broadcast loop does the pushing
        while True:
            # Accept any ping/pong or control messages from client
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Client can send {"type": "ping"} to keep alive
            except asyncio.TimeoutError:
                # Send a keepalive ping
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        logger.info(f"Dashboard client {client_id} disconnected")
    except Exception as e:
        logger.debug(f"Dashboard WS {client_id} closed: {e}")
    finally:
        _dashboard_connections.pop(client_id, None)
