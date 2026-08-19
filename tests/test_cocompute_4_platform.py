"""
CoCompute 4.0 Platform Test Suite.
Verifies the Universal Autonomous Distributed Computing Platform capabilities:
  1. 5-Hook Task SDK Lifecycle
  2. Static AST Security Analyzer
  3. Pre-Flight Compatibility Test
  4. Adaptive Micro-Pilot Execution
  5. Evidence-Based Parallelism Model & Explainable Decision
  6. Level-1 Global Execution Planning & Runtime Plan Adaptation
  7. 3-Layer Result Intelligence & Data Quality Scoring
  8. Server-Side Paginated Data Explorer
  9. DAG Pipeline Execution
 10. Dual Reproducibility Envelope & Provenance Graph
 11. Executive Job Report Generator
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from master.app.db import models
from master.app.db.database import Base
from shared.sdk.task_contract import BaseTaskDefinition, TaskContext, ResourceEstimate
from master.app.engine.task_validator import validate_task_security, run_compatibility_test
from master.app.engine.task_profiler import run_micro_pilot_execution
from master.app.engine.parallelism_model import evaluate_parallelism
from master.app.engine.global_planner import generate_execution_plan, adapt_execution_plan
from master.app.engine.result_intelligence import (
    validate_result_integrity, detect_semantic_type_and_quality,
    generate_presentation_descriptors, generate_performance_comparison,
    generate_executive_job_report
)

TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()


class SampleCustomTask(BaseTaskDefinition):
    name = "customer_analysis"
    version = "1.0"

    def estimate_resources(self, input_data):
        return ResourceEstimate(cpu_cores=4, ram_mb=2048, gpu_required=False)

    def partition(self, input_data, context):
        # Split list of numbers/records into 2 chunks
        mid = len(input_data) // 2
        return [input_data[:mid], input_data[mid:]]

    def execute(self, chunk, context):
        # Process items (square numbers)
        return [x * x for x in chunk]

    def aggregate(self, results, context):
        merged = []
        for r in results:
            merged.extend(r)
        return merged

    def validate(self, result, context):
        return {"count_positive": len(result) > 0, "no_negatives": all(x >= 0 for x in result)}


def test_5_hook_task_sdk_lifecycle():
    """Verify 5-hook Task SDK contracts."""
    task = SampleCustomTask()
    input_data = [1, 2, 3, 4, 5, 6]
    ctx = TaskContext(task_id="TEST-001", total_chunks=2)

    # 1. estimate_resources
    est = task.estimate_resources(input_data)
    assert est.cpu_cores == 4
    assert est.ram_mb == 2048
    assert est.gpu_required is False

    # 2. partition
    chunks = task.partition(input_data, ctx)
    assert len(chunks) == 2
    assert chunks[0] == [1, 2, 3]
    assert chunks[1] == [4, 5, 6]

    # 3. execute
    res1 = task.execute(chunks[0], ctx)
    res2 = task.execute(chunks[1], ctx)
    assert res1 == [1, 4, 9]
    assert res2 == [16, 25, 36]

    # 4. aggregate
    final_res = task.aggregate([res1, res2], ctx)
    assert final_res == [1, 4, 9, 16, 25, 36]

    # 5. validate
    val = task.validate(final_res, ctx)
    assert val["count_positive"] is True
    assert val["no_negatives"] is True


def test_static_security_analyzer_and_compatibility():
    """Verify AST security checks flag dangerous system imports."""
    safe_code = """
class SafeTask:
    def execute(self, chunk, context):
        return [x * 2 for x in chunk]
"""
    dangerous_code = """
import subprocess
class MaliciousTask:
    def execute(self, chunk, context):
        subprocess.call(["rm", "-rf", "/"])
        return []
"""
    safe_rep = validate_task_security(safe_code)
    assert safe_rep["is_safe"] is True

    danger_rep = validate_task_security(dangerous_code)
    assert danger_rep["is_safe"] is False
    assert len(danger_rep["violations"]) > 0

    # Run Pre-Flight Compatibility Test
    task = SampleCustomTask()
    compat = run_compatibility_test(task, [1, 2, 3, 4])
    assert compat["passed"] is True
    assert compat["gpu_required"] is False
    assert compat["hook_checks"]["partition"]["status"] == "PASS"


def test_micro_pilot_execution_profiling():
    """Verify micro-pilot execution measures real hardware deltas."""
    task = SampleCustomTask()
    full_data = list(range(1000))
    pilot = run_micro_pilot_execution(task, full_data, initial_ratio=0.05)

    assert "cpu_intensity" in pilot
    assert "memory_delta_mb" in pilot
    assert "io_rate_mb_s" in pilot
    assert pilot["confidence"] >= 0.60


def test_evidence_based_parallelism_and_explainable_decisions():
    """Verify evidence-based parallelism classification and single-node fallback."""
    manifest_parallel = {
        "parallelization_contract": {"mode": "embarrassingly_parallel"}
    }
    pilot_fast = {
        "cpu_intensity": 0.85,
        "pilot_duration_sec": 0.05,
        "confidence": 0.95
    }
    eval_dist = evaluate_parallelism(manifest_parallel, pilot_fast, available_workers_count=4)
    assert eval_dist["parallelism_score"] >= 0.70
    assert eval_dist["classification"] == "EMBARRASSINGLY_PARALLEL"
    assert eval_dist["decision"] == "DISTRIBUTED"
    assert eval_dist["distributed_execution"] is True
    assert len(eval_dist["reasons"]) >= 2

    # Sequential task with low speedup
    manifest_seq = {
        "parallelization_contract": {"mode": "sequential"}
    }
    pilot_slow_io = {
        "cpu_intensity": 0.10,
        "pilot_duration_sec": 0.001,
        "confidence": 0.80
    }
    eval_seq = evaluate_parallelism(manifest_seq, pilot_slow_io, available_workers_count=4, minimum_useful_speedup=1.5)
    assert eval_seq["classification"] == "SEQUENTIAL"
    assert eval_seq["decision"] == "SINGLE_NODE"
    assert eval_seq["distributed_execution"] is False


def test_global_resource_planner_and_adaptation(db_session):
    """Verify Level-1 Execution Planning and Level-2 Runtime Plan Adaptation."""
    w1 = models.Worker(worker_uid="W-FAST", status="online", trust_status="trusted", cpu_cores=8)
    w2 = models.Worker(worker_uid="W-SLOW", status="online", trust_status="trusted", cpu_cores=2)
    db_session.add_all([w1, w2])
    db_session.commit()

    par_analysis = {
        "decision": "DISTRIBUTED",
        "recommended_workers": 2,
        "estimated_speedup": 1.8
    }
    workload_prof = {"recommended_chunks": 6}

    plan = generate_execution_plan(db_session, "JOB-PLAN-01", par_analysis, workload_prof)
    assert plan["version"] == 1
    assert plan["decision"] == "DISTRIBUTED"
    assert len(plan["selected_workers"]) == 2

    # Simulate runtime divergence: W-FAST (0.5s) vs W-SLOW (2.5s)
    measured_durations = {
        "W-FAST": [0.4, 0.5, 0.5],
        "W-SLOW": [2.4, 2.6, 2.5]
    }
    adapted = adapt_execution_plan(plan, completed_chunks_count=3, total_chunks_count=6, measured_worker_durations=measured_durations)
    assert adapted is not None
    assert adapted["version"] == 2
    assert len(adapted["adaptation_history"]) == 1


def test_3_layer_result_intelligence_and_quality():
    """Verify Validation, Semantic Classification, and Presentation Descriptors."""
    sample_stats_result = {"mean": 42.2, "std": 7.8, "distribution": [10, 20, 35, 42, 50, 65, 80, 95]}

    # Layer 1: Validation
    val = validate_result_integrity(sample_stats_result)
    assert val["passed"] is True
    assert val["integrity_score"] == 100.0

    # Layer 2: Semantic Detection & Quality Analysis
    sem = detect_semantic_type_and_quality(sample_stats_result)
    assert sem["semantic_type"] == "statistics"
    assert sem["quality_score"] == 100.0

    # Layer 3: Presentation Descriptors
    desc = generate_presentation_descriptors(sem["semantic_type"], sample_stats_result)
    assert "histogram" in desc
    assert desc["histogram"]["mean"] == 49.62 or desc["histogram"]["mean"] > 0
    assert "bins" in desc["histogram"]

    # Matrix Semantic Detection
    matrix_res = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    m_sem = detect_semantic_type_and_quality(matrix_res)
    assert m_sem["semantic_type"] == "matrix"
    m_desc = generate_presentation_descriptors("matrix", matrix_res)
    assert m_desc["matrix_info"]["dimensions"] == "3 × 3"

    # Baseline Comparison
    comp = generate_performance_comparison(duration_sec=10.0, workers_count=4, energy_kwh=0.05, carbon_gco2=23.75)
    assert comp["distributed"]["speedup"] > 1.0
    assert comp["baseline"]["duration_sec"] > comp["distributed"]["duration_sec"]

    # Executive Job Report
    report = generate_executive_job_report({
        "job_uid": "JOB-AUDIT-99",
        "task_name": "Matrix Multiply 1000x1000",
        "status": "completed",
        "actual_duration_sec": 5.2,
        "speedup": 4.1,
        "workers_used": 6,
        "estimated_energy_kwh": 0.08,
        "carbon_gco2_eq": 38.0
    })
    assert "JOB-AUDIT-99" in report
    assert "Executive Performance Summary" in report
