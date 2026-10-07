# CoCompute Transparent Demo Mode
**Multi-Worker Demonstration & Stress Testing**

CoCompute Demo Mode allows running multiple concurrent local compute agents on a single machine alongside physical lab PCs.

---

## 1. What Demo Mode Is & Is Not

- **It IS**: A legitimate multi-process distributed compute deployment where each worker agent runs in its own process, maintains an independent WebSocket connection, receives distinct task chunks from the scheduler, executes computations in parallel, and submits validated results with cryptographic checksums.
- **It is NOT**: A fabricated UI simulation or hardcoded mock. The exact same scheduler, partitioning, partial validation, CAS acceptance, and k-way merging are executed.
- **Transparency**: Every demo worker is explicitly tagged with `worker_type = "LOCAL"`. The Master Dashboard displays distinct `LOCAL` and `PHYSICAL` badges so observers can clearly distinguish local demo agents from actual physical machines.

---

## 2. Launching Demo Mode

To launch 3 local worker agents against the local Master:
```cmd
python worker/demo_cluster.py --count 3
```

To connect local workers to a remote Master on the LAN:
```cmd
python worker/demo_cluster.py --count 4 --master 192.168.1.15:8000
```
Or using the Master Connect Code:
```cmd
python worker/demo_cluster.py --count 4 --code CC-4827
```

---

## 3. Instance Isolation

Each local worker instance is automatically provisioned with:
- **Unique Worker UID**: `local-worker-01-a1b2c3`
- **Unique Hostname**: `LOCAL-AGENT-01`
- **Ephemeral Session ID**: Managed per WebSocket connection
- **Independent Task History**: Kept distinct from other processes

When all workers are running, submitting a distributed job (e.g. 100,000-element distributed sorting) partitions the workload across both physical machines and local demo agents seamlessly.
