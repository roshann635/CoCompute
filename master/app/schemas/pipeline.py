from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class PipelineStageSchema(BaseModel):
    stage_name: str
    stage_order: int = 0
    task_type: str
    task_package_id: Optional[int] = None
    condition: Optional[str] = None # e.g. "on_pass", "on_fail", "score > 90"


class PipelineCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dag_structure: Dict[str, Any] = Field(default_factory=dict)
    stages: List[PipelineStageSchema] = Field(default_factory=list)


class PipelineResponse(BaseModel):
    id: int
    pipeline_uid: str
    name: str
    description: Optional[str] = None
    status: str
    dag_structure: Dict[str, Any]
    created_at: Optional[datetime] = None
    stages: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True
