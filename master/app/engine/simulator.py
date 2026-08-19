"""
Cluster Digital Twin & Simulation Engine — CoCompute 3.0.

Simulates heterogeneous virtual compute nodes (e.g., 10 to 100 virtual workers)
with configurable CPU cores, RAM, GPU, network latency, failure probabilities,
and execution speed multipliers.

Crucial Rule: All simulated workers are strictly tagged with `is_simulated = True`
and segregated so real physical benchmarks are never polluted with synthetic data.
"""

import math
import random
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ..db.database import SessionLocal
from ..db import models

logger = logging.getLogger(__name__)

SIMULATED_CPU_MODELS = [
    "Intel Core i7-13700K", "AMD Ryzen 9 7900X", "Apple M2 Pro (Sim)", "Intel Xeon Silver 4314", "AMD EPYC 7763"
]
SIMULATED_GPU_MODELS = [
    "NVIDIA RTX 4090", "NVIDIA RTX 3080", "NVIDIA A100 (40GB)", "NVIDIA T4", "NVIDIA RTX 3060"
]


class ClusterSimulator:
    _active_simulation_id: Optional[str] = None
    _simulated_tasks: List[asyncio.Task] = []

    @classmethod
    def start_simulation(
        cls,
        db: Session,
        worker_count: int = 10,
        cpu_cores_per_worker: int = 4,
        ram_gb_per_worker: float = 16.0,
        gpu_ratio: float = 0.3,
        network_latency_ms: float = 5.0,
        failure_probability: float = 0.02,
        speed_multiplier: float = 1.0
    ) -> Dict[str, Any]:
        """
        Creates and registers N virtual simulated worker records in the database.
        """
        cls.stop_simulation(db)

        simulation_id = f"SIM-{int(datetime.now(timezone.utc).timestamp())}"
        cls._active_simulation_id = simulation_id
        created_workers = []

        for i in range(1, worker_count + 1):
            uid = f"sim-node-{i:03d}"
            has_gpu = (random.random() < gpu_ratio)
            gpu_m = random.choice(SIMULATED_GPU_MODELS) if has_gpu else None
            vram = 24.0 if "4090" in str(gpu_m) or "A100" in str(gpu_m) else (12.0 if has_gpu else 0.0)

            w = models.Worker(
                worker_uid=uid,
                hostname=f"sim-host-{i:03d}",
                ip_address=f"10.200.0.{i}",
                status="online",
                cpu_cores=cpu_cores_per_worker + random.choice([-2, 0, 2, 4]),
                ram_total=ram_gb_per_worker,
                cpu_utilization=round(random.uniform(5.0, 35.0), 1),
                ram_usage=round(random.uniform(15.0, 45.0), 1),
                gpu_count=1 if has_gpu else 0,
                gpu_model=gpu_m,
                vram_total=vram,
                vram_usage=round(random.uniform(5.0, 25.0), 1) if has_gpu else 0.0,
                gpu_utilization=round(random.uniform(0.0, 20.0), 1) if has_gpu else 0.0,
                cuda_available=has_gpu,
                network_latency_ms=round(network_latency_ms + random.uniform(-2.0, 5.0), 1),
                platform="Linux (Simulated)",
                cpu_model=random.choice(SIMULATED_CPU_MODELS),
                reliability_score=round(random.uniform(0.85, 0.99), 2),
                trust_status="trusted",
                lifecycle_state="healthy",
                is_simulated=True,
                simulation_config={
                    "simulation_id": simulation_id,
                    "failure_prob": failure_probability,
                    "speed_multiplier": speed_multiplier
                }
            )
            db.add(w)
            created_workers.append(w)

        db.commit()
        logger.info(f"Started Cluster Simulation {simulation_id} with {worker_count} virtual nodes.")

        return {
            "simulation_id": simulation_id,
            "status": "running",
            "simulated_worker_count": len(created_workers),
            "simulated_gpu_nodes": sum(1 for w in created_workers if w.gpu_count > 0),
            "total_simulated_cores": sum(w.cpu_cores for w in created_workers),
            "total_simulated_ram_gb": sum(w.ram_total for w in created_workers)
        }

    @classmethod
    def stop_simulation(cls, db: Session) -> Dict[str, Any]:
        """
        Removes all virtual simulated workers from the database.
        """
        sim_workers = db.query(models.Worker).filter(models.Worker.is_simulated == True).all()
        count = len(sim_workers)
        for w in sim_workers:
            # Delete associated metrics or chunks if any
            db.query(models.Metric).filter(models.Metric.worker_id == w.id).delete()
            db.delete(w)
        db.commit()

        cls._active_simulation_id = None
        logger.info(f"Stopped simulation and removed {count} virtual workers.")
        return {"status": "stopped", "removed_simulated_workers": count}

    @classmethod
    def get_simulation_status(cls, db: Session) -> Dict[str, Any]:
        sim_workers = db.query(models.Worker).filter(models.Worker.is_simulated == True).all()
        return {
            "simulation_active": len(sim_workers) > 0,
            "simulation_id": cls._active_simulation_id,
            "simulated_workers_count": len(sim_workers),
            "simulated_workers": [
                {
                    "worker_uid": w.worker_uid,
                    "hostname": w.hostname,
                    "cpu_cores": w.cpu_cores,
                    "ram_total": w.ram_total,
                    "gpu_model": w.gpu_model,
                    "status": w.status,
                    "reliability_score": w.reliability_score
                }
                for w in sim_workers
            ]
        }
