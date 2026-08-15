# CoCompute — Master Development Prompt
> **Version:** 2.0 Final  
> **Author:** Roshan | Team Lead, Group No. 7 | K.K. Wagh Institute of Engineering, Nashik  
> **Stack:** Python (FastAPI) · React (MERN) · MongoDB · PySide6 · psutil · pynvml · PyTorch Distributed · Docker · Redis · WebSocket · UDP

---

## 1. WHAT CoCompute IS

CoCompute is an **intelligent institutional distributed-computing platform** that converts heterogeneous LAN-connected machines into a single unified compute pool. It supports general parallel computation, ML training, distributed deep learning, LLM fine-tuning, and custom task execution — without requiring users to understand distributed systems.

The system must handle everything automatically:

```
DISCOVER → AUTHENTICATE → MONITOR → ANALYZE CAPACITY
→ SELECT WORKERS → PARTITION WORKLOAD → DISPATCH CHUNKS
→ EXECUTE IN PARALLEL → TRACK PROVENANCE → DETECT FAILURES
→ RESCHEDULE → AGGREGATE CORRECTLY → VALIDATE → PRODUCE RESULT
→ DISPLAY ON DASHBOARD → ALLOW DOWNLOAD → STORE ARTIFACT
```

A user interacts only with a clean dashboard. CoCompute handles all distributed complexity underneath.

---

## 2. THE SINGLE MOST IMPORTANT RULE

> **A job is NOT successful because workers reported SUCCESS.**
>
> A job is successful ONLY when the Master has received ALL required valid chunk results, correctly aggregated them using the task's specific aggregation strategy, passed final validation, and produced the actual correct answer.

This rule is non-negotiable and governs every design decision in the system.

---

## 3. TECH STACK

| Layer | Technology |
|---|---|
| Master API | Python — FastAPI |
| Worker Agent | Python + PySide6 (GUI) + psutil + pynvml |
| Frontend Dashboard | React + Tailwind CSS |
| Database | MongoDB (jobs, workers, chunks, users, quotas) |
| Real-time Control | WebSocket (heartbeat, status push, live metrics) |
| Job REST API | HTTP — FastAPI routes |
| Worker Discovery | UDP broadcast |
| Message Queue | Redis (job queue, rescheduling events) |
| GPU Monitoring | pynvml / GPUtil |
| ML Runtime | PyTorch Distributed (torch.distributed) |
| Containerization | Docker (sandboxed task execution) |
| Storage | MinIO (large datasets, model checkpoints, artifacts) |
| Benchmarking | Custom benchmark module with real measured values |

---

## 4. FULL SYSTEM ARCHITECTURE

```
                    ┌──────────────────────────────┐
                    │            USERS             │
                    │  Student / Researcher /      │
                    │  Faculty / Administrator     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       CoCompute PORTAL        │
                    │   Dashboard + Job UI (React)  │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
         ┌─────────────────────────────────────────────────┐
         │              MASTER CONTROL PLANE               │
         │                                                 │
         │  FastAPI REST API  │  WebSocket Server          │
         │  Auth & RBAC       │  Job Manager               │
         │  Redis Job Queue   │  CoCompute Intelligence    │
         │  Fault Recovery    │  Engine (CIE)              │
         │  Aggregator        │  Checkpoint Manager        │
         │  Artifact System   │  Observability Layer       │
         └──────────────────────────┬──────────────────────┘
                                    │
                          ┌─────────┴──────────┐
                          │    RESOURCE POOL    │
                          └─────────┬──────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
      ┌───────────┐           ┌───────────┐           ┌───────────┐
      │ CPU Nodes │           │ GPU Nodes │           │  Hybrid   │
      │ psutil    │           │ pynvml    │           │  Nodes    │
      └─────┬─────┘           └─────┬─────┘           └─────┬─────┘
            └───────────────────────┼───────────────────────┘
                                    ▼
                          ┌──────────────────────┐
                          │    TASK RUNTIME       │
                          │  Docker Containers    │
                          │  Parallel CPU Tasks   │
                          │  PyTorch Distributed  │
                          │  LLM Workloads        │
                          │  Custom Task SDK      │
                          └──────────┬────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │    ARTIFACT SYSTEM   │
                          │  Results / Logs      │
                          │  Model Checkpoints   │
                          │  Metrics / Configs   │
                          └──────────────────────┘
```

---

## 5. CoCompute INTELLIGENCE ENGINE (CIE)

The CIE is the core decision-making brain embedded in the Master. It is a multi-module engine that runs continuously.

### CIE Sub-Modules

| Module | Responsibility |
|---|---|
| **Resource Monitor** | Continuously collects CPU, RAM, GPU, VRAM, network stats from all workers via WebSocket |
| **Capacity Analyzer** | Scores every worker in real time based on current load and available resources |
| **Worker Selector** | Picks the optimal set of workers for a given job and task type |
| **Scheduler** | Assigns chunks to workers using the configured pluggable strategy |
| **Fault Detector** | Monitors heartbeats; detects disconnects and timeouts immediately |
| **Reschedule Engine** | Identifies orphaned chunks on failed workers; creates new attempts on healthy ones |
| **Aggregator** | Collects partial results and merges them using task-specific aggregation logic |

### Scheduling Strategies (Strategy Pattern — pluggable)

| Strategy | Logic |
|---|---|
| **Round Robin** | Distribute chunks evenly regardless of load |
| **Least Loaded** | Prefer workers with the lowest current CPU + RAM utilization |
| **Capacity Based** | Score each worker on CPU, RAM, GPU, VRAM, and reliability; assign to highest scorer |
| **GPU Aware** | Filter to GPU-capable workers first; score on VRAM availability and GPU utilization |
| **Network Aware** | Prefer workers with lowest latency to Master |
| **Priority Based** | Higher-priority users / jobs get first access to best workers |
| **Fair Share** | Distribute cluster resources proportionally across all active users |

Each strategy is a swappable module. Changing the scheduler must not require changes to any other part of the system.

### Capacity Scoring (Capacity Based example)

```
Worker 1: CPU 20%  RAM 30%  GPU 24 GB VRAM avail  → Score: 94  → SELECTED
Worker 2: CPU 80%  RAM 70%  GPU: none              → Score: 32  → REJECTED (GPU job)
Worker 3: CPU 35%  RAM 40%  GPU 16 GB VRAM avail   → Score: 78  → SELECTED
```

---

## 6. WORKER IDENTITY MODEL

Every registered worker exposes full hardware metadata. These values are reported **dynamically** and **continuously** — never static.

```json
{
  "worker_id": "WORKER-07",
  "hostname": "LAB-PC-07",
  "ip_address": "192.168.1.107",
  "os": "Windows 11",
  "cpu_model": "AMD Ryzen 7 5700U",
  "cpu_cores": 8,
  "cpu_freq_mhz": 1800,
  "cpu_utilization_pct": 42,
  "ram_total_gb": 16,
  "ram_used_gb": 4.2,
  "ram_free_gb": 11.8,
  "ram_utilization_pct": 26,
  "gpu_count": 1,
  "gpu_model": "NVIDIA RTX 3060",
  "vram_total_gb": 12,
  "vram_available_gb": 9.7,
  "gpu_utilization_pct": 8,
  "gpu_temperature_c": 42,
  "cuda_capability": "8.6",
  "network_latency_ms": 2,
  "agent_version": "2.0.0",
  "status": "IDLE"
}
```

---

## 7. WORKER STATE MACHINE

```
DISCOVERING
    ↓
REGISTERING
    ↓
ONLINE (IDLE)
    ↓
BUSY
    ↓  ← heartbeat loss OR WebSocketDisconnect
SUSPECTED
    ↓  ← timeout confirmed
FAILED   → trigger rescheduling for all incomplete chunks
    ↓
OFFLINE
    ↓  ← if worker reconnects
RECOVERING → ONLINE (IDLE)
```

**Rules:**
- Heartbeat sent every 5 seconds (configurable)
- Missing 3 consecutive heartbeats → SUSPECTED
- `WebSocketDisconnect` event → immediately SUSPECTED (do not wait for heartbeat timeout)
- SUSPECTED → FAILED after configurable timeout
- FAILED → immediately query all ASSIGNED chunks owned by this worker and reschedule them

---

## 8. WORKER AGENT — PySide6 GUI

The Worker GUI is a **read-only status monitor**. Workers report; they never control the cluster.

```
┌────────────────────────────────────┐
│         CoCompute Worker           │
├────────────────────────────────────┤
│  Worker ID:  WORKER-03             │
│  Status:     🟢 BUSY               │
│  Master:     Connected             │
├────────────────────────────────────┤
│  CPU:   42%   ████████░░░░         │
│  RAM:   51%   ██████████░░         │
│  GPU:   63%   ████████████░        │
│  VRAM:  9.7 GB available           │
│  Temp:  61°C                       │
├────────────────────────────────────┤
│  Job:         JOB-104              │
│  Chunk:       CH-018               │
│  Progress:    ████████░░ 82%       │
├────────────────────────────────────┤
│  TASK HISTORY                      │
│  JOB-101 │ CH-04 │ Sort   │ ✓     │
│  JOB-101 │ CH-05 │ Sort   │ ✓     │
│  JOB-102 │ CH-01 │ Matrix │ ✓     │
│  JOB-103 │ CH-07 │ Search │ ✗     │
└────────────────────────────────────┘
```

**Strictly read-only fields (never editable):**
Worker ID · Master IP · Assigned Job/Chunk ID · Scheduler decisions · Task assignments

**Task History drill-down (click any row):**
Job ID · Chunk ID · Operation · Input size · Start time · End time · Duration · Status · Result

---

## 9. JOB DATA MODEL

```json
{
  "job_id": "JOB-1042",
  "user_id": "USER-001",
  "project_id": "PROJECT-05",
  "job_type": "SORT",
  "input_summary": "1,000,000 integers",
  "scheduler_strategy": "CAPACITY_BASED",
  "status": "RUNNING",
  "priority": "NORMAL",
  "created_at": "2025-04-15T14:20:01Z",
  "started_at": "2025-04-15T14:20:03Z",
  "completed_at": null,
  "execution_time_sec": null,
  "worker_count": 32,
  "chunk_count": 128,
  "chunks_completed": 127,
  "chunks_failed": 3,
  "chunks_rescheduled": 3,
  "result": null,
  "result_format": "JSON_ARRAY",
  "result_location": "minio://results/JOB-1042.json",
  "checkpoint_location": null,
  "timeline": []
}
```

---

## 10. JOB STATE MACHINE

```
QUEUED
  ↓
VALIDATING
  ↓
PARTITIONING
  ↓
SCHEDULING
  ↓
DISPATCHING
  ↓
RUNNING ─────────────────────────────┐
  ↓ (all chunks done)                │
AGGREGATING          WORKER_FAILED   │
  ↓                       ↓         │
VALIDATING_RESULT    RESCHEDULING ───┘
  ↓
COMPLETED

RUNNING → TIMEOUT → RESCHEDULING → RUNNING
AGGREGATING → VALIDATION_FAILED → FAILED
VALIDATING → INPUT_INVALID → REJECTED
```

---

## 11. CHUNK PROVENANCE MODEL

Every unit of work is fully traceable. The Master knows exactly which worker executed which chunk on which attempt.

```
JOB-1001
│
├── CHUNK-001
│    └── ATTEMPT-001 → WORKER-01 → ✓ SUCCESS
│
├── CHUNK-002
│    └── ATTEMPT-001 → WORKER-02 → ✓ SUCCESS
│
├── CHUNK-003
│    ├── ATTEMPT-001 → WORKER-03 → ✗ FAILED
│    └── ATTEMPT-002 → WORKER-05 → ✓ SUCCESS  ← only this contributes
│
└── CHUNK-004
     └── ATTEMPT-001 → WORKER-04 → ✓ SUCCESS
```

### ChunkAttempt Schema

```json
{
  "attempt_id": "ATT-004",
  "chunk_id": "CH-003",
  "job_id": "JOB-1001",
  "worker_id": "WORKER-05",
  "attempt_number": 2,
  "status": "SUCCESS",
  "assigned_at": "2025-04-15T14:20:05Z",
  "started_at": "2025-04-15T14:20:05.1Z",
  "completed_at": "2025-04-15T14:20:06.4Z",
  "execution_time_sec": 1.3,
  "input_reference": "minio://chunks/JOB-1001/chunk_003.bin",
  "output_reference": "minio://results/JOB-1001/result_ch003_att004.bin",
  "checksum_sha256": "abc123def456...",
  "error": null
}
```

**Critical rule:** Only the accepted attempt contributes to aggregation. Any result arriving for a non-accepted attempt (e.g., a late result from a worker previously marked FAILED) is silently discarded.

---

## 12. TASK SDK CONTRACT

Every supported task must implement this interface. This is the contract that makes CoCompute a platform rather than a hardcoded demo.

```python
class TaskDefinition:

    def resource_requirements(self) -> ResourceSpec:
        """
        Declare minimum CPU cores, RAM GB, GPU count,
        VRAM GB, and estimated execution time.
        CIE uses this to filter and score workers.
        """

    def validate_input(self, input_data) -> ValidationResult:
        """
        Validate input before partitioning.
        Reject malformed or unsupported input immediately.
        """

    def partition(self, input_data, worker_count: int) -> list[Chunk]:
        """
        Split input into N chunks for parallel execution.
        Each chunk must be independently executable.
        """

    def execute(self, chunk: Chunk) -> PartialResult:
        """
        Execute one chunk. Runs inside Docker container on Worker Agent.
        Must be stateless and deterministic.
        """

    def validate_partial(self, partial_result: PartialResult) -> ValidationResult:
        """
        Validate a single worker's result before accepting it.
        Check type, count, checksum, and domain constraints.
        """

    def aggregate(self, partial_results: list[PartialResult]) -> FinalResult:
        """
        Merge all accepted partial results into the correct global answer.
        This is task-specific logic — never a generic concatenation.
        """

    def validate_final(self, final_result: FinalResult) -> ValidationResult:
        """
        Validate the globally aggregated result.
        Verify count, correctness, integrity, and checksums.
        """
```

---

## 13. TASK-SPECIFIC AGGREGATION (REQUIRED FOR EVERY TASK)

Naive concatenation is wrong for most tasks. Every task type must define its own correct aggregation.

| Task | Partition Strategy | Correct Aggregation |
|---|---|---|
| **Sorting** | Split into N equal ranges | K-way merge → globally sorted array |
| **Matrix Multiply** | Block decomposition | Block matrix reconstruction |
| **Sum** | N sub-arrays | Sum of partial sums |
| **Average** | N sub-arrays | (Total partial sum) / (Total element count) |
| **Max / Min** | N sub-arrays | Max or Min of partial maxima/minima |
| **Search** | N sub-ranges of array/data | Union of all match indices |
| **Word Count** | N document chunks | Merged frequency maps (key-wise addition) |
| **Image Processing** | N image tiles | Ordered tile reconstruction → full image |
| **Statistics** | N sub-arrays | Aggregated mean, std dev, median, quartiles |
| **ML Training** | N data shards | Gradient aggregation / federated model averaging |
| **Distributed Inference** | N input batches | Concatenate ordered prediction arrays |
| **LLM Fine-tuning** | N data shards | Gradient aggregation with checkpoint merge |

**Sorting — correct example:**
```
Input: 1,000,000 numbers
       ↓ partition into 4 chunks
CH1 → W1 → [locally sorted 250k]
CH2 → W2 → [locally sorted 250k]
CH3 → W3 → [locally sorted 250k]
CH4 → W4 → [locally sorted 250k]
       ↓ K-WAY MERGE on Master
Output: [globally sorted 1,000,000 numbers]   ← the actual correct answer
```

---

## 14. RESULT VALIDATION PIPELINE

```
Worker Result Received
        ↓
SHA-256 Checksum Verification
        ↓ (mismatch → reject → reschedule)
Partial Validation
  - correct type
  - expected element count
  - domain constraints (no NaN, no out-of-range)
        ↓ (fail → reject → reschedule)
Attempt Accepted → stored
        ↓ (all chunks done)
Task-Specific Aggregation
        ↓
Global Validation
  - total element count == expected
  - sort order verified (for sort tasks)
  - mathematical correctness (for sum/avg)
  - no missing chunks
  - no duplicate attempt contributions
  - final checksum computed
        ↓ (fail → FAILED with error detail)
Final Result Produced
```

---

## 15. FAULT DETECTION & RECOVERY PIPELINE

```
Worker disconnect (WebSocketDisconnect) OR 3 missed heartbeats
               ↓
      Mark worker SUSPECTED
               ↓ (timeout expires)
      Mark worker FAILED
               ↓
Query: all ASSIGNED ChunkAttempts where worker_id = WORKER-X
               ↓
For each affected chunk:
    Set current attempt status = FAILED
    Create new ChunkAttempt (attempt_number + 1)
               ↓
Re-score all remaining ONLINE workers (exclude FAILED)
               ↓
Assign new attempts to best available workers
               ↓
Dispatch new chunks
               ↓
Receive results → validate → aggregate
               ↓
Job continues to COMPLETED
```

**Duplicate protection:** Master maintains `accepted_attempt_id` per chunk. Any result arriving for a different attempt ID is silently dropped.

---

## 16. STANDARD TASK LIBRARY

All tasks must be fully implemented end-to-end (partition → execute → aggregate → validate → display result).

**Computational Tasks:**
1. Sorting — K-way merge, verified globally sorted output
2. Matrix Multiplication — block decomposition, reconstructed matrix
3. Statistics — mean, median, min, max, std dev, quartiles
4. Search — find value/pattern in large dataset, return all match indices
5. Word Count — frequency map from large document corpus
6. Image Processing — parallel tile-based filters (blur, grayscale, edge detection)
7. Prime Number Sieve — parallel range search, merged prime list
8. Caesar / Substitution Cipher — simple custom task demonstration

**ML / AI Tasks:**
9. Distributed Model Training — PyTorch Distributed, data parallelism across GPU workers
10. Distributed Inference — batch inference across GPU workers, ordered result merge
11. LLM Fine-tuning — GPU-aware, data parallel, with checkpointing every N steps

---

## 17. GPU COMPUTING

### GPU Resource Model (per worker)

```json
{
  "gpu_count": 2,
  "gpus": [
    {
      "index": 0,
      "model": "NVIDIA RTX 4090",
      "vram_total_gb": 24,
      "vram_available_gb": 19.7,
      "gpu_utilization_pct": 21,
      "temperature_c": 58,
      "cuda_capability": "8.9"
    },
    {
      "index": 1,
      "model": "NVIDIA RTX 3060",
      "vram_total_gb": 12,
      "vram_available_gb": 11.1,
      "gpu_utilization_pct": 5,
      "temperature_c": 44,
      "cuda_capability": "8.6"
    }
  ]
}
```

### GPU-Aware Scheduling Rules

- GPU-required tasks are **never** assigned to CPU-only workers
- Scheduler filters worker pool to GPU-capable nodes first
- Workers are then ranked by VRAM available, GPU utilization, and CUDA capability
- Multi-GPU nodes are preferred for large model training
- GPU temperature is monitored; workers exceeding thermal threshold are deprioritized

---

## 18. ML DISTRIBUTED RUNTIME

CoCompute orchestrates PyTorch Distributed — it does not reimplement it.

**CoCompute's role in ML jobs:**

```
Discover GPU workers
        ↓
Rank GPU workers by VRAM and capability
        ↓
Prepare training environment (Docker image per worker)
        ↓
Distribute dataset shards to selected workers (via MinIO references)
        ↓
Launch torch.distributed training runtime across selected nodes
        ↓
Monitor: epoch, loss, accuracy, gradient norms per step
        ↓
Checkpoint every N steps → store to MinIO
        ↓
Detect GPU worker failure
        ↓
Resume training from last valid checkpoint on replacement workers
        ↓
Training complete → produce model artifact
```

**ML Job Dashboard:**
```
Model:     ResNet-50 (Custom)
Task:      Distributed Training
GPU Workers: 8
Status:    🟢 RUNNING

Epoch:     12 / 50
Loss:      0.284
Accuracy:  91.3%
Step:      4,800 / 20,000

Checkpoint:  epoch_12.pt  ← saved to MinIO

[ VIEW METRICS ]  [ DOWNLOAD CHECKPOINT ]
```

---

## 19. LLM WORKLOAD SUPPORT

Users can submit LLM fine-tuning jobs by specifying:

```
Model:           custom-llm-7b (uploaded or referenced)
Dataset:         dataset.jsonl (uploaded to MinIO)
Task:            Fine-tuning
GPU requirement: >= 16 GB VRAM
Min Workers:     4
Epochs:          10
Checkpoint:      Every 500 steps
Batch Size:      8 (auto-split across GPU workers)
```

CoCompute handles:
- Worker selection (VRAM >= 16 GB, CUDA >= 8.0)
- Dataset sharding across workers
- Distributed fine-tuning runtime
- Step-level checkpoint saving
- Worker failure → resume from last checkpoint
- Final model artifact download

---

## 20. CHECKPOINT MANAGER

Long-running jobs must never restart from zero on worker failure.

```
Training / Long Job Running
        ↓
Checkpoint at interval N
    → saved to MinIO with job_id + step
        ↓
Worker failure detected
        ↓
Load last valid checkpoint from MinIO
        ↓
Resume on replacement workers from that step
```

Checkpoint metadata stored in MongoDB per job:

```json
{
  "job_id": "JOB-2001",
  "checkpoint_step": 4800,
  "checkpoint_epoch": 12,
  "checkpoint_location": "minio://checkpoints/JOB-2001/epoch_12.pt",
  "saved_at": "2025-04-15T16:45:00Z",
  "is_valid": true
}
```

---

## 21. CONTAINERIZED TASK EXECUTION

All task execution runs inside Docker containers on Worker Agents. This provides isolation, reproducibility, and security.

```
Task Submitted
      ↓
Task SDK validated
      ↓
Docker image selected (per task type)
      ↓
Container launched on Worker with:
    CPU limit
    RAM limit
    GPU passthrough (if required)
    Disk quota
    Network policy (MinIO only)
    Execution timeout
      ↓
Chunk executed inside container
      ↓
Result written to MinIO output path
      ↓
Container terminated
      ↓
Master retrieves result reference
```

No user-submitted code ever runs directly on host worker OS.

---

## 22. ARTIFACT SYSTEM

Every job produces a complete, persistent artifact bundle.

```
JOB-1042/
├── config.json          ← job parameters, strategy, worker count
├── timeline.json        ← full event timeline with timestamps
├── provenance.json      ← chunk → attempt → worker → status map
├── partial_results/     ← per-chunk validated results
│    ├── result_ch001.bin
│    ├── result_ch002.bin
│    └── ...
├── final_result.json    ← the actual answer
├── metrics.json         ← execution time, speedup, utilization
├── logs/                ← per-worker and per-chunk execution logs
│    ├── WORKER-01.log
│    └── ...
├── checkpoints/         ← for ML/LLM jobs
│    └── epoch_12.pt
└── model/               ← for ML jobs
     └── final_model.pt
```

User actions on any completed job:
- View full result
- Download any artifact
- Resume from checkpoint (ML/LLM)
- Inspect provenance table
- View job timeline

---

## 23. MULTI-USER INSTITUTIONAL PLATFORM

### User Roles

| Role | Permissions |
|---|---|
| **Student** | Submit jobs, view own projects, limited quota |
| **Researcher** | Submit jobs, larger quota, priority access to GPU nodes |
| **Faculty** | Higher quota, can manage student projects |
| **Administrator** | Full cluster control, user management, quota management, audit logs |

### Resource Quotas

```json
{
  "user_id": "USER-042",
  "role": "RESEARCHER",
  "max_concurrent_jobs": 5,
  "max_workers_per_job": 20,
  "max_gpu_count": 16,
  "max_vram_gb": 128,
  "max_cpu_hours_per_day": 200,
  "priority": "HIGH"
}
```

### Scheduler considers simultaneously:
```
Task resource requirements
+ User priority level
+ User remaining quota
+ Worker current availability
+ Worker reliability history
→ Optimal assignment
```

### Project Model
Each user organizes work into Projects. A Project contains multiple Jobs. Results and artifacts are grouped per Project.

---

## 24. OBSERVABILITY

All events are logged with structured metadata and are searchable.

**Searchable by:** `job_id` · `worker_id` · `chunk_id` · `attempt_id` · `user_id` · `timestamp range`

**Tracked metrics:**
- Worker CPU / RAM / GPU utilization (time series)
- Job progress (chunks completed vs total, per second)
- Chunk execution latency (per worker)
- Scheduling latency (time from DISPATCHING to worker RECEIVED)
- Network latency between Master and each worker
- Failure count and recovery time per worker
- Aggregation time per job
- End-to-end job time

**Admin dashboard panels:**
- Cluster health overview (all workers, statuses, utilization)
- Active jobs and queue depth
- User activity and quota consumption
- Failure rate per worker (reliability ranking)
- Throughput over time (jobs/hour, chunks/sec)
- Audit log (all job submissions, user actions, admin changes)

---

## 25. SECURITY

| Concern | Implementation |
|---|---|
| User authentication | JWT-based login |
| Worker authentication | Shared secret token per worker registration |
| Authorization | Role-based access control (RBAC) |
| Task execution | Docker containers with resource limits and network isolation |
| Input validation | Strict schema validation before any task reaches workers |
| Transport | TLS for all Master ↔ Worker and Master ↔ Frontend communication |
| Data isolation | Users cannot access other users' jobs, results, or artifacts |
| Audit logging | All job submissions, admin actions, and failures logged with user + timestamp |

---

## 26. MASTER DASHBOARD — COMPLETED JOB VIEW

```
JOB-1042
════════════════════════════════════════════════════

Task:          Sort 1,000,000 Numbers
User:          Roshan (Researcher)
Project:       Distributed Algorithms Lab
Status:        🟢 COMPLETED
Strategy:      Capacity Based
Workers Used:  32
Chunks:        128  |  Successful: 128  |  Failed: 3  |  Rescheduled: 3
Execution:     14.82 sec

════════════════════════════════════════════════════
JOB TIMELINE

14:20:01   Job submitted by Roshan
14:20:01   Input validated — 1,000,000 integers
14:20:02   128 chunks created
14:20:02   32 workers selected (Capacity Based)
14:20:03   All chunks dispatched
14:20:04   CH001 completed — WORKER-01 (1.1s)
14:20:05   WORKER-17 disconnect detected
14:20:05   CH067–CH070 marked FAILED (Attempt 1)
14:20:05   CH067–CH070 rescheduled → WORKER-42 (Attempt 2)
14:20:06   CH067–CH070 completed — WORKER-42 (1.3s)
14:20:07   All 128 chunks received
14:20:07   K-way merge aggregation started
14:20:07   Global validation: ✓ PASSED (1,000,000 / 1,000,000)
14:20:07   Result artifact saved

════════════════════════════════════════════════════
WORKER PROVENANCE

WORKER-01   CH001–CH004   Attempt 1   ✓ SUCCESS    4.4s
WORKER-02   CH005–CH008   Attempt 1   ✓ SUCCESS    4.6s
...
WORKER-17   CH067–CH070   Attempt 1   ✗ FAILED     (disconnect)
WORKER-42   CH067–CH070   Attempt 2   ✓ SUCCESS    5.2s
...

════════════════════════════════════════════════════
FINAL RESULT

1,000,000 / 1,000,000 values processed
Validation: ✓ PASSED
Integrity:  SHA-256 verified

[1, 2, 3, 4, 5, 6, 7, 8, ...]

[ VIEW FULL RESULT ]   [ DOWNLOAD JSON ]   [ DOWNLOAD CSV ]
```

---

## 27. RESULT TYPES & DOWNLOAD FORMATS

| Task | Display | Download Format |
|---|---|---|
| Sorting / Search | Paginated array viewer | `.json`, `.csv`, `.txt` |
| Matrix | Grid table renderer | `.json`, `.csv`, `.npy` |
| Statistics | Key-value summary card | `.json`, `.txt` |
| Image Processing | Image preview + diff | `.png`, `.jpg`, `.zip` |
| ML Training | Loss/accuracy chart, epoch table | `.pt`, `.h5`, metrics `.json` |
| LLM Fine-tuning | Training curve, checkpoint browser | checkpoint `.zip` |
| Custom | Task-defined renderer | `.json`, `.txt`, `.zip` |

---

## 28. BENCHMARKING MODULE

All values must be **real measured numbers** — never hypothetical.

### Scalability Benchmark

| Workers | Execution Time | Speedup | Efficiency |
|---|---|---|---|
| 1 (baseline) | measured | 1× | 100% |
| 5 | measured | measured | measured |
| 10 | measured | measured | measured |
| 25 | measured | measured | measured |
| 50 | measured | measured | measured |
| 100 | measured | measured | measured |

### Scheduler Comparison (at fixed worker count)

| Strategy | Workers | Execution Time | Speedup vs Baseline |
|---|---|---|---|
| Round Robin | 10 | measured | measured |
| Least Loaded | 10 | measured | measured |
| Capacity Based | 10 | measured | measured |
| GPU Aware | 10 (GPU) | measured | measured |

Additional measurements per benchmark run: scheduling latency · aggregation time · network overhead · failure recovery time · Master CPU/RAM during job · chunk execution variance across workers.

---

## 29. COMMUNICATION LAYER DESIGN

| Purpose | Protocol | Notes |
|---|---|---|
| Worker discovery | UDP broadcast | Workers auto-discover Master on LAN |
| Real-time metrics & heartbeat | WebSocket | Persistent connection per worker |
| Job submission & REST API | HTTPS | FastAPI routes |
| Chunk dispatch | WebSocket | Master → Worker per assigned chunk |
| Result delivery | WebSocket | Worker → Master per completed chunk |
| Large dataset/model transfer | MinIO (S3 API) | Workers pull chunk data by reference |
| Job queue | Redis | Decouples job intake from scheduling |
| Rescheduling events | Redis Pub/Sub | Fault Recovery Engine publishes events |

Master never transfers large data through itself. It distributes **references** (MinIO paths). Workers pull input chunks and push result chunks directly to MinIO.

---

## 30. MANDATORY LIVE DEMO — 5-PC REGRESSION TEST

This is the required demonstration. Every step must work without manual intervention.

| Step | Action | Required Outcome |
|---|---|---|
| A | Start Master, then start 5 Workers | All 5 auto-discovered. Dashboard: 5 × 🟢 ONLINE. No manual IP entry. |
| B | View resource panel | Live CPU / RAM / GPU / VRAM % updating per worker in real time |
| C | Submit: Sort 1,000,000 numbers, Capacity Based | Job partitioned, distributed, live progress bar per worker visible |
| D | Watch dashboard mid-execution | Per-chunk assignment visible (W01 → CH001–CH004, etc.) |
| E | Kill Worker 3 mid-job | Dashboard: ⚠ WORKER-3 FAILED → affected chunks listed → Rescheduling |
| F | Watch auto-recovery | Failed chunks reassigned to healthy workers, job continues |
| G | Job completes | Dashboard: 1,000,000 / 1,000,000 · Validation ✓ PASSED |
| H | View provenance | Full Worker → Chunk → Attempt → Status table visible |
| I | View timeline | Full event log with timestamps visible |
| J | Download result | Globally sorted array downloads correctly as `.json` |
| K | Submit: Matrix Multiply | Correct mathematical matrix answer returned (not just "SUCCESS") |
| L | Submit: Statistics on dataset | Correct mean, median, min, max returned |
| M | View worker task history | Each worker's GUI shows history of all chunks it executed |
| N | Submit GPU job (if GPU available) | GPU-capable workers selected automatically; CPU-only workers excluded |

---

## 31. FULL ACCEPTANCE CHECKLIST

CoCompute is not considered complete until every item here is demonstrated and verified.

**Infrastructure**
- [ ] Automatic UDP discovery, zero manual IP entry
- [ ] Automatic worker registration with full hardware metadata
- [ ] JWT authentication for users; token-based auth for workers
- [ ] Multi-PC LAN operation (5+ physical machines minimum)
- [ ] Worker automatic reconnect after temporary disconnect
- [ ] TLS on all communication channels

**Monitoring**
- [ ] Live CPU, RAM, GPU, VRAM, temperature, network latency per worker
- [ ] Dynamic re-scoring — metrics update continuously, not at registration only
- [ ] Admin cluster-health dashboard with time-series graphs

**CIE — Intelligence**
- [ ] All 7 scheduling strategies implemented and switchable per job
- [ ] GPU-aware filtering (GPU tasks never go to CPU-only nodes)
- [ ] User priority and quota factored into scheduling

**Execution**
- [ ] Task SDK interface — all 7 methods implemented and enforced
- [ ] Dockerized execution — all tasks run in containers with resource limits
- [ ] Job and Chunk state machines with all transitions
- [ ] Chunk + ChunkAttempt provenance recorded for every job

**Fault Tolerance**
- [ ] Heartbeat monitoring (configurable interval and threshold)
- [ ] Immediate SUSPECTED on WebSocketDisconnect
- [ ] Automatic FAILED → rescheduling of all incomplete chunks
- [ ] Attempt retry tracking with attempt_number increment
- [ ] Duplicate result rejection (late results from failed attempts discarded)

**Correctness**
- [ ] Task-specific aggregation for every supported task (no generic concatenation)
- [ ] SHA-256 checksum verification per chunk result
- [ ] Partial validation before accepting any chunk result
- [ ] Global validation after full aggregation
- [ ] Actual correct final answer produced and verified

**Dashboard & UX**
- [ ] Live per-worker progress during job execution
- [ ] Worker provenance table (Worker → Chunk → Attempt → Status)
- [ ] Job timeline with timestamps for every event
- [ ] Actual result rendered (array, matrix, statistics, image, ML metrics)
- [ ] Result download in all required formats
- [ ] Worker task history in PySide6 GUI (drill-down per entry)

**GPU & ML**
- [ ] GPU metadata collected via pynvml per worker
- [ ] GPU-aware scheduling enforced
- [ ] PyTorch Distributed integration for ML training jobs
- [ ] Checkpoint saved to MinIO every N steps
- [ ] Worker failure during training → resume from last checkpoint
- [ ] LLM fine-tuning job end-to-end
- [ ] Final model artifact downloadable

**Artifact System**
- [ ] Per-job artifact bundle: config, timeline, provenance, partial results, final result, logs, checkpoints, model
- [ ] All artifacts browsable and downloadable from dashboard

**Multi-User Platform**
- [ ] Four roles: Student, Researcher, Faculty, Administrator
- [ ] Projects containing multiple Jobs
- [ ] Resource quotas per user (CPU hours, GPU count, VRAM, concurrent jobs)
- [ ] Admin panel: user management, quota management, cluster overview
- [ ] Audit log: all job submissions, admin actions, failures with timestamps

**Observability**
- [ ] All events searchable by job_id, worker_id, chunk_id, attempt_id
- [ ] Per-worker reliability scoring based on historical failure rate
- [ ] Throughput and utilization analytics over time

**Benchmarking**
- [ ] Speedup table (1 / 5 / 10 / 25 / 50 / 100 workers) — real measured values
- [ ] Scheduler strategy comparison table — real measured values
- [ ] Charts: execution time, speedup, efficiency, network overhead

**Scalability**
- [ ] Architecture validated at 5 / 10 / 25 / 50 nodes
- [ ] Design supports 100+ nodes (Redis queue, MinIO storage, stateless API)

---

## 32. ENGINEERING PHILOSOPHY

> **Build CoCompute as a platform, not a collection of demonstrations.**

Sorting is a test case.  
Matrix multiplication is a test case.  
Statistics is a test case.  
ML training is a workload.  
LLM fine-tuning is a workload.

**The actual product is the intelligent distributed execution infrastructure underneath all of them.**

The core loop is:

```
DISCOVER → MONITOR → ANALYZE → SCHEDULE → PARTITION
→ EXECUTE → TRACK → RECOVER → AGGREGATE → VALIDATE → RETURN
```

Everything in CoCompute exists to support this loop.

**The goal:**

> *Give an institution a large pool of heterogeneous computers and make them usable as one intelligent computing resource — without requiring ordinary users to understand distributed systems.*
