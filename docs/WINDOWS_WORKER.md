# Windows Worker Deployment Guide
**Adding Windows Lab PCs with Zero Friction**

This guide describes how to onboard a clean Windows 10/11 machine into a CoCompute institutional cluster in under 60 seconds without installing Python or cloning code.

---

## 1. Prerequisites on Target Machine

- **Operating System**: Windows 10 or 11 (64-bit).
- **Network**: Connected to the same institutional Wi-Fi, Ethernet switch, or VPN as the Master node.
- **Python**: **NOT REQUIRED**.
- **Pip / Git / Compilers**: **NOT REQUIRED**.

---

## 2. Step-by-Step Onboarding (Under 60 Seconds)

### Step 1: Copy the Executable
Copy `CoComputeWorker.exe` to the target machine (via USB flash drive, shared network drive, or direct download link from Master).

### Step 2: Launch the Worker
Open PowerShell or Command Prompt, or simply double click `CoComputeWorker.exe`:

```cmd
CoComputeWorker.exe
```

### Step 3: Observe Auto-Discovery
The worker immediately sends a UDP broadcast across the local subnet on port `9999`:
```
2026-10-05 21:00:01 [Worker] Broadcasting discovery message to local network on port 9999...
2026-10-05 21:00:02 [Worker] Discovered Master Node at 192.168.1.15:8000 (Code: CC-4827)
2026-10-05 21:00:02 [Worker] Successfully registered with Master (PHYSICAL). Worker UID: win-lab-01
2026-10-05 21:00:03 [Worker] Connected to Master Node via WebSocket. Status: READY
```

### Step 4: Verify on Master Dashboard
Open the Master Web Dashboard (`http://<master-ip>:5173` or port 80). The new machine will appear in the **Workers** tab with a green `ONLINE` badge, marked as `PHYSICAL`.

---

## 3. Fallback: If Auto-Discovery Is Filtered

Some campus firewalls or university VLAN switches drop UDP broadcast packets. If the console displays `UDP auto-discovery timed out`, connect immediately using the Master Code displayed on the dashboard:

```cmd
CoComputeWorker.exe --code CC-4827
```

Or connect directly via IP:
```cmd
CoComputeWorker.exe --master 192.168.1.15:8000
```

Once connected, the endpoint is automatically saved in `%APPDATA%\CoCompute\worker_config.json`, so subsequent launches require no flags.

---

## 4. Running Pre-Flight Diagnostics

If the machine cannot connect or you wish to verify GPU and Docker status, run:

```cmd
CoComputeWorker.exe --doctor
```

Output:
```
============================================================
                CoCompute Doctor Diagnostics                
============================================================
[OK]   Operating System         Windows (Windows 11)
[OK]   Architecture             x64
[OK]   CPU                      16 cores (Intel Core i7)
[OK]   RAM                      16.0 GB total
[OK]   Network Interface        Active (IP: 192.168.1.45)
[OK]   Master Auto-Discovery    Found 192.168.1.15:8000
[OK]   Master Connectivity      Connected (192.168.1.15:8000)
[OK]   Protocol Compatibility   v1.0 (Agent v3.1.0)
[OK]   GPU Hardware             NVIDIA GeForce RTX 4050
[OK]   CUDA Runtime             detected
[WARN] Docker Daemon            Inactive / Not Found
------------------------------------------------------------
OVERALL DEPLOYMENT STATUS: READY
============================================================
```

---

## 5. Storage & Log Locations

All runtime state on Windows is kept in standard user folders:
- **Configuration**: `%APPDATA%\CoCompute\worker_config.json`
- **Execution Logs**: `%APPDATA%\CoCompute\logs\worker.log`
- **Task History**: `%APPDATA%\CoCompute\data\task_history.db`
