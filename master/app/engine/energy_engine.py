"""
Energy-Aware & Carbon Modeling Engine — CoCompute 3.0.

Models estimated power consumption:
  P = P_idle + P_cpu * U_cpu + P_gpu * U_gpu
Estimates total energy in kWh and equivalent carbon footprint in gCO2e.
Provides scoring modifiers for ECO / FAST / BALANCED modes.
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..db import models

logger = logging.getLogger(__name__)

# Average hardware wattage constants (Watts)
P_IDLE_WATTS = 25.0
P_CPU_MAX_WATTS = 65.0
P_GPU_MAX_WATTS = 220.0
# Global average grid carbon intensity (approx 475 gCO2e per kWh)
CARBON_INTENSITY_G_PER_KWH = 475.0


def estimate_job_energy(job: models.Job, duration_seconds: float, workers_used: int, requires_gpu: bool = False) -> Dict[str, float]:
    """
    Computes energy consumption (kWh) and carbon emissions (gCO2eq) for a completed job.
    """
    if duration_seconds <= 0 or workers_used <= 0:
        return {"energy_kwh": 0.0, "carbon_gco2_eq": 0.0}

    hours = duration_seconds / 3600.0
    
    # Power per worker
    base_power = P_IDLE_WATTS + (P_CPU_MAX_WATTS * 0.7)  # approx 70% CPU usage
    if requires_gpu:
        base_power += (P_GPU_MAX_WATTS * 0.8)             # approx 80% GPU usage

    total_watts = base_power * workers_used
    energy_kwh = round((total_watts * hours) / 1000.0, 5)
    carbon_gco2 = round(energy_kwh * CARBON_INTENSITY_G_PER_KWH, 3)

    job.estimated_energy_kwh = energy_kwh
    job.carbon_gco2_eq = carbon_gco2

    return {
        "energy_kwh": energy_kwh,
        "carbon_gco2_eq": carbon_gco2,
        "total_watts": round(total_watts, 2)
    }


def compute_energy_score(worker: models.Worker, energy_mode: str = "BALANCED") -> float:
    """
    Computes worker energy efficiency score (0.0 to 100.0).
    Higher score is better (lower current power draw / lower heat).
    """
    cpu_util = getattr(worker, "cpu_utilization", 0.0) or 0.0
    gpu_util = getattr(worker, "gpu_utilization", 0.0) or 0.0
    temp = getattr(worker, "gpu_temperature", 45.0) or 45.0

    # In ECO mode, heavily penalize hot/overutilized nodes
    if energy_mode == "ECO":
        score = 100.0 - (cpu_util * 0.6) - (gpu_util * 0.3) - (max(0, temp - 50) * 0.5)
    elif energy_mode == "FAST":
        # In FAST mode, prioritize sheer speed (cores, ram) over energy
        cores = getattr(worker, "cpu_cores", 4) or 4
        score = (cores * 10.0) + (100.0 - cpu_util * 0.2)
    else:  # BALANCED
        cores = getattr(worker, "cpu_cores", 4) or 4
        score = (cores * 5.0) + (100.0 - cpu_util * 0.4) - (gpu_util * 0.2)

    return max(0.0, min(100.0, round(score, 2)))
