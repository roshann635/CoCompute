from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class TaskManifest(BaseModel):
    name: str
    version: str = "1.0"
    description: Optional[str] = None
    runtime: str = "python:3.11"
    input_contract: Dict[str, Any] = Field(default_factory=lambda: {"type": "json", "schema": None})
    execution_contract: Dict[str, Any] = Field(default_factory=lambda: {"entrypoint": "Task", "cpu": "auto", "ram": "auto", "gpu": False})
    parallelization_contract: Dict[str, Any] = Field(default_factory=lambda: {"mode": "auto"})
    partition_contract: Dict[str, Any] = Field(default_factory=lambda: {"strategy": "auto"})
    aggregation_contract: Dict[str, Any] = Field(default_factory=lambda: {"mode": "auto"})
    timeout_sec: int = 300
    retry_count: int = 3


class TaskPackageCreate(BaseModel):
    name: str
    version: str = "1.0"
    description: Optional[str] = None
    runtime: str = "python:3.11"
    is_public: bool = True
    manifest: TaskManifest
    script_code: str
    entrypoint: str = "Task"


class TaskPackageResponse(BaseModel):
    id: int
    package_uid: str
    name: str
    version: str
    description: Optional[str] = None
    author: str
    runtime: str
    is_public: bool
    code_hash: Optional[str] = None
    manifest: Dict[str, Any]
    script_code: str
    entrypoint: str
    is_verified: bool
    compatibility_report: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskTestRequest(BaseModel):
    script_code: Optional[str] = None
    sample_input: Optional[Any] = None


class TaskTestResponse(BaseModel):
    passed: bool
    recommendation: str
    report: Dict[str, Any]
