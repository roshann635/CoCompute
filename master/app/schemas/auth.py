from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: Optional[str] = "researcher"


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    max_concurrent_jobs: int = 5
    max_workers_per_job: int = 20
    max_gpu_count: int = 4
    max_vram_gb: float = 32.0
    max_cpu_hours_per_day: float = 100.0
    priority: str = "NORMAL"
    created_at: datetime

    class Config:
        from_attributes = True


class UserQuotaUpdate(BaseModel):
    role: Optional[str] = None
    max_concurrent_jobs: Optional[int] = None
    max_workers_per_job: Optional[int] = None
    max_gpu_count: Optional[int] = None
    max_vram_gb: Optional[float] = None
    max_cpu_hours_per_day: Optional[float] = None
    priority: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
