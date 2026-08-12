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
    agent_version: Optional[str] = "1.0.0"
    python_version: Optional[str] = None
    api_key: str = "cocompute-worker-key"


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

    class Config:
        from_attributes = True
