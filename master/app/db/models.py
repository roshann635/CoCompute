from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, JSON, Text, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workers = relationship("Worker", back_populates="owner")
    jobs = relationship("Job", back_populates="owner")


class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    worker_uid = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="offline")  # online, offline, busy
    ip_address = Column(String(50))
    hostname = Column(String(255))
    cpu_cores = Column(Integer)
    cpu_utilization = Column(Float, default=0.0)
    ram_total = Column(Float)
    ram_usage = Column(Float, default=0.0)
    disk_total = Column(Float)
    disk_usage = Column(Float, default=0.0)
    network_speed = Column(Float, default=0.0)  # Mbps
    platform = Column(String(100))
    reliability_score = Column(Float, default=1.0)  # 0.0 to 1.0
    total_tasks_completed = Column(Integer, default=0)
    total_tasks_failed = Column(Integer, default=0)
    running_tasks = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="workers")
    task_chunks = relationship("TaskChunk", back_populates="worker")
    metrics = relationship("Metric", back_populates="worker")
    health_records = relationship("NodeHealthRecord", back_populates="worker")


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(255))
    description = Column(Text)
    job_type = Column(String(50))  # prime_generation, matrix_multiply, word_count, generic_python
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    params = Column(JSON)  # Original job parameters
    aggregated_result = Column(JSON, nullable=True)  # Final merged result
    submission_time = Column(DateTime(timezone=True), server_default=func.now())
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="jobs")
    tasks = relationship("Task", back_populates="job")


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
    task_id = Column(Integer, ForeignKey("tasks.id"))
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    chunk_index = Column(Integer)
    data_payload = Column(JSON)
    status = Column(String(20), default="pending")  # pending, assigned, running, completed, failed
    attempt_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    task = relationship("Task", back_populates="chunks")
    worker = relationship("Worker", back_populates="task_chunks")
    result = relationship("Result", back_populates="chunk", uselist=False)


class Result(Base):
    __tablename__ = "results"
    id = Column(Integer, primary_key=True, index=True)
    task_chunk_id = Column(Integer, ForeignKey("task_chunks.id"), unique=True)
    result_data = Column(JSON)
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
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    worker = relationship("Worker", back_populates="metrics")


class Log(Base):
    """System event log for audit and debugging."""
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20))  # INFO, WARNING, ERROR, CRITICAL
    source = Column(String(100))  # Module that generated the log
    message = Column(Text)
    log_metadata = Column(JSON, nullable=True)  # Extra contextual data
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class SchedulerDecision(Base):
    """Audit trail for every scheduling decision made."""
    __tablename__ = "scheduler_decisions"
    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("task_chunks.id"))
    worker_id = Column(Integer, ForeignKey("workers.id"))
    algorithm = Column(String(50))  # round_robin, resource_aware, ai_predictive
    score = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)  # Human-readable explanation
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class NodeHealthRecord(Base):
    """Periodic health snapshots for trend analysis."""
    __tablename__ = "node_health_records"
    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"))
    cpu_usage = Column(Float)
    ram_usage = Column(Float)
    disk_usage = Column(Float)
    temperature = Column(Float, nullable=True)
    network_speed = Column(Float, nullable=True)
    running_tasks = Column(Integer, default=0)
    is_healthy = Column(Boolean, default=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    worker = relationship("Worker", back_populates="health_records")
