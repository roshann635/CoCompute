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


class TrustStatus(str, enum.Enum):
    PENDING = "pending"
    TRUSTED = "trusted"
    REJECTED = "rejected"


class WorkerLifecycle(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DRAINING = "draining"
    FAILED = "failed"
    RECOVERING = "recovering"
    BENCHMARKING = "benchmarking"


class EnergyMode(str, enum.Enum):
    FAST = "FAST"
    ECO = "ECO"
    BALANCED = "BALANCED"


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

    # CoCompute 3.0 Compute Credit System
    credits_balance = Column(Float, default=500.0)
    credits_daily_quota = Column(Float, default=500.0)
    credits_consumed_today = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workers = relationship("Worker", back_populates="owner")
    jobs = relationship("Job", back_populates="owner")
    projects = relationship("Project", back_populates="owner")
    credit_transactions = relationship("CreditTransaction", back_populates="user")


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
    agent_version = Column(String(20), default="3.0.0")
    python_version = Column(String(20), nullable=True)
    
    # 5-Factor Reliability Intelligence (CoCompute 3.0)
    reliability_score = Column(Float, default=1.0)          # Composite score 0.0 to 1.0
    execution_consistency = Column(Float, default=1.0)     # Variance of runtimes
    network_stability = Column(Float, default=1.0)         # Latency stability index
    thermal_stability = Column(Float, default=1.0)         # Temperature headroom index
    uptime_ratio = Column(Float, default=1.0)              # Uptime %
    
    total_tasks_completed = Column(Integer, default=0)
    total_tasks_failed = Column(Integer, default=0)
    running_tasks = Column(Integer, default=0)
    
    # Trust & Enrollment Workflow (CoCompute 3.0)
    trust_status = Column(String(20), default="trusted")   # pending, trusted, rejected
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_by = Column(String(100), nullable=True)
    
    # Self-Healing Lifecycle (CoCompute 3.0)
    lifecycle_state = Column(String(20), default="healthy") # healthy, degraded, draining, failed, recovering, benchmarking
    
    # Digital Twin Simulation Mode (CoCompute 3.0)
    is_simulated = Column(Boolean, default=False)
    simulation_config = Column(JSON, nullable=True)
    
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
    attempts = relationship("ChunkAttempt", back_populates="worker")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    job_uid = Column(String(50), unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    name = Column(String(255))
    job_type = Column(String(50))  # sorting, matrix_multiply, word_count, prime_generation, etc.
    scheduler_strategy = Column(String(50), default="adaptive_hybrid")  # adaptive_hybrid, capacity_based, etc.
    priority = Column(String(20), default="NORMAL")  # NORMAL, HIGH, CRITICAL
    status = Column(String(20), default="pending")  # pending, running, completed, failed, cancelled
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    rescheduled_tasks = Column(Integer, default=0)
    workers_used = Column(Integer, default=0)
    
    # CoCompute 3.0 Workload Profiling & Energy Modeling
    workload_profile = Column(JSON, nullable=True)       # CPU/GPU/RAM/Network intensity, data size
    energy_mode = Column(String(20), default="BALANCED") # FAST, ECO, BALANCED
    estimated_energy_kwh = Column(Float, default=0.0)
    carbon_gco2_eq = Column(Float, default=0.0)
    credits_cost = Column(Float, default=0.0)
    is_speculative_enabled = Column(Boolean, default=True)
    predicted_duration_sec = Column(Float, nullable=True)
    actual_duration_sec = Column(Float, nullable=True)

    # CoCompute 4.0 Universal Autonomous Platform Attributes
    task_package_id = Column(Integer, ForeignKey("task_packages.id", ondelete="SET NULL"), nullable=True)
    pipeline_id = Column(Integer, ForeignKey("task_pipelines.id", ondelete="SET NULL"), nullable=True)
    pipeline_stage_id = Column(Integer, nullable=True)
    pilot_profile = Column(JSON, nullable=True)
    parallelism_analysis = Column(JSON, nullable=True)
    execution_plan = Column(JSON, nullable=True)          # Formal ExecutionPlan object (v1, v2, v3...)
    decision_explanation = Column(JSON, nullable=True)    # Human-readable rationale
    result_semantic_type = Column(String(50), nullable=True) # table, matrix, image, statistics, ml_metrics
    result_quality = Column(JSON, nullable=True)          # Quality score %, missing records, validation checks
    reproducibility_envelope = Column(JSON, nullable=True) # Full exact/equivalent metadata
    is_reproducible = Column(Boolean, default=True)

    # Hardware & Runtime requirements
    requires_gpu = Column(Boolean, default=False)
    min_vram_gb = Column(Float, default=0.0)
    checkpoint_location = Column(String(500), nullable=True)
    model_location = Column(String(500), nullable=True)
    result_location = Column(String(500), nullable=True)

    # User Input & Result Summaries
    input_summary = Column(JSON, nullable=True)
    result_preview = Column(Text, nullable=True)
    timeline = Column(JSON, nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    params = Column(JSON, nullable=True)
    aggregated_result = Column(JSON, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="jobs")
    project = relationship("Project", back_populates="jobs")
    tasks = relationship("Task", back_populates="job", cascade="all, delete-orphan")
    checkpoints = relationship("Checkpoint", back_populates="job", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="job")
    task_package = relationship("TaskPackage", back_populates="jobs")
    pipeline = relationship("TaskPipeline", back_populates="jobs")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    name = Column(String(255))
    type = Column(String(50))
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="tasks")
    chunks = relationship("TaskChunk", back_populates="task", cascade="all, delete-orphan")


class TaskChunk(Base):
    __tablename__ = "task_chunks"
    id = Column(Integer, primary_key=True, index=True)
    chunk_uid = Column(String(50), unique=True, index=True, nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    chunk_index = Column(Integer)
    status = Column(String(20), default="pending")  # pending, assigned, running, completed, failed, timeout
    attempt_count = Column(Integer, default=0)
    accepted_attempt_id = Column(String(50), nullable=True)  # GAP 5: Duplicate attempt rejection guard
    
    # CoCompute 3.0 Speculative Execution (Straggler Mitigation)
    is_speculative = Column(Boolean, default=False)
    speculative_parent_chunk_id = Column(Integer, nullable=True)

    # Fault Recovery Provenance
    rescheduled_from_worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    rescheduled_reason = Column(String(255), nullable=True)

    input_data = Column(JSON)
    start_time = Column(DateTime(timezone=True), nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    task = relationship("Task", back_populates="chunks")
    worker = relationship("Worker", back_populates="task_chunks", foreign_keys=[worker_id])
    rescheduled_from = relationship("Worker", foreign_keys=[rescheduled_from_worker_id])
    result = relationship("Result", back_populates="chunk", uselist=False, cascade="all, delete-orphan")
    attempts = relationship("ChunkAttempt", back_populates="chunk", cascade="all, delete-orphan")


class ChunkAttempt(Base):
    __tablename__ = "chunk_attempts"
    id = Column(Integer, primary_key=True, index=True)
    attempt_uid = Column(String(50), unique=True, index=True, nullable=False)
    chunk_id = Column(Integer, ForeignKey("task_chunks.id"), nullable=False)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    attempt_number = Column(Integer, default=1)
    status = Column(String(20), default="assigned")  # assigned, running, completed, failed, timeout
    is_speculative = Column(Boolean, default=False)

    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    input_reference = Column(String(500), nullable=True)
    output_reference = Column(String(500), nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    failure_reason = Column(String(255), nullable=True)

    # Relationships
    chunk = relationship("TaskChunk", back_populates="attempts")
    worker = relationship("Worker", back_populates="attempts")


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    task_chunk_id = Column(Integer, ForeignKey("task_chunks.id"))
    result_data = Column(JSON)
    output_reference = Column(String(500), nullable=True)
    checksum_sha256 = Column(String(64), nullable=True)
    execution_time = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    chunk = relationship("TaskChunk", back_populates="result")


class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    checkpoint_step = Column(Integer, default=0)
    checkpoint_epoch = Column(Integer, default=0)
    checkpoint_location = Column(String(500), nullable=False)
    loss = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    metrics = Column(JSON, nullable=True)
    is_valid = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="checkpoints")


class CreditTransaction(Base):
    """
    Compute credit transaction ledger for tracking institutional usage.
    """
    __tablename__ = "credit_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    amount = Column(Float, nullable=False)          # Positive = topup, Negative = spent
    cpu_hours = Column(Float, default=0.0)
    gpu_hours = Column(Float, default=0.0)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="credit_transactions")
    job = relationship("Job", back_populates="credit_transactions")


class WorkloadFeedback(Base):
    """
    Closed-loop feedback engine tracking predicted vs actual execution time.
    """
    __tablename__ = "workload_feedback"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    job_type = Column(String(50), nullable=False)
    strategy_used = Column(String(50), nullable=False)
    predicted_duration_sec = Column(Float, nullable=False)
    actual_duration_sec = Column(Float, nullable=False)
    prediction_error_sec = Column(Float, nullable=False)
    error_percentage = Column(Float, default=0.0)
    workers_count = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    cpu_utilization = Column(Float, nullable=True)
    cpu_usage = Column(Float, nullable=True)
    ram_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, default=0.0)
    network_tx = Column(Float, default=0.0)
    network_rx = Column(Float, default=0.0)
    running_tasks = Column(Integer, default=0)
    gpu_utilization = Column(Float, default=0.0)
    vram_usage = Column(Float, default=0.0)
    gpu_temperature = Column(Float, nullable=True)
    network_latency_ms = Column(Float, default=1.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    worker = relationship("Worker", back_populates="metrics")

    def __init__(self, **kwargs):
        if "cpu_usage" in kwargs and "cpu_utilization" not in kwargs:
            kwargs["cpu_utilization"] = kwargs["cpu_usage"]
        elif "cpu_utilization" in kwargs and "cpu_usage" not in kwargs:
            kwargs["cpu_usage"] = kwargs["cpu_utilization"]
        super().__init__(**kwargs)


class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20))
    message = Column(Text)
    job_id = Column(Integer, nullable=True)
    worker_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class SchedulerDecision(Base):
    __tablename__ = "scheduler_decisions"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=True)
    chunk_id = Column(Integer, nullable=True)
    selected_worker_id = Column(Integer, nullable=True)
    strategy = Column(String(50), default="adaptive_hybrid")
    score = Column(Float, default=0.0)
    candidates_count = Column(Integer, default=0)
    reason = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        if "worker_id" in kwargs and "selected_worker_id" not in kwargs:
            kwargs["selected_worker_id"] = kwargs.pop("worker_id")
        if "algorithm" in kwargs and "strategy" not in kwargs:
            kwargs["strategy"] = kwargs.pop("algorithm")
        if "decision_reason" in kwargs and "reason" not in kwargs:
            kwargs["reason"] = kwargs.pop("decision_reason")
        super().__init__(**kwargs)

    @property
    def worker_id(self):
        return self.selected_worker_id

    @property
    def algorithm(self):
        return self.strategy

    @property
    def decision_reason(self):
        return self.reason


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    id = Column(Integer, primary_key=True, index=True)
    benchmark_uid = Column(String(50), unique=True, index=True, nullable=True)
    benchmark_type = Column(String(50), nullable=False)  # scalability, scheduler_comparison
    dataset_name = Column(String(100), default="sorting_100k")
    total_online_workers = Column(Integer, default=1)
    parameters = Column(JSON, nullable=True)
    results = Column(JSON, nullable=False)  # list of {workers, execution_time, speedup, efficiency, status}
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaskPackage(Base):
    """
    CoCompute 4.0 Universal Task Package Registry & Manifest.
    """
    __tablename__ = "task_packages"
    id = Column(Integer, primary_key=True, index=True)
    package_uid = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(20), default="1.0", nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(100), default="anonymous")
    runtime = Column(String(50), default="python:3.11")
    is_public = Column(Boolean, default=True)
    code_hash = Column(String(64), nullable=True)

    # 5-Hook Task Definition Source Code & Manifest Contract
    manifest = Column(JSON, nullable=False)        # Input, Execution, Parallelization, Aggregation contracts
    script_code = Column(Text, nullable=False)     # Python source code implementing BaseTaskDefinition
    entrypoint = Column(String(100), default="Task")
    
    # Pre-Flight Security & Compatibility Verification
    is_verified = Column(Boolean, default=False)
    compatibility_report = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    jobs = relationship("Job", back_populates="task_package")


class TaskPipeline(Base):
    """
    CoCompute 4.0 Multi-Stage Workflow & Conditional DAG Pipeline.
    """
    __tablename__ = "task_pipelines"
    id = Column(Integer, primary_key=True, index=True)
    pipeline_uid = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), default="idle") # idle, running, completed, failed
    dag_structure = Column(JSON, nullable=False) # Nodes, edges, conditions (PASS, FAIL, score > X)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stages = relationship("PipelineStage", back_populates="pipeline", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="pipeline")


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"
    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("task_pipelines.id", ondelete="CASCADE"), nullable=False)
    stage_name = Column(String(100), nullable=False)
    stage_order = Column(Integer, default=0)
    task_type = Column(String(50), nullable=False)
    task_package_id = Column(Integer, ForeignKey("task_packages.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(30), default="pending") # pending, running, completed, skipped, failed
    condition = Column(String(100), nullable=True) # e.g. "on_pass", "on_fail", "score > 90"
    stage_output = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pipeline = relationship("TaskPipeline", back_populates="stages")

