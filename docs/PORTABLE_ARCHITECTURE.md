# CoCompute Portable Architecture Specification
**Decoupled Compute Agent Architecture**

---

## 1. Architectural Tiers

CoCompute strictly separates the **Control Plane** (Master Node) from the **Compute Plane** (Worker Agents):

```
+-------------------------------------------------------------+
|                      CONTROL PLANE                          |
|  - FastAPI HTTP REST & WebSocket Gateway                   |
|  - UDP Auto-Discovery Responder (0.0.0.0:9999)              |
|  - Master Connect Code Generator (CC-XXXX)                 |
|  - Incarnation Lifecycle & Ephemeral Session Invalidation   |
|  - Optimistic Locking Scheduler & CAS Result Acceptance     |
|  - Result Checksum & SDK Partial/Final Validation           |
|  - Real-Time WebSocket Streaming to React Dashboard        |
+------------------------------+------------------------------+
                               |
                   Network Protocol v1.0
          (UDP Broadcast, HTTP API, Authenticated WS)
                               |
+------------------------------v------------------------------+
|                      COMPUTE PLANE                          |
|  - Standalone Portable Executable (CoComputeWorker.exe)     |
|  - Zero-Config UDP Discovery with Master Code Fallback      |
|  - Platform-Safe Config & Directory Resolver                |
|  - Automated Hardware & Capability Discovery Engine         |
|  - Pre-Flight Diagnostics Engine (CoCompute Doctor)         |
|  - Sandboxed Execution Engine (Docker / Isolated Subprocess)|
|  - Optional Desktop GUI (PySide6)                           |
+-------------------------------------------------------------+
```

---

## 2. Capability Detection & Reporting Contract

Every worker agent advertises a structured capability schema:
```json
{
  "worker_uid": "worker-uuid-v4",
  "hostname": "LAB-PC-01",
  "worker_type": "PHYSICAL",
  "os": "Windows",
  "architecture": "x64",
  "cpu_cores": 16,
  "cpu_model": "Intel Core i7-13620H",
  "cpu_frequency": 2.4,
  "ram_gb": 16.0,
  "disk_gb": 256.0,
  "gpu": true,
  "gpu_count": 1,
  "gpu_model": "NVIDIA GeForce RTX 4050 Laptop GPU",
  "vram_gb": 6.0,
  "cuda": "8.9",
  "cuda_available": true,
  "docker": false,
  "protocol_version": "1.0",
  "agent_version": "3.1.0",
  "supported_task_versions": ["1.0"],
  "supported_tasks": ["sort", "matrix_mult", "prime_search", "data_clean"]
}
```

---

## 3. Correctness & Fault Tolerant Invariants

1. **Ephemeral Sessions**: Worker session IDs are strictly unique per WebSocket connection. When network interrupts and restores, a new session is established. Results associated with prior sessions or prior Master incarnation IDs are rejected.
2. **Double Validation**: Worker computes partial validation (`validate_partial`) before submitting results. Master verifies SHA-256 checksum and executes partial validation again prior to atomic CAS acceptance.
3. **Graceful Degradation**: Incompatible or degraded workers (e.g. GPU=false) are never dispatched GPU tasks. The scheduler matches workload requirements against advertised capability bitmasks.
