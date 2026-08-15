from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WorkerCreate(BaseModel):
    worker_uid: str
    ip_address: str
    hostname: str
    cpu_cores: int
    ram_total: float
    disk_total: float
    platform: str
    cpu_model: Optional[str] = None
    cpu_frequency: Optional[float] = None
    mac_address: Optional[str] = None
    agent_version: Optional[str] = "2.0.0"
    python_version: Optional[str] = None
    api_key: str = "cocompute-worker-key"
    # GPU Specifications
    gpu_count: Optional[int] = 0
    gpu_model: Optional[str] = "None"
    vram_total: Optional[float] = 0.0
    cuda_available: Optional[bool] = False


class WorkerResponse(BaseModel):
    id: int
    worker_uid: str
    ip_address: str
    hostname: str
    cpu_cores: int
    ram_total: float
    disk_total: float
    platform: str
    cpu_model: Optional[str]
    cpu_frequency: Optional[float]
    mac_address: Optional[str]
    agent_version: Optional[str]
    python_version: Optional[str]
    status: str
    cpu_utilization: float
    ram_usage: float
    disk_usage: float
    reliability_score: float
    total_tasks_completed: int
    total_tasks_failed: int
    running_tasks: int
    created_at: datetime
    last_seen: Optional[datetime]
    # GPU Telemetry
    gpu_count: Optional[int] = 0
    gpu_model: Optional[str] = "None"
    vram_total: Optional[float] = 0.0
    vram_usage: Optional[float] = 0.0
    gpu_utilization: Optional[float] = 0.0
    gpu_temperature: Optional[float] = None
    cuda_available: Optional[bool] = False

    class Config:
        from_attributes = True
