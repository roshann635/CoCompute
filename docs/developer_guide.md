# CoCompute Developer Guide

Welcome to the CoCompute Developer Guide. This document details the platform architecture, directory layout, network protocol specifications, database design, API endpoints, setup, and validation steps.

---

## 1. Directory Structure

CoCompute follows a loose-coupled master-worker architecture.

```
CoCompute/
├── docs/                        # Project documentation (developer guide, etc.)
├── tests/                       # Unit and integration test suites
├── shared/                      # Shared protocols, config schemas, and constants
│   ├── protocol.py              # WebSocket and UDP protocol strings and constants
│   └── config.py                # Configuration loader
├── master/                      # Master Node (FastAPI application backend)
│   ├── app/
│   │   ├── main.py              # Application entry point & WebSockets
│   │   ├── api/                 # REST Routers (Auth, Jobs, Workers, etc.)
│   │   ├── db/                  # SQLAlchemy models and connection
│   │   ├── engine/              # Scheduler strategies, aggregators, analytics
│   │   └── schemas/             # Pydantic validation schemas
│   └── Dockerfile
├── worker/                      # Worker Agent (PySide6 application frontend/CLI)
│   ├── app/
│   │   ├── main.py              # Worker entry point (coordinates UI and Thread loops)
│   │   ├── execution/           # Docker sandboxing and subprocess executor
│   │   ├── history/             # SQLite local task history manager
│   │   ├── monitor/             # Hardware metrics collection (psutil)
│   │   ├── network/             # UDP auto-discovery & HTTP connection manager
│   │   └── ui/                  # PySide6 desktop dashboard frontend files
│   └── Dockerfile
└── dashboard/                   # Administrator control panel (React / Vite)
```

---

## 2. Platform Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Dashboard (React)                     │
│              Vite + TailwindCSS + Recharts                │
└────────────────────────┬─────────────────────────────────┘
                         │ REST / WebSocket
┌────────────────────────▼─────────────────────────────────┐
│                  Master Node (FastAPI)                     │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Auth API │ │ Scheduler  │ │Aggregator│ │ Analytics │  │
│  └──────────┘ │ RR/RA/AI   │ └──────────┘ └───────────┘  │
│               └────────────┘                              │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌───────────┐  │
│  │Discovery │ │ WS Manager │ │ Fault Tol│ │ Job Engine│  │
│  │ UDP 9999 │ └────────────┘ └──────────┘ └───────────┘  │
│  └──────────┘                                             │
│                    PostgreSQL + SQLAlchemy                 │
└──────────────────────────────────────────────────────────┘
         │ UDP Discovery    │ WebSocket        │ HTTP
┌────────▼────┐      ┌──────▼──────┐    ┌─────▼──────┐
│  Worker #1  │      │  Worker #2  │    │  Worker #N │
│  ┌────────┐ │      │  ┌────────┐ │    │  ┌────────┐│
│  │Executor│ │      │  │Executor│ │    │  │Executor││
│  │Docker/ │ │      │  │Docker/ │ │    │  │Docker/ ││
│  │Subproc │ │      │  │Subproc │ │    │  │Subproc ││
│  └────────┘ │      │  └────────┘ │    │  └────────┘│
│  │Metrics │ │      │  │Metrics │ │    │  │Metrics ││
│  │psutil  │ │      │  │psutil  │ │    │  │psutil  ││
│  └────────┘ │      │  └────────┘ │    │  └────────┘│
└─────────────┘      └─────────────┘    └────────────┘
```

### Master Node Services
- **FastAPI HTTP API**: Manages authentication, worker lists, job submissions, and logs.
- **UDP Discovery Server**: Listens on port `9999` and responds to worker broadcasts with Master connection metadata.
- **Scheduler Loop**: Dynamically assigns pending tasks to workers using Round Robin, Resource-Aware, or AI-Predictive algorithms.
- **Heartbeat & Fault Tolerance**: Monitors WS connections. If a worker goes offline for >15s, its current tasks are requeued (up to 3 retries).
- **Result Aggregator**: Merges chunk outputs depending on the job type (e.g. sums primes, merge-sorts sorting arrays, concatenates matrix rows).

### Worker Agent Services
- **UDP Auto-Discovery**: Broadcasts UDP search requests, parses the response, resolves master IPs, and begins registration.
- **Desktop UI**: Custom styled PySide6 dark-theme dashboard. Displays resource progress bars, connection status, current task state, local logs, and a SQLite execution table. Can be bypassed with `--headless`.
- **Sandbox Execution**: Launches scripts inside temporary Docker containers (`--network=none`, `--memory=512m`, `--cpus=1.0`). If Docker is not running, falls back to a subprocess with timeout limits.

---

## 3. Supported Job Types

CoCompute supports six default job types, each implementing split-partition and aggregation strategies:
1. **Prime Generation**: Finds prime numbers in range $A$ to $B$. Aggregator compiles list of samples and sums counts.
2. **Matrix Multiplication**: Row-based split. Workers multiply a chunk of rows by Matrix $B$. Aggregator sorts and reconstructs rows.
3. **Word Count**: MapReduce word frequency count. Aggregator reduces/sums dictionaries and returns top 50.
4. **Sorting**: Splits a list of integers. Workers sort slices. Aggregator performs a merge-sort using `heapq`.
5. **Image Processing**: Grayscale/Invert filter on pixel matrices. Aggregator merges outputs sorted by ID.
6. **Compression**: Text payload split. Workers compress chunks using `zlib`. Aggregator returns saved byte ratios.

---

## 4. Run & Test Instructions

### Setup Virtual Environment & Dependencies
```bash
# Setup python dependencies for testing/local run
pip install -r master/requirements.txt
pip install -r worker/requirements.txt
```

### Running Tests
Execute the pytest suite from the root directory:
```bash
pytest tests/ -v
```

### Starting the GUI Worker manually
To run the PySide6 worker interface from terminal:
```bash
python -m worker.app.main
```
To run the worker in headless command-line interface mode (suitable for cloud containers):
```bash
python -m worker.app.main --headless
```
