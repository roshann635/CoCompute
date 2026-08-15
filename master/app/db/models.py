from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STUDENT = "student"
    RESEARCHER = "researcher"
    FACULTY = "faculty"
    USER = "user"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="researcher")
    is_active = Column(Boolean, default=True)

    # Resource Quotas (FR Institutional Multi-User)
    max_concurrent_jobs = Column(Integer, default=5)
    max_workers_per_job = Column(Integer, default=20)
    max_gpu_count = Column(Integer, default=4)
    max_vram_gb = Column(Float, default=32.0)
    max_cpu_hours_per_day = Column(Float, default=100.0)
    priority = Column(String(20), default="NORMAL")  # NORMAL, HIGH, CRITICAL

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workers = relationship("Worker", back_populates="owner")
    jobs = relationship("Job", back_populates="owner")
    projects = relationship("Project", back_populates="owner")


class Project(Base):
    """
    Project container for organizing multiple Jobs and tracking institutional resources.
    """
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    project_uid = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("User", back_populates="projects")
    jobs = relationship("Job", back_populates="project")


class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    worker_uid = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="offline")  # online, offline, busy, suspected, failed
    ip_address = Column(String(50))
    hostname = Column(String(255))
    cpu_cores = Column(Integer)
    cpu_utilization = Column(Float, default=0.0)
    ram_total = Column(Float)
    ram_usage = Column(Float, default=0.0)
    disk_total = Column(Float)
    disk_usage = Column(Float, default=0.0)
    network_speed = Column(Float, default=0.0)  # Mbps
    network_latency_ms = Column(Float, default=1.0)
    platform = Column(String(100))
    cpu_model = Column(String(255), nullable=True)
    cpu_frequency = Column(Float, nullable=True)
    mac_address = Column(String(100), nullable=True)
    agent_version = Column(String(20), default="2.0.0")
    python_version = Column(String(20), nullable=True)
    reliability_score = Column(Float, default=1.0)  # 0.0 to 1.0
    total_tasks_completed = Column(Integer, default=0)
    total_tasks_failed = Column(Integer, default=0)
    running_tasks = Column(Integer, default=0)
    
    # GPU Hardware & Telemetry
    gpu_count = Column(Integer, default=0)
    gpu_model = Column(String(255), nullable=True)
    vram_total = Column(Float, default=0.0)      # GB
    vram_usage = Column(Float, default=0.0)      # %
    gpu_utilization = Column(Float, default=0.0) # %
    gpu_temperature = Column(Float, nullable=True)
    cuda_available = Column(Boolean, default=False)
    cuda_capability = Column(String(20), default="8.6")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="workers")
    task_chunks = relationship("TaskChunk", back_populates="worker", foreign_keys="[TaskChunk.worker_id]")
    metrics = relationship("Metric", back_populates="worker")
    health_records = relationship("NodeHealthRecord", back_populates="worker")
    chunk_attempts = relationship("ChunkAttempt", back_populates="worker")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    job_uid = Column(String(20), unique=True, index=True, nullable=True)  # e.g., "JOB-001"
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    name = Column(String(255))
    description = Column(Text)
    job_type = Column(String(50))  # sorting, matrix_multiply, statistics, search, word_count, image_processing, prime_generation, cipher, ml_training, distributed_inference, llm_finetune, generic_python
    scheduler_strategy = Column(String(50), default="capacity_based")
    priority = Column(String(20), default="NORMAL")
    status = Column(String(20), default="pending")  # pending, running, aggregating, completed, failed, rejected
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    rescheduled_tasks = Column(Integer, default=0)
    workers_used = Column(Integer, default=0)
    
    # Resource requirements
    requires_gpu = Column(Boolean, default=False)
    min_vram_gb = Column(Float, default=0.0)

    params = Column(JSON)  # Original job parameters
    input_summary = Column(JSON, nullable=True)
    aggregated_result = Column(JSON, nullable=True)
    result_preview = Column(Text, nullable=True)
    result_location = Column(String(255), nullable=True)
    checkpoint_location = Column(String(255), nullable=True)
    model_location = Column(String(255), nullable=True)
    timeline = Column(JSON, default=list)

    submission_time = Column(DateTime(timezone=True), server_default=func.now())
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="jobs")
    project = relationship("Project", back_populates="jobs")
    tasks = relationship("Task", back_populates="job")
    checkpoints = relationship("Checkpoint", back_populates="job")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    type = Column(String(50))
    payload_ref = Column(JSON)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="tasks")
    chunks = relationship("TaskChunk", back_populates="task")


class TaskChunk(Base):
    __tablename__ = "task_chunks"
    id = Column(Integer, primary_key=True, index=True)
    chunk_uid = Column(String(20), index=True, nullable=True)  # e.g., "CHUNK-001"
    task_id = Column(Integer, ForeignKey("tasks.id"))
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    chunk_index = Column(Integer)
    data_payload = Column(JSON)
    input_reference = Column(String(255), nullable=True)
    output_reference = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")  # pending, assigned, running, completed, failed, rescheduled
    attempt_count = Column(Integer, default=0)
    accepted_attempt_id = Column(String(50), nullable=True)  # GAP 5: Duplicate protection
    max_retries = Column(Integer, default=3)
    rescheduled_from_worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    rescheduled_reason = Column(String(100), nullable=True)
    checksum = Column(String(100), nullable=True)  # SHA-256 hash
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    task = relationship("Task", back_populates="chunks")
    worker = relationship("Worker", back_populates="task_chunks", foreign_keys=[worker_id])
    rescheduled_from_worker = relationship("Worker", foreign_keys=[rescheduled_from_worker_id])
    result = relationship("Result", back_populates="chunk", uselist=False)
    attempts = relationship("ChunkAttempt", back_populates="chunk", order_by="ChunkAttempt.attempt_number")


class ChunkAttempt(Base):
    """
    Provenance tracking for every chunk execution attempt across nodes.
    """
    __tablename__ = "chunk_attempts"
    id = Column(Integer, primary_key=True, index=True)
    attempt_uid = Column(String(50), index=True, nullable=True)  # e.g. "ATT-001"
    chunk_id = Column(Integer, ForeignKey("task_chunks.id"), index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), index=True)
    attempt_number = Column(Integer, default=1)
    status = Column(String(20), default="assigned")  # assigned, running, completed, failed, timeout
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    failure_reason = Column(Text, nullable=True)
    checksum = Column(String(100), nullable=True)
    input_reference = Column(String(255), nullable=True)
    output_reference = Column(String(255), nullable=True)
    result_summary = Column(Text, nullable=True)

    # Relationships
    chunk = relationship("TaskChunk", back_populates="attempts")
    worker = relationship("Worker", back_populates="chunk_attempts")


class Checkpoint(Base):
    """
    ML/LLM training checkpoint model for fault-tolerant step resumption.
    """
    __tablename__ = "checkpoints"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    checkpoint_step = Column(Integer, default=0)
    checkpoint_epoch = Column(Integer, default=0)
    checkpoint_location = Column(String(255), nullable=False)
    loss = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    metrics = Column(JSON, nullable=True)
    is_valid = Column(Boolean, default=True)
    saved_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="checkpoints")


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    task_chunk_id = Column(Integer, ForeignKey("task_chunks.id"), unique=True)
    result_data = Column(JSON)
    output_reference = Column(String(255), nullable=True)
    checksum = Column(String(100), nullable=True)
    error_log = Column(Text, nullable=True)
    execution_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chunk = relationship("TaskChunk", back_populates="result")


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    cpu_usage = Column(Float)
    ram_usage = Column(Float)
    disk_usage = Column(Float)
    network_tx = Column(Float)
    network_rx = Column(Float)
    running_tasks = Column(Integer, default=0)
    gpu_utilization = Column(Float, nullable=True)
    vram_usage = Column(Float, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    worker = relationship("Worker", back_populates="metrics")


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20))
    source = Column(String(100))
    message = Column(Text)
    log_metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class SchedulerDecision(Base):
    __tablename__ = "scheduler_decisions"
    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("task_chunks.id"))
    worker_id = Column(Integer, ForeignKey("workers.id"))
    algorithm = Column(String(50))
    score = Column(Float, nullable=True)
    decision_reason = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    worker = relationship("Worker")


class NodeHealthRecord(Base):
    __tablename__ = "node_health_records"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    cpu_usage = Column(Float, default=0.0)
    ram_usage = Column(Float, default=0.0)
    disk_usage = Column(Float, default=0.0)
    temperature = Column(Float, nullable=True)
    network_speed = Column(Float, default=0.0)
    running_tasks = Column(Integer, default=0)
    is_healthy = Column(Boolean, default=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    worker = relationship("Worker", back_populates="health_records")


class BenchmarkRun(Base):
    """
    Stores executed scalability and scheduler comparison benchmarks with real measured values.
    """
    __tablename__ = "benchmark_runs"
    id = Column(Integer, primary_key=True, index=True)
    benchmark_type = Column(String(50))  # scalability, scheduler_comparison
    parameters = Column(JSON)
    results = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
