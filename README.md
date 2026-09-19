# CoCompute ⚡️
**Universal Autonomous Distributed Computing Platform**

[![Tests](https://img.shields.io/badge/tests-98%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41cd52.svg)]()
[![React](https://img.shields.io/badge/dashboard-React%2019%20%2B%20TailwindCSS-61dafb.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

CoCompute is an autonomous, self-optimizing distributed computing platform designed for institutional, research, and enterprise workloads. It accepts computational tasks, automatically profiles and partitions workloads, schedules execution across heterogeneous LAN/cluster worker nodes, enforces data correctness via multiset hashing and mathematical validation, guarantees exactly-once acceptance via database-level atomic CAS, survives Master restarts without split-brain, and preserves immutable provenance for exact or equivalent reproduction.

---

## 🏛 System Architecture

```
                                  CoCompute Cluster
                                         │
                 ┌───────────────────────┼───────────────────────┐
                 │                       │                       │
                 ▼                       ▼                       ▼
          MASTER NODE (CIE)        WORKER FLEET            DATA & ARTIFACTS
                 │                       │                       │
         ┌───────┴───────┐       ┌───────┴───────┐       ┌───────┴───────┐
         │ Master Lease  │       │ PySide6 GUI / │       │ Atomic Store  │
         │ (Split-Brain) │       │ Headless Node │       │ (Temp→Rename) │
         ├───────────────┤       ├───────────────┤       ├───────────────┤
         │ CIE Scheduler │◄─────►│ Heartbeat Seq │       │ SHA-256 Check │
         │ (Optimistic)  │       │ & Health State│       │ & Provenance  │
         ├───────────────┤       ├───────────────┤       ├───────────────┤
         │ Validate First│       │ Speculative & │       │ Reconciliation│
         │ & Atomic CAS  │       │ Sandboxed Exec│       │ Engine        │
         └───────────────┘       └───────────────┘       └───────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (tested on Python 3.10, 3.11, 3.12, 3.13)
- **Node.js 18+** (for the Web Dashboard)
- **Redis** *(Optional — system features built-in in-memory fallback)*

---

### 1. Repository Setup & Dependencies

Clone the repository and install dependencies:

```bash
git clone https://github.com/roshann635/CoCompute.git
cd CoCompute
pip install -r requirements.txt
```

*(Optional)* Copy the example environment configuration:
```bash
cp .env.example .env
```

---

### 2. Launch Master Node (Central Intelligence Engine)

Start the Master API and scheduling engine:

```bash
uvicorn master.app.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 3. Launch Worker Node (Cross-Platform)

CoCompute workers support automatic LAN master discovery, zero configuration, and automatic dependency installation.

#### 🪟 Windows (1-Click Run)
Double-click `worker\run_worker.bat` or run:
```cmd
worker\run_worker.bat
```

#### 🐧 Linux & 🍎 macOS (1-Click Run)
```bash
chmod +x worker/run_worker.sh
./worker/run_worker.sh
```

#### 🐍 Universal Python Launcher
Run anywhere directly via Python:
```bash
# Auto-detects GUI availability (PySide6) or falls back to headless
python worker/start_worker.py

# Explicit Desktop GUI mode:
python worker/start_worker.py --gui

# Explicit Headless / Server CLI mode:
python worker/start_worker.py --cli

# Explicit remote Master IP / Port:
python worker/start_worker.py --master ws://192.168.1.100:8000 --worker-uid worker-01
```

---

### 4. Launch React Management Dashboard

Open a new terminal and run:

```bash
cd dashboard
npm install
npm run dev
```

The web dashboard will be available at **[http://localhost:5173](http://localhost:5173)**.

---

## 🛡 Platform Architecture & Hardening Specifications

CoCompute operates under the fundamental invariant **`CORRECTNESS > STATUS`**.

### 1. Result Correctness & Mathematical Verification
- **Sorting Multiset Verification**: Input multiset is SHA-256 hashed at partition time; final aggregated output verifies exact multiset preservation, rejecting any dropped, duplicated, or corrupted items.
- **Matrix Multiplication Verification**: Row-index aggregation with dimension matching and submatrix reference validation.
- **Mergeable Statistics**: Streaming statistical summaries (count, sum, min, max, variance, moments) preserving mathematical identities across partitions.
- **Prime Generation Validation**: Sieve range partitioning with strict duplicate rejection, monotonic ordering, and primality spot-checks.
- **Universal Final Validation**: `validate_final()` executed for all task definitions before job completion.

### 2. Exactly-Once Acceptance & Provenance
- **Validate Partial First, Then Atomic CAS**: Partial task outputs are mathematically validated *before* attempting database acceptance via:
  ```sql
  UPDATE task_chunks SET accepted_attempt_id = :att WHERE id = :id AND accepted_attempt_id IS NULL;
  ```
- **Duplicate & Late-Attempt Rejection**: Late or redundant worker attempts are marked `ignored_duplicate` without altering accepted results.
- **Provenance API**: `GET /api/v1/jobs/{job_id}/provenance` returns complete attempt trees, worker assignments, duration metrics, and SHA-256 checksums.

### 3. Worker Failure Recovery & Speculation
- **Independent Retry Budgets**: `normal_attempt_count` and `speculative_attempt_count` are tracked independently to ensure speculative execution never exhausts fault-retry budgets.
- **Failure Classification**: Failures are classified into `NON_RETRYABLE`, `INFRA_FAILURE`, and `APP_FAILURE`.
- **Worker Sessions**: Ephemeral `session_id` per connection isolates worker reconnections.

### 4. Master Recovery & Split-Brain Mitigation
- **Distributed Master Lease**: `MasterLease` model with dynamic lease acquisition, heartbeats, and expiry takeover to guarantee single-active-master operation.
- **Startup Incarnation & Recovery**: `CURRENT_INCARNATION_ID` stamps every attempt; `recover_after_restart()` resets orphaned assigned/running chunks back to `pending`.
- **Reconciliation Protocol**: Worker reconnect sends `CANCEL_STALE` WebSocket messages to terminate pre-restart worker attempts.

### 5. Concurrency-Safe Scheduling & Reservations
- **Optimistic Concurrency Locking**: Atomic version checking (`TaskChunk.version`) prevents scheduler race conditions.
- **Resource Reservations & Rollback**: CPU cores, RAM, and GPU VRAM are reserved on worker assignment; reservations automatically roll back if WebSocket dispatch fails.
- **Leadership-Gated Loop**: Scheduler checks leadership lease on every tick before dispatching work.

### 6. Security, Protocols & Audit
- **Structured Audit Logging**: Comprehensive `AuditLog` records actor, role, action, resource, IP, and outcome.
- **Protocol Versioning**: Control and execution messages include `protocol_version: "1.0"`.
- **Role-Based Access Control (RBAC)**: Role validation dependencies (`require_role()`, `require_admin()`).

### 7. Durable Result Artifacts & Reconciliation
- **Atomic File Store Pipeline**: Temporary file write $\rightarrow$ `fsync` $\rightarrow$ checksum verification $\rightarrow$ atomic rename $\rightarrow$ `ResultArtifact` record commit.
- **Cancellation Workflow**: `POST /api/v1/jobs/{job_id}/cancel` cleans pending/running chunks and releases worker reservations.
- **Artifact Reconciliation**: Periodic background audit reconciling disk files with database entries.

### 8. ML / LLM Orchestration
- **Distributed Training (`ml_training`)**: Sharded PyTorch data-parallel training with loss curve convergence, shard synchronization, and model checkpointing (`minio://...`).
- **Distributed Inference (`distributed_inference`)**: Batch item slicing and sorted confidence-scored prediction merging.
- **LLM Fine-Tuning (`llm_finetune`)**: Step checkpointing, perplexity curve aggregation, and adapter checkpoint tracking.
- **GPU-Aware Scheduling**: Worker candidate filtering based on CUDA availability, GPU count, and minimum VRAM thresholds.

### 9. Institutional Scale & Operations
- **Data Locality Scoring**: Locality bonus (+30.0) awarded when worker node matches chunk data proximity.
- **Cluster Backpressure**: High-load queue thresholds with HTTP 429 Too Many Requests response.
- **Multi-User Quotas**: Role-based limits on concurrent jobs, GPU allocations, and max VRAM.
- **Worker Lifecycle State Machine**: Enforces `healthy -> degraded -> draining -> failed -> recovering -> benchmarking`.
- **Heartbeat Sequencing**: Sequence number (`heartbeat_seq`) tracking to ignore out-of-order or stale worker heartbeats.

---

## 🧪 Automated Test Suite

CoCompute includes a comprehensive multi-tier test suite covering correctness, fault injection, concurrency, and intelligence:

```bash
python -m pytest tests/ -v
```

### Verification Summary (98 passed / 98 tests):
```
collected 98 items

tests/test_ai_scheduler.py .                                              [  1%]
tests/test_analytics.py .........                                         [ 10%]
tests/test_api.py ..........                                              [ 20%]
tests/test_auth.py .......                                                [ 27%]
tests/test_cocompute_1_core.py ......                                     [ 33%]
tests/test_cocompute_2_advanced.py ......                                 [ 39%]
tests/test_cocompute_3_intelligence.py ......                             [ 45%]
tests/test_cocompute_4_platform.py ....                                   [ 50%]
tests/test_e2e_correctness.py ....                                        [ 54%]
tests/test_failure_policy.py ..                                           [ 56%]
tests/test_fault_injection.py .                                           [ 57%]
tests/test_gaps_and_features.py .........                                 [ 66%]
tests/test_institutional_scale.py .......                                 [ 73%]
tests/test_jobs.py ...                                                    [ 76%]
tests/test_master_leadership.py ...                                       [ 80%]
tests/test_ml_orchestration.py ....                                       [ 84%]
tests/test_scheduler.py ........                                          [ 92%]
tests/test_scheduler_concurrency.py ..                                    [ 94%]
tests/test_sdk.py ......                                                  [100%]

====================== 98 passed, 31 warnings in 11.24s =======================
```

---

## 📁 Repository Structure

```
CoCompute/
├── master/                   # Master Node / Central Intelligence Engine (CIE)
│   ├── app/
│   │   ├── api/              # REST Endpoints (Jobs, Auth, Analytics, Workers, etc.)
│   │   ├── core/             # Configuration, Security, Auth, Logging
│   │   ├── db/               # SQLAlchemy Models, Session, Migration schemas
│   │   ├── engine/           # Pluggable Schedulers, Aggregator, Fault Recovery
│   │   ├── network/          # WebSocket Manager & UDP Discovery
│   │   └── schemas/          # Pydantic Schemas & DTOs
│   ├── Dockerfile
│   └── requirements.txt
│
├── worker/                   # Worker Node Agent
│   ├── app/
│   │   ├── execution/        # Task Executor, Sandbox, Docker Engine
│   │   ├── monitor/          # System Metrics Collector (CPU, RAM, GPU)
│   │   ├── network/          # WebSocket Client & LAN Discovery
│   │   └── ui/               # PySide6 Desktop GUI Interface
│   ├── start_worker.py       # Cross-platform universal runner
│   ├── run_worker.bat        # Windows 1-click launcher
│   ├── run_worker.sh         # Linux / macOS launcher
│   └── requirements.txt
│
├── dashboard/                # Modern React 19 Management Dashboard
│   ├── src/                  # React Components, State, WebSocket client
│   ├── package.json
│   └── vite.config.js
│
├── tests/                    # 98-Item Comprehensive Test Suite
├── docker-compose.yml        # Multi-container orchestration (Master, Redis, MinIO)
├── requirements.txt          # Unified project requirements
├── .gitignore                # Comprehensive Git exclusion rules
└── README.md                 # Project documentation
```

---

## 📄 License

Distributed under the **MIT License**. Developed for enterprise, institutional, and academic collaborative computing environments.
