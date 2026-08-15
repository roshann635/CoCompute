# CoCompute ⚡️
**Enterprise Collaborative Distributed Computing Framework for Intelligent Resource Sharing and Heterogeneous Task Execution**

[![Tests](https://img.shields.io/badge/tests-59%20passed%20(100%25)-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41cd52.svg)]()
[![React](https://img.shields.io/badge/dashboard-React%2019%20%2B%20Vite-61dafb.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

CoCompute is an enterprise-grade distributed computing platform that aggregates computational resources from multiple heterogeneous devices (CPUs, GPUs, edge nodes) and orchestrates them into a unified, high-performance distributed computing cluster.

---

## 📑 Table of Contents
- [Architecture Overview](#-architecture-overview)
- [Key Systems & 7 Core Architectural Gaps](#-key-systems--7-core-architectural-gaps)
- [CoCompute Unified Intelligence Engine (CIE)](#-cocompute-unified-intelligence-engine-cie)
- [Distributed Task SDK & 11 Standard Tasks](#-distributed-task-sdk--11-standard-tasks)
- [Real-Cluster Benchmarking Suite](#-real-cluster-benchmarking-suite)
- [Multi-User Institutional Quotas & Projects](#-multi-user-institutional-quotas--projects)
- [Worker Agent & PySide6 GUI](#-worker-agent--pyside6-gui)
- [React Control Center Dashboard](#-react-control-center-dashboard)
- [Quick Start Guide](#-quick-start-guide)
- [REST & WebSocket API Reference](#-rest--websocket-api-reference)
- [Testing & Verification](#-testing--verification)

---

## 🏛 Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                   React Dashboard (Vite + TailwindCSS)                 │
│         Live WebSockets • Provenance • Benchmarks • Projects           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST / WebSocket Push
┌───────────────────────────────────▼────────────────────────────────────┐
│                       Master Node (FastAPI Core)                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ CIE Scheduler Engine (7 Pluggable Strategies + AI Predictive)     │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────┐ ┌──────────────────────┐ ┌─────────────┐  │
│  │ Redis Priority Queues   │ │ Fault Recovery (<1s) │ │ Aggregator  │  │
│  │ & Pub/Sub Rescheduling  │ │ SUSPECTED -> FAILED  │ │ File Store  │  │
│  └─────────────────────────┘ └──────────────────────┘ └─────────────┘  │
│  ┌─────────────────────────┐ ┌──────────────────────┐ ┌─────────────┐  │
│  │ MinIO S3 Object Storage │ │ Token HMAC Auth (GAP7│ │ UDP Discover│  │
│  │ Artifact Bundler (.zip) │ │ SHA-256 Verifier     │ │ Port 9999   │  │
│  └─────────────────────────┘ └──────────────────────┘ └─────────────┘  │
│                   PostgreSQL / SQLite Database Layer                   │
└───────────────────────────────────┬────────────────────────────────────┘
         ▲                          │ WebSocket + Token
         │ UDP Broadcast (9999)     │ Dispatched MinIO References
         │                          ▼
┌────────┴───────────────────────────────────────────────────────────────┐
│               Worker Agents (PySide6 GUI / CLI Daemon)                 │
│  ┌────────────────────────┐ ┌───────────────────┐ ┌─────────────────┐  │
│  │ Docker Sandbox Engine  │ │ GPU / VRAM Monitor│ │ Local SQLite    │  │
│  │ --network=none limits  │ │ Telemetry Poller  │ │ History Ledger  │  │
│  └────────────────────────┘ └───────────────────┘ └─────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡 Key Systems & 7 Core Architectural Gaps

CoCompute fulfills all production requirements and mandatory isolation/security gaps:

### 1. Docker Containerized Execution Sandbox (GAP 1)
- **Module**: `worker/executor/docker_executor.py`
- **Isolation**: Every chunk executes inside a standalone container with `--network=none`, `--cpus`, `--memory=1024m`, input mount `-v {in}:/input:ro`, output mount `-v {out}:/output:rw`, and optional GPU passthrough `--gpus "device=N"`.
- **Prebuilt Task Images**: Dedicated Dockerfiles in `docker/task_images/` for sort, matrix, statistics, search, word count, image processing, PyTorch ML, LLM fine-tuning, cipher, and generic scripts.

### 2. MinIO S3 Object Storage & Artifact Bundles (GAP 2)
- **Module**: `master/app/services/minio_service.py`
- **Buckets**: `chunks`, `results`, `checkpoints`, `artifacts`, `models`.
- **References**: Distributes `minio://...` object URIs rather than raw heavy payloads over WebSocket.
- **Per-Job Artifact Bundle Generator**: Compiles `.json`, `.csv`, `.txt`, and full `.zip` archives containing `config.json`, `timeline.json`, `provenance.json`, and `final_result.json`.

### 3. Redis Job Queue & Pub/Sub Rescheduling (GAP 3)
- **Module**: `master/app/services/queue_service.py`
- **Intake**: Priority queues `jobs:high` and `jobs:normal`.
- **Event-Driven**: Publishes instant rescheduling events to Redis channel `cocompute:reschedule` without polling database tables in loops.

### 4. Immediate SUSPECTED State & Rapid Fault Recovery (GAP 4)
- **Module**: `master/app/engine/fault_detector.py`
- **Recovery (< 1s)**: On `WebSocketDisconnect`, immediately marks the worker as `SUSPECTED`, resets orphaned chunks to `pending`, increments attempt provenance, and triggers Redis pub/sub rescheduling.
- **Timeout Transition**: Transitions `SUSPECTED` → `FAILED` after 15s heartbeat timeout.

### 5. Duplicate Attempt Rejection (GAP 5)
- **Database Model**: `TaskChunk.accepted_attempt_id`
- **Protection**: If an attempt has been accepted or a stale/duplicate result arrives for a different attempt, it is discarded to prevent aggregation corruption.

### 6. Cryptographic SHA-256 Checksum Verification (GAP 6)
- **Module**: `master/app/services/integrity.py`
- **Validation**: Deterministic SHA-256 verification on every worker result before DB commit or aggregation. Checksum mismatches immediately trigger chunk rescheduling.

### 7. Worker HMAC Token Authentication (GAP 7)
- **Module**: `master/app/services/auth_service.py`
- **Validation**: Workers authenticate with HMAC-SHA256 tokens derived from `worker_uid` and cluster secret (`COCOMPUTE_WORKER_SECRET`). Rejects unauthorized nodes with WebSocket code `4001`.

---

## 🧠 CoCompute Unified Intelligence Engine (CIE)

The scheduler supports 7 pluggable strategies with dynamic switching via the dashboard:

| Strategy ID | Name | Core Logic & Weighted Formula | Best Used For |
|---|---|---|---|
| `capacity_based` | Capacity Based | Scores nodes by CPU cores, RAM, and reliability, penalized by queue & utilization | Heterogeneous clusters |
| `round_robin` | Round Robin | Deterministic cyclic distribution across active nodes | Uniform CPU tasks |
| `least_loaded` | Least Loaded | Selects node with lowest combined CPU & RAM utilization | Dynamic multi-user loads |
| `gpu_aware` | GPU Aware | Filters CUDA nodes; ranks by VRAM availability & thermal health | PyTorch / LLM workloads |
| `network_aware` | Network Aware | Prioritizes workers with highest throughput & lowest latency | Large dataset transfers |
| `priority_based` | Priority Based | Multiplies capacity score by user role & job priority class | Institutional SLA guarantees |
| `fair_share` | Fair Share | Distributes cluster nodes proportionally across active jobs | Multi-tenant environments |
| `ai_predictive` | AI Predictive | Random Forest Regressor predicting execution runtime from node metrics | Historical workloads |

---

## 📦 Distributed Task SDK & 11 Standard Tasks

Every distributed task implements the complete 7-method lifecycle in `shared/sdk/task_definition.py`:
1. `resource_requirements(self) -> dict`
2. `validate_input(self, input_data: dict) -> (bool, str)`
3. `partition(self, input_data: dict, chunks: int) -> list[dict]`
4. `execute(self, payload: dict) -> dict`
5. `validate_partial(self, chunk_result: dict) -> (bool, str)`
6. `aggregate(self, results: list[dict]) -> dict`
7. `validate_final(self, final_result: dict, input_data: Optional[dict]) -> (bool, str)`

### 11 Standard Built-in Tasks:
- 📶 **Distributed Merge Sort (`sorting`)**: K-way merge using `heapq` with global sorted array verification.
- 🧮 **Matrix Multiplication (`matrix_multiply`)**: Row-decomposed parallel matrix product $C = A \times B$.
- 📊 **Statistical Analysis (`statistics`)**: Parallel computation of mean, median, standard deviation, variance, min, and max.
- 🔍 **Distributed Search (`search`)**: Parallel value/pattern search with global offset index tracking.
- 📝 **MapReduce Word Count (`word_count`)**: MapReduce token frequency aggregation.
- 🖼️ **Image Filter Processing (`image_processing`)**: Distributed tile-based image filters (grayscale, invert, edge detection).
- 🔢 **Prime Number Generation (`prime_generation`)**: Parallel numeric range sieve.
- 🔐 **Substitution Cipher (`cipher`)**: Distributed Caesar / substitution encryption and decryption.
- 🤖 **Distributed Deep Learning Training (`ml_training`)**: Data-parallel PyTorch training with loss/accuracy curves and step checkpointing.
- ⚡ **Distributed Batch Inference (`distributed_inference`)**: GPU-accelerated batch vision/transformer inference with ordered confidence aggregation.
- 🧠 **Distributed LLM Fine-Tuning (`llm_finetune`)**: GPU-aware data-sharded LLM fine-tuning with step checkpoint persistence.

---

## 🏆 Real-Cluster Benchmarking Suite

The benchmarking runner in `master/app/engine/benchmarks.py` **executes strictly against connected physical cluster workers** (never uses simulated/mocked pools):

- **Scalability Benchmark**: Measures wall-clock execution time for $N \in \{1, 5, 10, 25, 50, 100\}$.
- **Real Metrics**: Computes Speedup $S = T_1 / T_N$ and Parallel Efficiency $E = S / N$.
- **Explicit Notice**: Skips data points if fewer than $N$ real workers are connected, displaying an explicit notice in the dashboard.
- **Scheduler Comparison**: Evaluates decision latency (ms) and node allocation scores across all 7 strategies in real-time.

---

## 👥 Multi-User Institutional Quotas & Projects

Supports 4 institutional user tiers with strict quota enforcement:

| Role | Concurrent Jobs | Max Workers / Job | GPU Access | Daily CPU Hours | Priority Class |
|---|---|---|---|---|---|
| **Student** | 2 | 5 | None | 20.0 hrs | NORMAL |
| **Researcher** | 5 | 20 | 4 GPUs (32 GB) | 100.0 hrs | HIGH |
| **Faculty** | 10 | 50 | 8 GPUs (64 GB) | 250.0 hrs | HIGH |
| **Administrator** | 50 | 100 | 16 GPUs (128 GB) | 1000.0 hrs | CRITICAL |

---

## 🖥 Worker Agent & PySide6 GUI

The worker agent runs either as a background headless daemon or with a rich PySide6 desktop GUI:

```bash
# Launch with PySide6 Native GUI
python -m worker.app.main --gui

# Launch in Headless Mode
python -m worker.app.main
```

### PySide6 GUI Highlights:
- **Task History Drill-Down Dialog**: Double-click any execution history row to inspect Chunk ID, status, start/end timestamps, duration (s), and detailed output/error payloads.
- **Live Telemetry Gauges**: Real-time CPU, RAM, and GPU/VRAM progress bars.
- **Auto-Discovery**: Automatically discovers the Master node on UDP port 9999 and authenticates via HMAC token.

---

## 🌐 React Control Center Dashboard

Built with React 19, Vite, and Tailwind CSS:
- **Overview Tab**: Real-time cluster health, active core pools, RAM capacity, and live area charts.
- **Jobs & Queue Tab**: Live ledger of active and completed distributed jobs with progress bars.
- **Submit Job Modal**: Instant presets for all 11 task types, scheduler strategy picker, and priority selectors.
- **Job Results Modal**: Multi-format downloads (`.json`, `.csv`, `.txt`, `.zip` artifact bundles), timeline milestones, and chunk provenance trees.
- **Benchmarks Tab**: Real cluster scalability curves and scheduling strategy performance comparison.
- **Projects & Quota Tab**: Multi-user project containerization and quota overview.
- **Nodes Tab**: Hardware breakdown (CPU model, GPU model, VRAM, reliability score).

---

## 🚀 Quick Start Guide

### Option 1: Docker Compose (Full Stack)

```bash
# Start Master, Redis, PostgreSQL, MinIO, Dashboard, and Workers
docker-compose up --build

# Scale to 5 worker nodes
docker-compose up --build --scale worker=5
```

- **Dashboard**: `http://localhost:3000`
- **Master API**: `http://localhost:8000`
- **API Swagger Docs**: `http://localhost:8000/docs`
- **MinIO Console**: `http://localhost:9001`

### Option 2: Local Development Setup

1. **Start Master Node**:
```bash
cd master
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. **Start Worker Node(s)**:
```bash
cd worker
pip install -r requirements.txt
python -m app.main --gui
```

3. **Start Dashboard**:
```bash
cd dashboard
npm install
npm run dev
```

---

## 🧪 Testing & Verification

CoCompute includes a comprehensive automated test suite testing all 7 gaps, task lifecycle execution, schedulers, and analytics:

```bash
pytest
```

```text
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-8.4.2
collected 59 items

tests/test_aggregator.py ..........                                      [ 16%]
tests/test_analytics.py .........                                        [ 32%]
tests/test_gaps_and_features.py ...............                          [ 57%]
tests/test_jobs.py ........                                              [ 71%]
tests/test_scheduler.py .......                                          [ 83%]
tests/test_sdk.py ......                                                 [ 93%]
tests/test_storage_and_metrics.py ..                                     [ 96%]
tests/test_worker_metrics.py ..                                          [100%]

======================= 59 passed, 24 warnings in 6.09s =======================
```

---

## 📄 License
MIT License. Developed for Enterprise Collaborative Distributed Computing.
