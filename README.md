# CoCompute ⚡️

**A Collaborative Distributed Computing Framework for Intelligent Resource Sharing and Parallel Task Execution**

CoCompute is a production-inspired distributed computing platform that aggregates idle computational resources from multiple heterogeneous devices and transforms them into a unified computational network. Built with a Master-Worker architecture, it features intelligent scheduling (Round Robin, Resource-Aware, AI-Predictive), fault tolerance, sandboxed execution, and a comprehensive real-time dashboard.

---

## Key Features

### Core Architecture
- **Master-Worker Pattern** — Centralized coordination with distributed execution
- **Auto-Discovery** — Workers broadcast UDP to find the Master automatically
- **WebSocket Communication** — Real-time bidirectional messaging for heartbeats, task dispatch, and results

### Scheduling Algorithms
- **Round Robin** — Baseline sequential assignment
- **Resource-Aware** — Weighted scoring: `(CPU*10 + RAM*2) * Reliability / (ActiveTasks+1) - Utilization`
- **AI-Predictive** — Random Forest Regressor trained on historical execution data to predict optimal worker

### Task Execution
- **4 Job Types** — Prime generation, matrix multiplication, MapReduce word count, generic Python
- **Docker Sandboxing** — Isolated containers with `--network=none`, memory/CPU limits
- **Subprocess Fallback** — Automatic fallback when Docker is unavailable
- **Result Aggregation** — Type-specific merge strategies (sum, reassemble, reduce)

### Fault Tolerance
- **Heartbeat Monitoring** — 5s heartbeat interval, 15s timeout detection
- **Auto-Requeue** — Orphaned tasks reassigned to live workers
- **Max Retry Limit** — 3 attempts before permanent failure
- **Worker Reliability Scoring** — Dynamic score: `completed / total`

### Security
- **JWT Authentication** — Token-based user auth with role-based access
- **Worker API Keys** — Workers authenticate during registration
- **Password Hashing** — bcrypt via passlib
- **Role-Based Access** — Admin/User roles (first user = admin)

### Analytics
- **Speedup** — `T_sequential / T_parallel` per job
- **Efficiency** — `Speedup / N_workers`
- **Throughput** — Jobs/chunks per hour
- **Worker Rankings** — Composite score from reliability, speed, completed tasks
- **Scheduler Comparison** — Side-by-side algorithm performance analysis
- **Failure Statistics** — Chunk/job failure rates, retry counts

### Dashboard
- **Auth Screen** — Login/Register with JWT
- **Cluster Overview** — Real-time nodes, cores, RAM, efficiency
- **Resource Charts** — Live CPU/RAM/Disk utilization from real metrics
- **Task Monitoring** — Job table with progress bars, status, pie chart
- **Analytics Panel** — Speedup charts, worker rankings table
- **Worker Cards** — Dynamic Online/Offline/Busy badges, utilization bars

---

## Architecture

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

---

## Database Schema

| Table | Purpose |
|---|---|
| `users` | User accounts with roles and auth |
| `workers` | Registered worker nodes with hardware specs and reliability |
| `jobs` | Submitted jobs with type, params, and aggregated results |
| `tasks` | Task containers linking jobs to chunks |
| `task_chunks` | Individual work units assigned to workers |
| `results` | Per-chunk execution results |
| `metrics` | Time-series resource utilization data |
| `logs` | System event audit log |
| `scheduler_decisions` | Scheduling decision audit trail |
| `node_health_records` | Periodic worker health snapshots |

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, AsyncIO, WebSockets |
| Networking | TCP/HTTP, UDP Broadcast, WebSocket |
| Database | PostgreSQL 15, SQLAlchemy ORM |
| Caching | Redis 7 (provisioned) |
| Auth | JWT (PyJWT), bcrypt (passlib) |
| ML | scikit-learn (Random Forest), pandas, numpy |
| Monitoring | psutil |
| Dashboard | React 19, Vite, TailwindCSS 4, Recharts, Lucide Icons |
| Containerization | Docker, Docker Compose |
| Web Server | Nginx (dashboard proxy) |

---

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
docker-compose up --build
```

- Dashboard: http://localhost:3000
- Master API: http://localhost:8000
- API Docs: http://localhost:8000/docs

Scale workers:
```bash
docker-compose up --build --scale worker=5
```

### Option 2: Manual Setup

**Prerequisites**: Python 3.10+, Node.js 18+, PostgreSQL

1. **Database**:
   ```bash
   # Create PostgreSQL database
   createdb cocompute
   ```

2. **Master**:
   ```bash
   cd master
   pip install -r requirements.txt
   export DATABASE_URL="postgresql://user:pass@localhost:5432/cocompute"
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

3. **Worker** (run on each compute node):
   ```bash
   cd worker
   pip install -r requirements.txt
   python -m app.main
   ```

4. **Dashboard**:
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/auth/me` | Current user info |

### Workers
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/workers/register` | Register worker (API key) |
| GET | `/api/v1/workers/` | List all workers |
| GET | `/api/v1/workers/{uid}` | Get worker details |
| DELETE | `/api/v1/workers/{uid}` | Deregister worker |

### Jobs
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/jobs/submit` | Submit job (JWT required) |
| GET | `/api/v1/jobs/` | List all jobs |
| GET | `/api/v1/jobs/{id}` | Job details |
| GET | `/api/v1/jobs/{id}/result` | Aggregated result |

### Metrics
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/metrics/cluster` | Real-time cluster overview |
| GET | `/api/v1/metrics/workers/{id}/history` | Worker metric history |

### Analytics
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/analytics/speedup` | Speedup per job |
| GET | `/api/v1/analytics/efficiency` | Cluster efficiency |
| GET | `/api/v1/analytics/throughput` | Throughput stats |
| GET | `/api/v1/analytics/workers/ranking` | Worker leaderboard |
| GET | `/api/v1/analytics/failures` | Failure statistics |
| GET | `/api/v1/analytics/comparison` | Scheduler comparison |

---

## Project Structure

```
CoCompute/
├── docker-compose.yml
├── README.md
├── master/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # FastAPI entry point
│       ├── api/
│       │   ├── auth.py          # Authentication endpoints
│       │   ├── workers.py       # Worker management
│       │   ├── jobs.py          # Job submission & results
│       │   ├── metrics.py       # Real-time metrics
│       │   └── analytics.py     # Performance analytics
│       ├── core/
│       │   └── security.py      # JWT, bcrypt, API keys
│       ├── db/
│       │   ├── database.py      # PostgreSQL connection
│       │   └── models.py        # 10 SQLAlchemy models
│       ├── engine/
│       │   ├── scheduler.py     # Unified scheduler (RR/RA/AI)
│       │   ├── ai_scheduler.py  # Random Forest ML model
│       │   ├── round_robin.py   # Round Robin algorithm
│       │   ├── jobs.py          # Job chunk generators
│       │   ├── aggregator.py    # Result aggregation
│       │   └── analytics.py     # Analytics computations
│       ├── network/
│       │   ├── discovery.py     # UDP discovery server
│       │   └── ws_manager.py    # WebSocket manager
│       └── schemas/
│           ├── auth.py
│           ├── worker.py
│           └── job.py
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py              # Worker entry point
│       ├── execution/
│       │   └── docker_engine.py # Docker + subprocess executor
│       ├── monitor/
│       │   └── metrics.py       # psutil + temperature + task count
│       └── network/
│           └── discovery.py     # UDP broadcast client
├── dashboard/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── src/
│       ├── App.jsx              # Full dashboard application
│       ├── index.css            # TailwindCSS theme
│       └── main.jsx
└── shared/                      # Future: shared protocols
```

---

## License

MIT
