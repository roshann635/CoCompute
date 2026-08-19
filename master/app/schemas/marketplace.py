from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ComputePoolSummary(BaseModel):
    total_workers: int
    online_workers: int
    busy_workers: int
    total_cpu_cores: int
    total_ram_gb: float
    total_gpus: int
    total_vram_gb: float
    avg_cpu_utilization: float
    avg_ram_utilization: float
    pool_utilization_pct: float
    active_jobs_count: int
    queued_jobs_count: int
    simulated_workers_count: int


class CreditBalanceResponse(BaseModel):
    user_id: int
    username: str
    role: str
    credits_balance: float
    credits_daily_quota: float
    credits_consumed_today: float
    remaining_today: float


class CreditTransactionResponse(BaseModel):
    id: int
    amount: float
    cpu_hours: float
    gpu_hours: float
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AllocateCreditsRequest(BaseModel):
    user_id: int
    amount: float = Field(..., gt=0)
    description: Optional[str] = "Admin Top-up"


class SimulationStartRequest(BaseModel):
    worker_count: int = Field(10, ge=1, le=100)
    cpu_cores_per_worker: int = 4
    ram_gb_per_worker: float = 16.0
    gpu_ratio: float = 0.3  # 30% of workers get GPUs
    network_latency_ms: float = 5.0
    failure_probability: float = 0.02
    speed_multiplier: float = 1.0


class SimulationStopRequest(BaseModel):
    simulation_id: Optional[str] = None


class WorkerTrustApprovalRequest(BaseModel):
    approve: bool
    reason: Optional[str] = None
