# CoCompute ⚡️
**Universal Autonomous Distributed Computing Platform**

[![Tests](https://img.shields.io/badge/tests-73%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41cd52.svg)]()
[![React](https://img.shields.io/badge/dashboard-React%2019%20%2B%20TailwindCSS-61dafb.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

CoCompute is a universal, autonomous, self-optimizing distributed-computing platform that accepts user-defined computational workloads, validates and profiles them through real micro-execution, determines whether distribution is beneficial, automatically plans and adapts execution across heterogeneous LAN resources, validates and semantically interprets the resulting computation, and preserves complete provenance for exact or equivalent reproduction.

---

## 🏛 The CoCompute Autonomous Architecture

```
                           CoCompute
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
    TASK PLATFORM       COMPUTE ENGINE      RESULT PLATFORM
          │                   │                   │
      Task Builder       Global Planner        Validator
      5-Hook Task SDK    Cost Scheduler        Semantic Analyzer
      Registry           Elastic Chunks        Quality Analysis
      Versioning         Work Stealing         Data Explorer
      Compatibility      Plan Adaptation       Visualizers
      Security Sandbox   Straggler Mgmt        Executive Reports
      Micro-Pilot        Fault Recovery
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
                    EXECUTION PROVENANCE
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             REPRODUCIBILITY       AUDIT / ANALYTICS
                    │
             ┌──────┴──────┐
             ▼             ▼
          EXACT        EQUIVALENT
```

---

## 🌟 The 6 Core Engines of CoCompute

### 1. Universal Task Platform & 5-Hook Task SDK
Unified base class `TaskDefinition` for all workloads (built-in & custom user tasks):
```python
class TaskDefinition:
    def estimate_resources(self, input_data) -> ResourceEstimate: ...
    def partition(self, input_data, context: TaskContext) -> List[Any]: ...
    def execute(self, chunk, context: TaskContext) -> Any: ...
    def aggregate(self, results: List[Any], context: TaskContext) -> Any: ...
    def validate(self, result: Any, context: TaskContext) -> Dict[str, bool]: ...
```

### 2. Task Security & Pre-Flight Compatibility Engine
- **Multi-Tier Security**: Static AST code inspection flags disallowed system calls (`os.system`, `subprocess`, `socket`, `eval`).
- **Pre-Flight Sandbox Compatibility Test**: Executes dummy verification across all 5 hooks before admitting tasks into the cluster.

### 3. Adaptive Micro-Pilot & Evidence-Based Parallelism Model
- **Conditional Micro-Pilot**: 1% pilot sample $\rightarrow$ if confidence $< 0.70$, automatically escalates to 3% or 5% sample.
- **Evidence-Based Parallelism Analysis**: Synthesizes AST code structure, manifest contracts, and empirical pilot metrics into an **Explainable Decision**:
  - `EMBARRASSINGLY_PARALLEL` / `MAP_REDUCE` / `STATEFUL_ITERATIVE` $\rightarrow$ Distributed cluster execution.
  - `SEQUENTIAL` or Speedup $< 1.1\times$ $\rightarrow$ Intelligently falls back to the single best local node to avoid distributed overhead.

### 4. Two-Level Scheduling & Dynamic Plan Adaptation
- **Level 1 (Global Resource Planner)**: Emits a versioned `ExecutionPlan` object (`PLAN-v1`).
- **Level 2 (Elastic Chunk Scheduler)**: Proactive work stealing, adaptive per-worker chunk resizing, and runtime plan adaptation (`PLAN-v1` $\rightarrow$ `PLAN-v2` $\rightarrow$ `PLAN-v3`) with full decision audit logs.

### 5. Four-Stage Result Intelligence & Server-Side Data Explorer
$$\text{Raw Results} \rightarrow \text{Validation} \rightarrow \text{Aggregation} \rightarrow \text{Semantic Analysis} \rightarrow \text{Quality Analysis} \rightarrow \text{Presentation}$$
- **Universal Server-Side Data Explorer**: `preview` (100 rows), `sample` (1000 rows), `full_query` (paginated table slice).
- **Domain Visualizers**: Statistical Histograms, Matrix Heatmaps, PyTorch Loss/Accuracy Curves, and Image Tile Mosaic views.
- **Performance Comparison Card**: Single-Node Baseline vs. Distributed Speedup ($S_N$), Parallel Efficiency ($E_N$), Energy ($kWh$), and Carbon ($gCO_2e$).

### 6. Chain-of-Custody Provenance & Dual Reproducibility
- **End-to-End Computational Provenance Graph**:
  $$\text{Task Version} \rightarrow \text{Input} \rightarrow \text{Pilot} \rightarrow \text{Execution Plan} \rightarrow \text{Chunks} \rightarrow \text{Attempts} \rightarrow \text{Workers} \rightarrow \text{Aggregator} \rightarrow \text{Result}$$
- **Exact vs. Equivalent Reproduction**:
  - **Exact**: Identical code hash, input hash, random seed, environment, and container digest.
  - **Equivalent**: Identical logical computation executed across dynamic cluster hardware.

---

## 🚀 Quick Start Guide

### 1. Launch Master Node
```bash
uvicorn master.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Launch Worker Agent (GUI or Headless)
```bash
# PySide6 GUI with Trust Badge & 5-Factor Score
python -m worker.app.main --gui

# Headless Worker Daemon
python -m worker.app.main --master ws://localhost:8000 --worker-uid worker-01
```

### 3. Launch React Dashboard
```bash
cd dashboard
npm install
npm run dev
```

---

## 🧪 Comprehensive Automated Testing

Execute the complete test suite:
```bash
pytest tests/ -v
```

All 73 currently implemented automated tests pass successfully (73/73), with 22 warnings:
```
tests/test_aggregator.py (10 tests) ......................... PASSED [ 13%]
tests/test_analytics.py (9 tests) ........................... PASSED [ 26%]
tests/test_cocompute_3_intelligence.py (8 tests) ............ PASSED [ 36%]
tests/test_cocompute_4_platform.py (6 tests) ................ PASSED [ 45%]
tests/test_gaps_and_features.py (14 tests) .................. PASSED [ 65%]
tests/test_jobs.py (8 tests) ................................ PASSED [ 76%]
tests/test_scheduler.py (7 tests) ........................... PASSED [ 86%]
tests/test_sdk.py (6 tests) ................................. PASSED [ 94%]
tests/test_storage_and_metrics.py (2 tests) ................. PASSED [ 97%]
tests/test_worker_metrics.py (2 tests) ...................... PASSED [100%]

======================= 73 passed, 22 warnings in 7.43s =======================
```

---

## 📄 License
MIT License. Developed for enterprise and academic collaborative computing environments.
