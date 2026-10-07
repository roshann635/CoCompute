# CoCompute Worker Deployment Guide
**Zero-Friction, Portable Compute Agent Deployment**

## 1. Overview & Core Philosophy

CoCompute's deployment architecture has evolved from a developer-dependent setup into a zero-friction, portable compute-plane agent:

```
[ Traditional Setup (Legacy) ]
Clone Git Repo -> Install Python -> Install Visual C++ -> pip install -r requirements.txt -> Manual IP config

[ CoCompute Zero-Friction Architecture ]
Download Standalone Worker -> Run Executable -> Auto-Discovery -> Authenticate -> Register -> READY
```

The Worker Agent is completely decoupled from development tooling:
- **No Python or Pip required** on the client PC for standalone binaries.
- **No Git repository cloning**.
- **No manual configuration** when connected to the local subnet.
- **Automatic capability reporting** (CPU, RAM, GPU, CUDA, Docker).

---

## 2. Deployment Architecture

```
                  +-----------------------------------+
                  |          CoCompute Master         |
                  |  Control Plane & Scheduler Core   |
                  +-----------------+-----------------+
                                    |
           UDP Discovery (9999)     |    HTTP/WebSocket (8000)
         +--------------------------+-------------------------+
         |                                                    |
         v                                                    v
+-----------------+                                  +-----------------+
|  PC 01 (Win11)  |                                  |  PC 02 (Linux)  |
| CoComputeWorker |                                  | cocompute-worker|
| [PHYSICAL]      |                                  | [PHYSICAL]      |
+-----------------+                                  +-----------------+
```

---

## 3. Workload Tiers & Compatibility

Every Worker advertises its detected capabilities to the Master upon connection. The Master scheduler matches tasks to suitable tiers:

| Tier | Workload Types | Requirements | Worker Support |
|---|---|---|---|
| **Tier 1: Portable CPU** | Distributed Sorting, Prime Search, Matrix Multiplication, Data Cleaning | 1+ CPU Core, 1+ GB RAM | Supported on **all** Workers |
| **Tier 2: GPU Compute** | Accelerated Math, Compression, Vector Operations | NVIDIA GPU with CUDA capability | GPU-capable Workers only |
| **Tier 3: ML / LLM** | Deep Learning Chunks, Model Sharding | Dedicated VRAM, PyTorch/CUDA runtime | High-VRAM GPU Workers |

Workers lacking GPU or Docker are categorized as `READY` (or `DEGRADED` for advanced tasks) and continue serving Tier 1 CPU tasks without disrupting the cluster.

---

## 4. Connection Flow

1. **Auto-Discovery**: Worker broadcasts UDP packets on port `9999`. The Master replies with its LAN endpoint and Master Connect Code.
2. **Fallback Connection**: If UDP is blocked by institutional network switches, operators can supply:
   - The human-friendly **Master Connect Code** (e.g. `CC-4827` displayed on Master dashboard).
   - Or directly specify `--master-ip <IP> --master-port 8000`.
3. **HMAC Authentication**: Worker generates an HMAC-SHA256 signature using the cluster shared secret.
4. **Registration**: Hardware specs, OS, architecture, and supported task types are posted to `/api/v1/workers/register`.
5. **WebSocket Session**: An ephemeral session ID is established for heartbeat telemetry and task distribution.

---

## 5. Quick Start Cheatsheet

| Target | Command |
|---|---|
| **Standalone Windows** | `CoComputeWorker.exe` |
| **With Fallback Code** | `CoComputeWorker.exe --code CC-4827` |
| **Headless Source Run** | `python worker/start_worker.py --cli` |
| **Pre-Flight Diagnostics** | `python worker/start_worker.py --doctor` |
| **Local Demo Cluster** | `python worker/demo_cluster.py --count 3` |
