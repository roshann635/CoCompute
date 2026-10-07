# CoCompute Worker Troubleshooting Guide
**Diagnostic Matrix & Failure Recovery**

When a worker node experiences connection difficulties or execution errors, use this troubleshooting matrix to resolve the problem rapidly.

---

## Diagnostic Matrix

| Symptom / Error | Root Cause | Immediate Solution |
|---|---|---|
| **UDP Auto-Discovery Timed Out** | Institutional Wi-Fi / switch blocks UDP broadcast port 9999. | 1. Use the Master Connect Code displayed on the dashboard: `CoComputeWorker.exe --code CC-4827`<br>2. Or provide Master IP directly: `--master-ip <IP> --master-port 8000`. |
| **Connection Refused on Port 8000** | Master node is offline or Windows/Linux firewall on Master blocks port 8000. | 1. Ensure `python -m master.app.main` is running on Master.<br>2. Add inbound firewall rule on Master for TCP port 8000.<br>3. Verify ping from worker to master IP. |
| **Invalid Worker Token (4001 Close)** | Shared secret mismatch between Master and Worker. | Verify `COCOMPUTE_WORKER_SECRET` matches across both Master and Worker environment variables (defaults to `cocompute-default-cluster-secret-2026`). |
| **Worker Shows DEGRADED Status** | Worker lacks dedicated NVIDIA GPU or active Docker daemon. | Worker is fully functional for Tier 1 CPU workloads (Sorting, Matrix Mult, Primes, Data Clean). No action required unless GPU/container tasks are mandatory. |
| **Stale Attempt / Checksum Mismatch** | Network dropped during task execution or attempt timed out before submission. | Master automatically reschedules the chunk to a healthy worker. The reconnecting worker is assigned a new ephemeral session ID; stale results are safely rejected. |
| **Cannot Import PySide6** | Headless machine lacks Qt/GUI libraries. | Run in headless mode using `start_worker.py --cli`. The core worker never requires PySide6 or graphics drivers. |
| **Permission Denied Writing Config** | Application placed in read-only directory. | CoCompute stores config in user application data (`%APPDATA%\CoCompute` on Windows, `~/.config/cocompute` on Linux), avoiding permission errors. |

---

## Running the Doctor

To run an automated health check:
```cmd
CoComputeWorker.exe --doctor
```
The Doctor evaluates OS, architecture, memory, CPU, discovery, API reachability, and capability state, outputting specific remedies for each failed check.
