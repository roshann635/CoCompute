# CoCompute 3.0 ⚡️
**Adaptive, Predictive, and Self-Healing Distributed Computing Platform**

[![Tests](https://img.shields.io/badge/tests-67%20passed%20(100%25)-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)]()
[![PySide6](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt-41cd52.svg)]()
[![React](https://img.shields.io/badge/dashboard-React%2019%20%2B%20TailwindCSS-61dafb.svg)]()
[![License](https://img.shields.io/badge/license-MIT-purple.svg)]()

CoCompute 3.0 transforms ordinary local area networks (LANs) and heterogeneous hardware into a self-organizing, fault-tolerant, green-aware, predictive supercomputing cluster.

---

## 🌟 The 12 Intelligence Pillars of CoCompute 3.0

1. **Adaptive Hybrid Scheduler (AHS)**: Replaces static manual selection with an automated Workload Profiler that classifies compute intensities ($\text{CPU}, \text{GPU}, \text{Memory}, \text{Network} \in [0, 1]$) and automatically executes the optimal scheduling strategy.
2. **5-Factor Composite Worker Reliability Intelligence**:
   $$\text{Score} = 0.30 \cdot \text{Success} + 0.20 \cdot \text{Consistency} + 0.20 \cdot \text{Uptime} + 0.15 \cdot \text{Network Stability} + 0.15 \cdot \text{Thermal Health}$$
3. **Multi-Target AI Runtime & Resource Predictor**: Random Forest ML model trained on real execution history predicting chunk runtime, resource deltas, and candidate failure probability.
4. **Closed-Loop Feedback Learning**: Evaluates $|\text{Actual Duration} - \text{Predicted Duration}|$, automatically recalibrating worker performance coefficients after every job.
5. **Speculative Execution & Straggler Mitigation**: Background watchdog detects straggling chunks ($> 2.0\times$ median chunk time) and spawns speculative replica copies. Provenance protection guarantees only the first verified attempt wins.
6. **Dynamic Chunk Sizing & Work Stealing**: Partitions workloads into elastic chunk pools ($K > N$) with proactive WebSocket chunk pulling (`PULL_CHUNK`) ensuring fast workers never sit idle.
7. **Carbon- & Energy-Aware Green Scheduling**: `FAST`, `ECO`, and `BALANCED` modes with power modeling:
   $$P = P_{\text{idle}} + P_{\text{cpu}} \cdot U_{\text{cpu}} + P_{\text{gpu}} \cdot U_{\text{gpu}}$$
   Estimates total job energy consumption in $\text{kWh}$ and carbon footprint in $\text{gCO}_2\text{eq}$.
8. **Cluster Digital Twin & Simulation Mode**: Configurable virtual cluster simulator (10 to 100 virtual nodes) with strict `is_simulated = True` isolation to evaluate large-scale algorithmic behavior without polluting physical benchmarks.
9. **LAN Resource Marketplace**: Aggregate compute pool metrics (Total Cores, RAM, GPUs, VRAM, and Cluster Utilization %).
10. **Institutional Compute Credit System**: Tiered daily quotas (Student: 100, Researcher: 500, Faculty: 1000, Admin: Unlimited) with dynamic job costing ($C = 2 \cdot \text{CPU\_hrs} + 10 \cdot \text{GPU\_hrs}$) and an immutable ledger.
11. **Worker Trust Enrollment Gate**: Two-stage security handshake (`pending` $\rightarrow$ `trusted` / `rejected`) preventing unauthorized nodes from receiving payloads.
12. **7-State Self-Healing Cluster Lifecycle**: Dynamic state machine transitions (`HEALTHY` $\rightarrow$ `DEGRADED` $\rightarrow$ `DRAINING` $\rightarrow$ `FAILED` $\rightarrow$ `RECOVERING` $\rightarrow$ `BENCHMARKING` $\rightarrow$ `HEALTHY`).

---

## 🏛 Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                   React Dashboard (Vite + TailwindCSS)                 │
│    Marketplace • Digital Twin • Live Provenance • Carbon Tracking      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST / WebSocket Push
┌───────────────────────────────────▼────────────────────────────────────┐
│                       Master Node (FastAPI Core)                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Adaptive Hybrid Scheduler (AHS) + 8 Pluggable Strategies         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────┐ ┌──────────────────────┐ ┌─────────────┐  │
│  │ Straggler Watchdog &    │ │ 5-Factor Reliability │ │ Closed-Loop │  │
│  │ Speculative Execution   │ │ Intelligence Engine  │ │ Feedback ML │  │
│  └─────────────────────────┘ └──────────────────────┘ └─────────────┘  │
│  ┌─────────────────────────┐ ┌──────────────────────┐ ┌─────────────┐  │
│  │ Energy & Carbon Engine  │ │ Cluster Digital Twin │ │ Compute Pool│  │
│  │ (kWh & gCO2e Estimator) │ │ Simulation Manager   │ │ & Credits   │  │
│  └─────────────────────────┘ └──────────────────────┘ └─────────────┘  │
│  ┌─────────────────────────┐ ┌──────────────────────┐ ┌─────────────┐  │
│  │ MinIO S3 Object Storage │ │ Redis Priority Queue │ │ Worker Trust│  │
│  │ Artifact Bundler (.zip) │ │ & Pub/Sub Reschedule │ │ Gatekeeper  │  │
│  └─────────────────────────┘ └──────────────────────┘ └─────────────┘  │
│                   PostgreSQL / SQLite Database Layer                   │
└───────────────────────────────────┬────────────────────────────────────┘
         ▲                          │ WebSocket + HMAC Token
         │ UDP Broadcast (8000)     │ Dispatched MinIO References
         │                          ▼
┌────────┴───────────────────────────────────────────────────────────────┐
│               Worker Agents (PySide6 GUI / CLI Daemon)                 │
│  ┌────────────────────────┐ ┌───────────────────┐ ┌─────────────────┐  │
│  │ Docker Sandbox Engine  │ │ Dynamic Work      │ │ 5-Factor Score  │  │
│  │ --network=none limits  │ │ Stealing Puller   │ │ & Trust Badge   │  │
│  └────────────────────────┘ └───────────────────┘ └─────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ (for Dashboard)
- Docker Desktop (for sandboxed containerized worker task execution)

### 1. Launch Master Node
```bash
cd d:/CoCompute
uvicorn master.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Launch Worker Agent (GUI or Headless)
```bash
# PySide6 GUI with Trust Badge & 5-Factor Breakdown
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
Open `http://localhost:5173` to access the CoCompute 3.0 control center.

---

## 🧪 Testing & Verification

Run the full 67-test automated verification suite:

```bash
pytest tests/ -v
```

All 67 tests covering CoCompute 1.0, 2.0, and 3.0 intelligence pillars pass with 100% precision:
- `tests/test_cocompute_3_intelligence.py` (Workload Profiler, 5-Factor Reliability, Energy Modeling, Digital Twin, Predictive Scoring, AHS, Trust Gate, Straggler Speculation)
- `tests/test_gaps_and_features.py` (Docker Sandboxing, MinIO, Redis, Instant Suspected, Checksums, HMAC Auth, Quotas)
- `tests/test_scheduler.py` (CIE Schedulers, AI Training, Fallback)
- `tests/test_jobs.py` (Job Partitioning & Chunk Generators)
- `tests/test_aggregator.py` (K-way Merge Aggregation & Bundling)
- `tests/test_analytics.py` (Rankings, Speedup, Efficiency)
- `tests/test_sdk.py` (Task Registry & SDK Life cycles)
- `tests/test_storage_and_metrics.py` (File Store & MinIO S3)
- `tests/test_worker_metrics.py` (Telemetry Polling)

---

## 📄 License
MIT License. Developed for enterprise and academic collaborative computing environments.
