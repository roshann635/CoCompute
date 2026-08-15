from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .job import JobResponse


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    project_uid: str
    name: str
    description: Optional[str] = None
    user_id: int
    created_at: datetime
    job_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    jobs: List[JobResponse] = []
