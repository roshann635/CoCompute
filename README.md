# CoCompute ⚡️
**Universal Autonomous Distributed Computing Platform (v3.1 Hardened)**

[![Tests](https://img.shields.io/badge/tests-98%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41cd52.svg)]()
[![React](https://img.shields.io/badge/dashboard-React%2019%20%2B%20TailwindCSS-61dafb.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

CoCompute is a universal, self-optimizing distributed computing platform designed for institutional, research, and enterprise workloads. It accepts computational tasks, automatically profiles and partitions workloads, schedules execution across heterogeneous LAN/cluster worker nodes, enforces data correctness via multiset hashing and mathematical validation, guarantees exactly-once acceptance via database-level atomic CAS, survives Master restarts without split-brain, and preserves immutable provenance for exact or equivalent reproduction.

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

## 🛡 Hardening Plan v3.1 — 10-Phase Specification

CoCompute operates under the fundamental invariant **`CORRECTNESS > STATUS`**.

### 1. Result Correctness
- **Sorting Multiset Verification**: Input element multiset is SHA-256 hashed at partition time; final aggregated output verifies exact multiset preservation, rejecting any dropped or corrupted items.
- **Matrix Multiplication Verification**: Complete row-index aggregation with dimension matching and submatrix reference validation.
- **Mergeable Statistics**: Streaming statistical summaries (count, sum, min, max, variance, moments) preserving mathematical identities across partitions.
- **Prime Generation Validation**: Sieve range partitioning with strict duplicate rejection, monotonic ordering, and primality spot-checks.
- **Universal Final Validation**: `validate_final()` executed for all task definitions before job completion.

### 2. Exactly-Once Acceptance & Provenance
- **Validate Partial First, Then Atomic CAS**: Partial task outputs are mathematically validated *before* attempting database acceptance via `UPDATE task_chunks SET accepted_attempt_id = :att WHERE id = :id AND accepted_attempt_id IS NULL`.
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

### 8. Multi-Suite Automated Verification
- Automated tests covering E2E correctness, fault injection, concurrency races, lease takeovers, and worker recovery.

### 9. ML / LLM Orchestration
- **Distributed Training (`ml_training`)**: Sharded PyTorch data-parallel training with loss curve convergence, shard synchronization, and model checkpointing (`minio://...`).
- **Distributed Inference (`distributed_inference`)**: Batch item slicing and sorted confidence-scored prediction merging.
- **LLM Fine-Tuning (`llm_finetune`)**: Step checkpointing, perplexity curve aggregation, and adapter checkpoint tracking.
- **GPU-Aware Scheduling**: Worker candidate filtering based on CUDA availability, GPU count, and minimum VRAM thresholds.

### 10. Institutional Scale & Operations
- **Data Locality Scoring**: Locality bonus (+30.0) awarded when worker node matches chunk data proximity.
- **Cluster Backpressure**: High-load queue thresholds with HTTP 429 Too Many Requests response.
- **Multi-User Quotas**: Role-based limits on concurrent jobs, GPU allocations, and max VRAM.
- **Worker Lifecycle State Machine**: Enforces `healthy -> degraded -> draining -> failed -> recovering -> benchmarking`.
- **Heartbeat Sequencing**: Sequence number (`heartbeat_seq`) tracking to ignore out-of-order or stale worker heartbeats.
- **Composite Database Indexes**: Optimized composite indexes on `task_chunks(task_id, status)`, `chunk_attempts(chunk_id, status)`, `workers(status, last_seen)`, and `audit_logs(actor, timestamp)`.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ (for Web Dashboard)
- Redis (optional, graceful in-memory fallback included)

### 1. Installation
```bash
git clone https://github.com/roshann635/CoCompute.git
cd CoCompute
pip install -r requirements.txt
```

### 2. Launch Master Node
```bash
uvicorn master.app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation is available at `http://localhost:8000/docs`.

### 3. Launch Worker Agent
```bash
# GUI Worker (PySide6 / Qt)
python -m worker.app.main --gui

# Headless Worker Daemon
python -m worker.app.main --master ws://localhost:8000 --worker-uid worker-01
```

### 4. Launch React Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Dashboard is available at `http://localhost:5173`.

---

## 🧪 Automated Test Suite

Run the full automated test suite:
```bash
python -m pytest tests/ -v
```

### Verification Results (98 passed / 98 tests):
```
============================== test session starts ==============================
rootdir: D:\CoCompute
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

## 📄 License
MIT License. Developed for enterprise and academic collaborative computing environments.
