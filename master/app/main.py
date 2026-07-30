from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import asyncio
import logging
import os

from .db.database import engine, Base, get_db
from .db import models
from .api import workers, jobs, metrics, auth, analytics, logs
from .network.ws_manager import manager
from .network.discovery import start_discovery_server
from .engine.scheduler import unified_scheduler_loop, fault_tolerance_loop
from .engine.ai_scheduler import periodic_training_loop
from .engine.aggregator import try_aggregate_job

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

    logger.info("All background services started.")


@app.get("/")
def root():
    return {
        "name": "CoCompute Master Node",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


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
