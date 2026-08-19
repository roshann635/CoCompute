from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class JobCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    job_type: str  # sorting, matrix_multiply, statistics, search, word_count, image_processing, prime_generation, cipher, ml_training, distributed_inference, llm_finetune, generic_python
    params: dict
    project_id: Optional[int] = None
    scheduler_strategy: Optional[str] = "adaptive_hybrid"
    priority: Optional[str] = "NORMAL"
    energy_mode: Optional[str] = "BALANCED"  # FAST, ECO, BALANCED
    is_speculative_enabled: Optional[bool] = True
    requires_gpu: Optional[bool] = False
    min_vram_gb: Optional[float] = 0.0


class JobResponse(BaseModel):
    id: int
    job_uid: Optional[str] = None
    user_id: Optional[int] = None
    project_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    job_type: str
    scheduler_strategy: Optional[str] = "adaptive_hybrid"
    priority: Optional[str] = "NORMAL"
    energy_mode: Optional[str] = "BALANCED"
    status: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    workers_used: int = 0
    requires_gpu: bool = False
    min_vram_gb: float = 0.0
    credits_cost: float = 0.0
    estimated_energy_kwh: float = 0.0
    carbon_gco2_eq: float = 0.0
    submission_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result_preview: Optional[str] = None
    checkpoint_location: Optional[str] = None
    model_location: Optional[str] = None

    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    params: Optional[dict] = None
    input_summary: Optional[dict] = None
    workload_profile: Optional[dict] = None
    aggregated_result: Optional[Any] = None
    timeline: Optional[list[dict]] = []


class JobResultResponse(BaseModel):
    job_id: int
    job_uid: Optional[str] = None
    job_name: str
    status: str
    aggregated_result: Optional[Any] = None
    input_summary: Optional[dict] = None
    workload_profile: Optional[dict] = None
    result_preview: Optional[str] = None
    chunks_completed: int
    chunks_failed: int
    total_chunks: int
    workers_used: int = 0
    total_execution_time_seconds: Optional[float] = None
    estimated_energy_kwh: float = 0.0
    carbon_gco2_eq: float = 0.0
    checkpoint_location: Optional[str] = None
    model_location: Optional[str] = None


class ChunkProvenanceItem(BaseModel):
    chunk_id: int
    chunk_uid: Optional[str] = None
    chunk_index: int
    status: str
    worker_uid: Optional[str] = None
    attempt_count: int
    accepted_attempt_id: Optional[str] = None
    is_speculative: bool = False
    attempts: list[dict] = []


class JobProvenanceResponse(BaseModel):
    job_id: int
    job_uid: Optional[str] = None
    job_name: str
    job_type: str
    status: str
    input_summary: Optional[dict] = None
    result_preview: Optional[str] = None
    workers_used: int = 0
    total_chunks: int
    completed_chunks: int
    failed_chunks: int
    total_execution_time_seconds: Optional[float] = None
    chunks: list[ChunkProvenanceItem] = []


class JobTimelineResponse(BaseModel):
    job_id: int
    job_uid: Optional[str] = None
    job_name: str
    status: str
    events: list[dict] = []
