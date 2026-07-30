from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class JobCreate(BaseModel):
    name: str
    description: str
    job_type: str  # prime_generation, matrix_multiply, word_count, generic_python
    params: dict


class JobResponse(BaseModel):
    id: int
    name: str
    description: str
    job_type: str
    status: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    submission_time: datetime
    start_time: Optional[datetime]
    end_time: Optional[datetime]

    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    params: Optional[dict]
    aggregated_result: Optional[Any]


class JobResultResponse(BaseModel):
    job_id: int
    job_name: str
    status: str
    aggregated_result: Optional[Any]
    chunks_completed: int
    chunks_failed: int
    total_chunks: int
    total_execution_time_seconds: Optional[float]
