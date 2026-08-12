# CoCompute — Intelligent Distributed Computing Platform
## Complete Project Documentation & Deployment Guide

---

## 1. Executive Summary & Architecture Overview

**CoCompute** is a full-stack, intelligent, collaborative distributed computing platform. It aggregates idle computing resources from multiple heterogeneous worker nodes (laptops, desktops, servers across Windows/Linux/macOS) into a unified compute cluster for parallel execution of compute-heavy tasks.

### Core Architecture Components

```
                      ┌─────────────────────────────────┐
                      │    User / Administrator UI      │
                      │    Master Dashboard (React/Vite)│
                      └────────────────┬────────────────┘
                                       │ HTTP / WebSocket (Live Push)
                                       ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                            MASTER SERVER                            │
    │  ┌───────────────────────────────────────────────────────────────┐  │
    │  │             CoCompute Intelligence Engine (CIE)               │  │
    │  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌────────────┐  │  │
    │  │  │ UDP       │  │ Worker    │  │ Resource  │  │ Capacity   │  │  │
    │  │  │ Discovery │─►│ Register  │─►│ Monitor   │─►│ Score      │  │  │
    │  │  └───────────┘  └───────────┘  └───────────┘  └─────┬──────┘  │  │
    │  │                                                     │         │  │
    │  │  ┌───────────┐  ┌───────────┐  ┌───────────┐        ▼         │  │
    │  │  │ Result    │◄─│ Task      │◄─│ Scheduler │◄─────────────────┤  │
    │  │  │Aggregator │  │ Dispatcher│  │ (3 Algos) │  (Load Guard)    │  │
    │  │  └───────────┘  └───────────┘  └───────────┘                  │  │
    │  └───────────────────────────────────────────────────────────────┘  │
    └──────────────┬───────────────────┬───────────────────┬──────────────┘
                   │                   │                   │
  WebSocket / UDP  │                   │                   │
                   ▼                   ▼                   ▼
            ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
            │  Worker 1   │     │  Worker 2   │     │  Worker N   │
            │ ┌─────────┐ │     │ ┌─────────┐ │     │ ┌─────────┐ │
            │ │ Agent   │ │     │ │ Agent   │ │     │ │ Agent   │ │
            │ ├─────────┤ │     │ ├─────────┤ │     │ ├─────────┤ │
            │ │ Docker/ │ │     │ │ Docker/ │ │     │ │ Docker/ │ │
            │ │Subproc  │ │     │ │Subproc  │ │     │ │Subproc  │ │
            │ └─────────┘ │     │ └─────────┘ │     │ └─────────┘ │
            └─────────────┘     └─────────────┘     └─────────────┘
```

The system comprises three primary tiers:
1. **Master Node (FastAPI)**: Central coordinator running the Intelligence Engine, API server, UDP discovery service, scheduler algorithms, fault-tolerance monitor, and Redis metrics cache.
2. **Worker Cluster (Python/PySide6)**: Distributed agent nodes that automatically discover the master, report hardware metrics, receive task chunks via WebSockets, and execute them safely inside isolated Docker containers or sandboxed subprocesses.
3. **Master Dashboard (React + Vite + TailwindCSS)**: Web application providing real-time monitoring of cluster resources, live worker cards, task management, performance analytics (speedup/efficiency), system logs, active alerts, and downloadable results (JSON/CSV).

---

## 2. Technology Stack & Component Requirements

### Backend & Core Services (Master)
- **Python 3.10+**: Core programming language.
- **FastAPI (v0.115.0)**: High-performance async web framework for REST API endpoints and WebSocket channels.
- **Uvicorn (v0.30.0)**: Asynchronous Server Gateway Interface (ASGI) web server.
- **SQLAlchemy (v2.0.35)**: Object-Relational Mapping (ORM) database layer.
- **PostgreSQL 15**: Primary relational database storing users, workers, jobs, tasks, results, metrics, logs, and audit trails.
- **Redis 7 (redis-py v5.0.0)**: In-memory cache for sub-millisecond real-time cluster snapshots and time-series metric tracking.
- **scikit-learn (v1.5.1) & pandas (v2.2.2) & numpy (v1.26.4)**: Powers the AI Predictive Scheduler (`RandomForestRegressor`) for forecasting worker task execution duration.
- **PyJWT (v2.9.0) & Passlib/Bcrypt**: Authentication, user password hashing, and security token management.

### Worker Node Software
- **Python 3.10+**: Execution runtime.
- **psutil (v6.0.0)**: Cross-platform hardware metric collection (CPU, RAM, Disk, Network IO, Temperature, Frequency).
- **Websockets (v13.0) & HTTPX (v0.27.0)**: Asynchronous persistent communication channel and HTTP client.
- **PySide6 (v6.9.2)**: Qt GUI desktop interface for worker operator interaction.
- **Docker Engine (CLI)**: Preferred execution environment (`--network=none`, `--memory=512m`, `--cpus=1.0`). Falls back to sandboxed subprocess if Docker is unavailable.
- **SQLite3**: Local task execution history persistence independent of master.

### Frontend Dashboard
- **React 19 & Vite 8**: Modern frontend framework and build engine.
- **TailwindCSS v4**: Dark glassmorphism design system.
- **Recharts (v3.9.2)**: Responsive live resource area charts, speedup bar charts, and task distribution pie charts.
- **Lucide React (v1.25.0)**: UI Icon set.
- **Nginx (Alpine)**: Reverse proxy for production dashboard serving, routing `/api/` REST requests and `/ws/` WebSocket connections.

---

## 3. Directory Structure & Key Files Map

```
CoCompute/
├── CoCompute_Master_Blueprint.md   # Architectural requirement specification
├── CoCompute_Project_Documentation.md # Complete project documentation & deployment manual
├── README.md                       # High-level overview
├── docker-compose.yml              # Multi-container orchestration specification
├── docker-compose.ssl.yml          # TLS/SSL Docker compose override
├── .env.example                    # Environment variable specification template
│
├── master/                         # MASTER SERVER CODEBASE
│   ├── Dockerfile                  # Master container build recipe
│   ├── requirements.txt            # Python dependencies for Master
│   └── app/
│       ├── main.py                 # FastAPI app entry point, WebSocket handlers & loops
│       ├── api/                    # REST API ROUTERS
│       │   ├── auth.py             # User register/login endpoints
│       │   ├── workers.py          # Worker registration & metrics history
│       │   ├── jobs.py             # Job submission & progress tracking
│       │   ├── metrics.py          # Cluster overview & Redis timeseries
│       │   ├── analytics.py        # Speedup, throughput, efficiency & rankings
│       │   ├── alerts.py           # Active cluster alerts (FR-15)
│       │   ├── logs.py             # Centralized log viewer API
│       │   └── files.py            # Result file download (JSON/CSV)
│       ├── core/
│       │   └── security.py         # JWT tokens & worker key validation
│       ├── db/
│       │   ├── database.py         # SQLAlchemy engine connection
│       │   └── models.py           # Database tables definition (9 models)
│       ├── engine/                 # COCOMPUTE INTELLIGENCE ENGINE (CIE)
│       │   ├── scheduler.py        # Unified Scheduler with strategy pattern & FR-14 load guard
│       │   ├── round_robin.py      # Baseline Round-Robin algorithm
│       │   ├── ai_scheduler.py     # Random Forest predictive ML scheduler
│       │   ├── jobs.py             # Task chunk generator for 7 job types
│       │   ├── aggregator.py       # Result merger per job type & auto file exporter
│       │   ├── analytics.py        # Speedup, efficiency & SLA breach calculator
│       │   └── metrics_engine.py   # Redis real-time snapshot & time-series cache
│       ├── network/
│       │   ├── discovery.py        # UDP Discovery server (Port 9999)
│       │   └── ws_manager.py       # WebSocket connection manager
│       ├── storage/
│       │   └── file_store.py       # Filesystem storage manager for JSON/CSV results
│       └── schemas/                # Pydantic schemas for request/response validation
│
├── worker/                         # WORKER AGENT CODEBASE
│   ├── Dockerfile                  # Worker container build recipe
│   ├── requirements.txt            # Python dependencies for Worker
│   └── app/
│       ├── main.py                 # Worker agent entry point (CLI/GUI launcher)
│       ├── execution/
│       │   └── docker_engine.py    # Docker container & subprocess execution engine
│       ├── history/
│       │   └── task_history.py     # Local SQLite task history manager
│       ├── monitor/
│       │   └── metrics.py          # psutil hardware metrics collector
│       ├── network/
│       │   └── discovery.py        # UDP broadcast client finder
│       └── ui/
│           └── gui.py              # PySide6 Desktop GUI dashboard
│
├── dashboard/                      # REACT MASTER DASHBOARD
│   ├── Dockerfile                  # Nginx + Node build recipe
│   ├── nginx.conf                  # Reverse proxy configuration
│   ├── package.json                # Frontend package dependencies
│   └── src/
│       ├── App.jsx                 # Complete single-page dashboard application
│       ├── main.jsx                # React app mounting script
│       └── index.css               # Design system, glassmorphism tokens & animations
│
├── shared/                         # SHARED MODULES
│   └── config.py                   # Centralized configuration loader
├── scripts/
│   └── simulate_nodes.py           # Multi-worker cluster simulation script for load testing
├── ssl/                            # SSL/TLS CERTIFICATE GENERATION UTILITIES
└── tests/                          # AUTOMATED TEST SUITE (38 tests)
```

---

## 4. System Prerequisites

Ensure the following tools are installed on your host system:

- **Git**
- **Python 3.10+** (with `pip` and `venv`)
- **Node.js 18+ & npm** (for dashboard development if running locally outside Docker)
- **Docker Desktop & Docker Compose** (for containerized deployment)

---

## 5. Deployment Options & Execution Commands

You can run CoCompute in two ways:
- **Option A (Recommended for Quick Evaluation)**: Docker Compose (Runs Master, PostgreSQL, Redis, and Dashboard together).
- **Option B (Distributed Execution)**: Run Master Server on Node A and Worker Agents on separate machines (Nodes B, C, D...).

---

### Method A: Full-Stack Deployment via Docker Compose

Run the complete platform (PostgreSQL, Redis, Master Server, Web Dashboard) with a single command:

#### Step 1: Clone Repository & Configure Environment
```bash
git clone <repository_url>
cd CoCompute
cp .env.example .env
```

#### Step 2: Build & Start All Services
```bash
docker-compose up --build -d
```

#### Step 3: Check Container Status
```bash
docker-compose ps
```

The services will be available at:
- **Web Dashboard**: `http://localhost:3000`
- **Master REST API Docs**: `http://localhost:8000/docs`
- **UDP Discovery Port**: `9999/udp`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

#### Step 4: Stop Services
```bash
docker-compose down
```

---

### Method B: Manual Master Node Setup (Local / Standalone Server)

If running the Master Node directly on a host machine without Docker Compose:

#### Step 1: Prerequisites Setup
Ensure a PostgreSQL database and Redis server are running.
```bash
# Example using Docker for databases only
docker run -d --name cocompute-db -p 5432:5432 -e POSTGRES_DB=cocompute -e POSTGRES_USER=cocompute -e POSTGRES_PASSWORD=cocompute postgres:15-alpine
docker run -d --name cocompute-redis -p 6379:6379 redis:7-alpine
```

#### Step 2: Set Environment Variables
```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://cocompute:cocompute@localhost:5432/cocompute"
$env:REDIS_URL="redis://localhost:6379/0"
$env:JWT_SECRET_KEY="cocompute-production-secret-change-me"
$env:WORKER_API_KEY="cocompute-worker-key"
$env:SCHEDULER_ALGORITHM="resource_aware"

# Linux / macOS
export DATABASE_URL="postgresql://cocompute:cocompute@localhost:5432/cocompute"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="cocompute-production-secret-change-me"
export WORKER_API_KEY="cocompute-worker-key"
export SCHEDULER_ALGORITHM="resource_aware"
```

#### Step 3: Install Dependencies & Run Master
```bash
cd CoCompute/master
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
python -m app.main
```

The Master Node will start listening on `http://0.0.0.0:8000` and UDP port `9999`.

---

## 6. Worker Node Execution Guide

Worker agents can run on any physical or virtual machine connected to the same LAN (or reachable over IP). They will automatically discover the Master via UDP broadcast.

### Option 1: Worker with Desktop GUI (PySide6 Interface)

Runs the worker with an interactive Qt graphical dashboard showing real-time CPU/RAM meters, connection status, and task logs.

```bash
cd CoCompute/worker

# Create and activate virtual environment
python -m venv venv
# Windows: .\venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

pip install -r requirements.txt

# Run with GUI interface
python -m app.main
```

*Note: If `MASTER_IP` is not set in environment variables, the worker automatically broadcasts on UDP port 9999 to locate the Master node.*

---

### Option 2: Headless CLI Worker (Background / Server Mode)

Runs without a graphical interface (ideal for headless servers, Docker containers, or terminal sessions):

```bash
cd CoCompute/worker

# Install requirements
pip install -r requirements.txt

# Run in headless CLI mode
python -m app.main --headless
```

#### Explicit Master IP Configuration (If UDP Broadcast is Blocked across Subnets)
```bash
# Windows PowerShell
$env:MASTER_IP="192.168.1.100"
$env:MASTER_PORT="8000"
$env:WORKER_API_KEY="cocompute-worker-key"
python -m app.main --headless

# Linux / macOS
export MASTER_IP="192.168.1.100"
export MASTER_PORT="8000"
export WORKER_API_KEY="cocompute-worker-key"
python -m app.main --headless
```

---

### Option 3: Simulating Multiple Worker Nodes for Load Testing

To test how the Master Server handles a multi-node cluster on a single machine, use the included node simulation utility:

```bash
cd CoCompute
python scripts/simulate_nodes.py --count 5 --master http://localhost:8000
```
This spawns 5 simulated worker agents that register, send live heartbeats, and report metrics to the Master Node.

---

## 7. Master Dashboard Usage Guide

1. Open `http://localhost:3000` in your web browser.
2. **Account Registration**: Click "Register", enter a username, email, and password. The first registered user is automatically granted `admin` privileges.
3. **Cluster Overview Tab**: View total nodes, online/offline counts, active CPU cores, aggregate RAM pool, live cluster efficiency %, real-time resource utilization chart, and task distribution pie chart.
4. **Submit a Distributed Job**:
   - Click the **"Submit Job"** button in the top navigation bar.
   - Choose from pre-built presets or select **🐍 Custom User Task**:
     - 🔢 **Prime Generation**: Parallel sieve search across numeric ranges.
     - 🧮 **Matrix Multiplication**: Row-split parallel matrix computation.
     - 📝 **Word Count**: MapReduce text frequency calculation.
     - 📶 **Sorting**: Parallel list merge-sort.
     - 🖼️ **Image Filter**: Distributed image pixel transformation.
     - 🗜️ **Compression**: Parallel zlib text compression.
     - 🐍 **Custom User Task**: Custom user-defined Python script executed across arbitrary parallel data chunks.
   - **Full Parameter Customization**: Edit the JSON parameters directly in the modal (e.g. custom Python script code, custom input data chunks, custom matrix dimensions, numeric ranges, or word lists).
   - Click **Submit Task**.
5. **View Results & Download**:
   - Navigate to the **Tasks** tab or click on a job row.
   - Once completed, click **⬇ Download JSON** or **📄 Export CSV** to download the aggregated output saved by the File Storage Service.
6. **Dynamic Scheduler Configuration**:
   - Click the scheduler selector in the header bar (e.g. `Resource Aware`).
   - Switch between **Round Robin**, **Resource Aware**, or **AI Predictive** algorithms in real-time.

---

## 8. Verification & Test Suite

CoCompute includes a comprehensive automated test suite covering all engines, APIs, schedulers, aggregators, file storage, and metric handlers.

To run tests:
```bash
cd CoCompute
pytest -v
```

Expected output:
```
======================= 38 passed in 1.98s =======================
```

---

## 9. Summary Table of Requirements & Operations

| Task / Operational Step | Command / File Reference | Target Machine |
|---|---|---|
| Full Stack Start | `docker-compose up --build -d` | Master Host |
| Standalone Master Start | `python -m app.main` in `master/` | Master Host |
| Run GUI Worker Node | `python -m app.main` in `worker/` | Worker Machine(s) |
| Run Headless Worker Node | `python -m app.main --headless` in `worker/` | Worker Machine(s) |
| Simulate 5 Cluster Workers | `python scripts/simulate_nodes.py --count 5` | Any Host |
| Execute Unit Tests | `pytest -v` | Master Host |
| Access Web Dashboard | `http://localhost:3000` | Any Browser |
