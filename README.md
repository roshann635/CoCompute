# CoCompute ⚡️
**Universal Autonomous Distributed Computing Platform**

[![Tests](https://img.shields.io/badge/pytest-130%20passed-brightgreen.svg)]()
[![Selenium E2E](https://img.shields.io/badge/selenium%20E2E-16%2F16%20passed-success.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41cd52.svg)]()
[![React](https://img.shields.io/badge/dashboard-React%2019%20%2B%20TailwindCSS-61dafb.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-orange.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

CoCompute is an autonomous, self-optimizing distributed computing platform designed for institutional computer labs, research clusters, and enterprise workloads. It accepts large-scale computational tasks, automatically profiles and partitions workloads, schedules execution across heterogeneous LAN/cluster worker nodes, enforces data correctness via multiset hashing and mathematical validation, guarantees exactly-once acceptance via database-level atomic CAS, survives Master restarts without split-brain, and preserves immutable provenance for exact reproduction.

---

## 🌟 Key Capabilities

- **Zero-Friction Worker Deployment**: Deploy standalone worker executables (`CoComputeWorker.exe`) on Windows client PCs with zero Python installation required, or 1-click bash scripts on Linux.
- **LAN Auto-Discovery & Pairing**: UDP broadcast discovery (`Port 8001`) with automatic Master pairing and manual pairing code (`CC-XXXX`) fallbacks.
- **Correctness Over Status**: Cryptographic multiset verification (SHA-256) on partitioned data; chunks are validated mathematically before database acceptance.
- **Atomic Compare-And-Swap (CAS)**: Chunk result acceptance is guarded by atomic database queries, preventing duplicate, late, or speculative race conditions.
- **Heterogeneous Workload Presets**:
  - **Sorting**: Chunked sorting with K-way stream merge and multiset integrity checks.
  - **Prime Generation**: Segmented sieve partitioning with duplicate elimination and monotonicity validation.
  - **Matrix Multiplication**: Row/block partitioning with dimensional verification.
  - **ML Training & Inference**: Sharded PyTorch data-parallel training and batched model inference.
- **Modern Real-Time Dashboard**: High-performance React 19 UI with real-time WebSocket telemetry, cluster topology visualizer, node resource meters, and 1-click job dispatch.
- **Battle-Tested Resilience**: Straggler watchdog with speculative re-execution, dead worker detection, network partition recovery, and Master restart reconciliation.

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
         │ (Split-Brain) │       │ Headless CLI  │       │ (Temp→Rename) │
         ├───────────────┤       ├───────────────┤       ├───────────────┤
         │ CIE Scheduler │◄─────►│ Heartbeat Seq │       │ SHA-256 Check │
         │ (Active WS)   │       │ & Health State│       │ & Multiset    │
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
# Recommended launcher (runs host discovery and launches API)
python start_master.py

# Or directly via Uvicorn:
python -m uvicorn master.app.main:app --host 0.0.0.0 --port 8000
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 3. Launch React Management Dashboard

Open a separate terminal and start the web dashboard:

```bash
cd dashboard
npm install
npm run dev
```

The web dashboard will be available at **[http://localhost:5173](http://localhost:5173)**.

---

### 4. Deploying Worker Nodes

CoCompute workers can run on any machine in your local network with zero friction.

#### Option A: Portable Windows Standalone Binary (`.exe`)
For lab computers or systems without Python installed:
1. Build the standalone executable (or copy the generated bundle):
   ```cmd
   scripts\build_worker_windows.bat
   ```
2. Distribute `dist\windows\CoComputeWorker.exe` to client PCs via USB or network share.
3. Simply double-click `CoComputeWorker.exe` to launch the Desktop GUI or run:
   ```cmd
   CoComputeWorker.exe --cli --master-ip <MASTER_IP> --port 8000
   ```

#### Option B: Linux & macOS (1-Click Run)
On Linux/macOS worker machines:
```bash
chmod +x worker/run_worker.sh
./worker/run_worker.sh
```
*Automatically provisions a virtual environment, installs dependencies, and runs discovery.*

#### Option C: Universal Python Launcher
Run anywhere directly from source:
```bash
# Auto-detects GUI availability (PySide6) or falls back to headless CLI
python worker/start_worker.py

# Explicit Headless / Server CLI mode (specify Master IP):
python worker/start_worker.py --cli --master-ip 192.168.1.100 --port 8000

# Explicit Desktop GUI mode:
python worker/start_worker.py --gui
```

---

## 🏫 Computer Lab & Classroom Deployment

CoCompute is optimized for deployment in university computer labs and multi-machine environments:

1. **Start Master on Main PC**:
   - Run `python start_master.py` on the teacher/server machine.
   - Note the Master's IP address displayed on startup (e.g., `192.168.1.50`).
2. **Start Dashboard**:
   - Run `cd dashboard && npm run dev -- --host 0.0.0.0`.
   - Access from any browser at `http://192.168.1.50:5173`.
3. **Distribute Workers to Student PCs**:
   - Copy `worker/` or the portable `CoComputeWorker.exe` to client machines.
   - Run the executable or script. It will auto-discover the Master over UDP.
   - If UDP broadcast is restricted on your campus subnet, enter the Master IP in the GUI or via `--master-ip 192.168.1.50`.
4. **Submit Workloads**:
   - Use the **Quick Submit** presets in the dashboard (Sorting 25,000 items, Primes up to 100,000, etc.).
   - Watch the chunks distribute in real-time, execute across machines, and merge back seamlessly.

---

## 🛡 Platform Architecture & Hardening Specifications

CoCompute operates under the fundamental invariant **`CORRECTNESS > STATUS`**.

### 1. Result Correctness & Mathematical Verification
- **Sorting Multiset Verification**: Input multiset is SHA-256 hashed at partition time; final aggregated output verifies exact multiset preservation, rejecting any dropped, duplicated, or corrupted items.
- **Prime Generation Validation**: Sieve range partitioning with strict duplicate rejection, monotonic ordering, and primality spot-checks.
- **Matrix Multiplication Verification**: Row-index aggregation with dimension matching and submatrix reference validation.
- **Mergeable Statistics**: Streaming statistical summaries (count, sum, min, max, variance, moments) preserving mathematical identities across partitions.

### 2. Exactly-Once Acceptance & Provenance
- **Validate Partial First, Then Atomic CAS**: Partial task outputs are mathematically validated *before* attempting database acceptance via:
  ```sql
  UPDATE task_chunks SET accepted_attempt_id = :att WHERE id = :id AND accepted_attempt_id IS NULL;
  ```
- **Duplicate & Late-Attempt Rejection**: Late or redundant worker attempts are marked `ignored_duplicate` without altering accepted results.
- **Provenance API**: `GET /api/v1/jobs/{job_id}/provenance` returns complete attempt trees, worker assignments, duration metrics, and SHA-256 checksums.

### 3. Robust Task Execution & OS Limits Handling
- **In-Memory Registry**: Workload definitions are resolved in-memory first for ultra-low latency execution.
- **Temp-File Spillover**: Chunks with large payloads (>2KB) automatically spill to temporary JSON files to avoid Windows command-line character limits (`WinError 206`).
- **Active WebSocket Gating**: The scheduler validates an active, open WebSocket connection before committing task assignment, eliminating silent task stalls.

### 4. Master Recovery & Split-Brain Mitigation
- **Distributed Master Lease**: `MasterLease` model with dynamic lease acquisition, heartbeats, and expiry takeover to guarantee single-active-master operation.
- **Startup Incarnation & Recovery**: `CURRENT_INCARNATION_ID` stamps every attempt; `recover_after_restart()` resets orphaned assigned/running chunks back to `pending`.
- **Reconciliation Protocol**: Worker reconnect sends `CANCEL_STALE` WebSocket messages to terminate pre-restart worker attempts.

---

## 🧪 Automated Test Suite & E2E Verification

CoCompute includes a multi-tier automated test suite covering algorithmic correctness, fault injection, concurrency, cross-platform paths, deployment diagnostics, and full Selenium browser automation:

```bash
# Run backend, scheduler, and algorithmic test suite
python -m pytest tests/ -v

# Run Selenium End-to-End browser automation
python -m pytest tests/test_ui_e2e_selenium.py -v
```

### Verification Summary (130 Pytest Units & Integration Tests):
```
collected 130 items

tests/test_aggregator.py ..........                                       [  7%]
tests/test_ai_scheduler.py .                                              [  8%]
tests/test_analytics.py .........                                         [ 15%]
tests/test_api.py ..........                                              [ 23%]
tests/test_auth.py .......                                                [ 28%]
tests/test_cocompute_1_core.py ......                                     [ 33%]
tests/test_cocompute_2_advanced.py ......                                 [ 37%]
tests/test_cocompute_3_intelligence.py ......                             [ 42%]
tests/test_cocompute_4_platform.py ......                                 [ 46%]
tests/test_cross_platform_paths.py ...                                    [ 49%]
tests/test_demo_mode.py ....                                              [ 52%]
tests/test_deployment_diagnostics.py ....                                 [ 55%]
tests/test_e2e_correctness.py ....                                        [ 58%]
tests/test_failure_policy.py ..                                           [ 60%]
tests/test_fault_injection.py .                                           [ 61%]
tests/test_gaps_and_features.py .........                                 [ 68%]
tests/test_institutional_scale.py .......                                 [ 73%]
tests/test_jobs.py ...                                                    [ 75%]
tests/test_master_discovery.py ...                                        [ 78%]
tests/test_master_leadership.py ...                                       [ 80%]
tests/test_ml_orchestration.py ....                                       [ 83%]
tests/test_scheduler.py ........                                          [ 89%]
tests/test_scheduler_concurrency.py ..                                    [ 91%]
tests/test_sdk.py ......                                                  [ 95%]
tests/test_storage_and_metrics.py ..                                      [ 97%]
tests/test_worker_capabilities.py ...                                     [ 99%]
tests/test_worker_metrics.py ..                                           [100%]

============================ 130 passed in 23.40s =============================
```

### 🌐 Selenium E2E Browser Test Suite (16/16 Passed — 100% Pass Rate)
Full live browser automation tests running against Chrome headless driver:
- **API Health Check**: Master connection & worker registration verification
- **Authentication**: User registration, login & JWT token retention
- **Overview & Nodes**: Live worker card inspection, telemetry meters, and node hardware specs
- **WebSocket Telemetry**: Bi-directional real-time push streaming verification
- **Workload Execution**: Sorting job (25k elements) & Prime job submission and execution
- **Result Integrity**: Verification of computed result previews and cryptographic multiset hashes
- **Tab Navigation & Modals**: Complete verification across all 8 dashboard tabs

*Detailed execution report and screenshots available in [`tests/selenium_e2e_report.md`](./tests/selenium_e2e_report.md).*

---

## 📖 In-Depth Documentation

Detailed guides are available in the [`docs/`](./docs) directory:
- [Windows Worker Deployment Guide](./docs/WINDOWS_WORKER.md)
- [Linux & macOS Worker Deployment Guide](./docs/LINUX_WORKER.md)
- [Multi-Machine Lab Deployment Guide](./docs/WORKER_DEPLOYMENT.md)
- [Portable Architecture Design](./docs/PORTABLE_ARCHITECTURE.md)
- [Worker Troubleshooting & Diagnostics](./docs/WORKER_TROUBLESHOOTING.md)
- [Demo Mode & Simulated Cluster Guide](./docs/DEMO_MODE.md)

---

## 📁 Repository Structure

```
CoCompute/
├── master/                   # Master Node / Central Intelligence Engine (CIE)
│   ├── app/
│   │   ├── api/              # REST Endpoints (Jobs, Workers, Analytics, etc.)
│   │   ├── core/             # Configuration, Security, Auth, Logging
│   │   ├── db/               # SQLAlchemy Models, Database Session
│   │   ├── engine/           # Scheduler, Aggregator, Recovery Engine
│   │   ├── network/          # WebSocket Manager & UDP Discovery
│   │   └── schemas/          # Pydantic Schemas & DTOs
│   ├── Dockerfile
│   └── requirements.txt
│
├── worker/                   # Worker Node Agent
│   ├── app/
│   │   ├── diagnostics/      # Health & Network Diagnostic Probes
│   │   ├── execution/        # Task Executor, Sandbox, Task Registry
│   │   ├── monitor/          # Hardware Capability & Metrics Collector
│   │   ├── network/          # WebSocket Client & LAN Discovery
│   │   └── ui/               # PySide6 Desktop GUI Interface
│   ├── start_worker.py       # Cross-platform universal runner
│   ├── run_worker.bat        # Windows 1-click launcher
│   ├── run_worker.sh         # Linux / macOS 1-click launcher
│   └── demo_cluster.py       # Simulated multi-worker cluster runner
│
├── dashboard/                # Modern React 19 Management Dashboard
│   ├── src/                  # React Components, State, WebSocket telemetry
│   ├── package.json
│   └── vite.config.js
│
├── packaging/                # Binary packaging specifications
│   └── windows/              # PyInstaller spec for CoComputeWorker.exe
│
├── scripts/                  # Standalone build & deployment scripts
│   ├── build_worker_windows.bat
│   ├── build_worker_windows.ps1
│   └── build_worker_linux.sh
│
├── docs/                     # Comprehensive deployment & architecture guides
├── tests/                    # 115-Item Comprehensive Test Suite
├── docker-compose.yml        # Multi-container orchestration (Master, Redis, MinIO)
├── start_master.py           # Master node auto-discovery runner
├── requirements.txt          # Unified project requirements
├── .gitignore                # Production Git exclusion rules
└── README.md                 # Project documentation
```

---

## 📄 License

Distributed under the **MIT License**. Developed for enterprise, institutional, and academic collaborative computing environments.
