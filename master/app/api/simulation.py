"""
Cluster Digital Twin & Simulation REST API — CoCompute 3.0.

Provides:
  - POST /api/v1/simulation/start  — Launch N simulated virtual compute nodes
  - POST /api/v1/simulation/stop   — Stop virtual simulation and cleanup nodes
  - GET  /api/v1/simulation/status — Get active simulation status and virtual node pool
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..db import models
from ..core.security import get_current_admin_user
from ..engine.simulator import ClusterSimulator
from ..schemas.marketplace import SimulationStartRequest, SimulationStopRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/simulation", tags=["Cluster Simulation & Digital Twin"])


@router.post("/start")
def start_simulation(
    req: SimulationStartRequest,
    admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Spawns N virtual compute nodes for large-scale cluster experimentation.
    """
    res = ClusterSimulator.start_simulation(
        db=db,
        worker_count=req.worker_count,
        cpu_cores_per_worker=req.cpu_cores_per_worker,
        ram_gb_per_worker=req.ram_gb_per_worker,
        gpu_ratio=req.gpu_ratio,
        network_latency_ms=req.network_latency_ms,
        failure_probability=req.failure_probability,
        speed_multiplier=req.speed_multiplier
    )
    return res


@router.post("/stop")
def stop_simulation(
    admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Terminates the active virtual cluster simulation and cleans up virtual nodes.
    """
    return ClusterSimulator.stop_simulation(db)


@router.get("/status")
def get_simulation_status(db: Session = Depends(get_db)):
    """
    Returns current digital twin simulation status.
    """
    return ClusterSimulator.get_simulation_status(db)
