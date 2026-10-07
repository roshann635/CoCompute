from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class WorkerCreate(BaseModel):
    worker_uid: str
    ip_address: str
    hostname: str
    cpu_cores: int
    ram_total: float
    disk_total: float
    platform: str
    worker_type: Optional[str] = "PHYSICAL"
    cpu_model: Optional[str] = None
    cpu_frequency: Optional[float] = None
    mac_address: Optional[str] = None
    agent_version: Optional[str] = "3.1.0"
    python_version: Optional[str] = None
    protocol_version: Optional[str] = "1.0"
    docker: Optional[bool] = False
    supported_task_versions: Optional[List[str]] = None
    capabilities: Optional[Dict[str, Any]] = None
    lifecycle_state: Optional[str] = "healthy"
    api_key: str = "cocompute-worker-key"
    # GPU Specifications
    gpu_count: Optional[int] = 0
    gpu_model: Optional[str] = "None"
    vram_total: Optional[float] = 0.0
    cuda_available: Optional[bool] = False


class WorkerResponse(BaseModel):
    id: int
    worker_uid: str
    ip_address: Optional[str] = "127.0.0.1"
    hostname: Optional[str] = "unknown"
    cpu_cores: Optional[int] = 1
    ram_total: Optional[float] = 1.0
    disk_total: Optional[float] = 1.0
    platform: Optional[str] = "unknown"
    worker_type: Optional[str] = "PHYSICAL"
    session_id: Optional[str] = None
    lifecycle_state: Optional[str] = "healthy"
    capabilities: Optional[Dict[str, Any]] = None
    cpu_model: Optional[str] = None
    cpu_frequency: Optional[float] = None
    mac_address: Optional[str] = None
    agent_version: Optional[str] = None
    python_version: Optional[str] = None
    status: Optional[str] = "offline"
    cpu_utilization: Optional[float] = 0.0
    ram_usage: Optional[float] = 0.0
    disk_usage: Optional[float] = 0.0
    reliability_score: Optional[float] = 1.0
    total_tasks_completed: Optional[int] = 0
    total_tasks_failed: Optional[int] = 0
    running_tasks: Optional[int] = 0
    created_at: Optional[datetime] = None
    last_seen: Optional[datetime] = None
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

