# Linux Worker Deployment Guide
**Deploying Linux Lab Machines & Compute Nodes**

This guide outlines deployment on Linux x64 platforms.

---

## 1. Operating System Support Matrix

| Platform | Architecture | Status | Notes |
|---|---|---|---|
| **Ubuntu 22.04 / 24.04 LTS** | x86_64 / x64 | **SUPPORTED** | Verified with Python 3.10+ and standard socket runtime |
| **Debian 12** | x86_64 / x64 | **SUPPORTED** | Verified with standard glibc |
| **RHEL / Rocky / AlmaLinux 9**| x86_64 / x64 | **SUPPORTED** | Ensure firewalld permits TCP port 8000 outbound |
| **Arch / Fedora** | x86_64 / x64 | **SUPPORTED** | Standard Python 3 runtime |
| **ARM64 / Raspberry Pi** | aarch64 | **NOT TESTED** | Hardware build not validated in current lab setup |
| **macOS (Darwin)** | Apple Silicon | **NOT TESTED** | Architecture planned for future release |

---

## 2. Zero-Friction Launcher Options

### Option A: Portable Standalone Binary
If built via `scripts/build_worker_linux.sh`:
```bash
./dist/linux/cocompute-worker --cli
```

### Option B: Native Python Headless Run
If Python 3.10+ is installed on the Linux system:
```bash
python3 worker/start_worker.py --cli
```
*Note*: No GUI dependencies (such as Qt/PySide6) or X11/Wayland display servers are required.

---

## 3. Auto-Discovery & Firewall Rules

The worker broadcasts UDP datagrams to `255.255.255.255:9999` and local subnet broadcast addresses.

If the institutional firewall drops outbound UDP broadcasts, connect directly using the Master Code or endpoint:
```bash
./cocompute-worker --code CC-4827
# or
./cocompute-worker --master 192.168.1.15:8000
```

---

## 4. Running Pre-Flight Diagnostics

To evaluate Linux kernel, CPU cores, RAM, and Docker status:
```bash
./cocompute-worker --doctor
```

---

## 5. Linux Path Conventions

In accordance with XDG standards:
- **Configuration**: `~/.config/cocompute/worker_config.json` (or `$XDG_CONFIG_HOME/cocompute`)
- **Worker Logs**: `~/.config/cocompute/logs/worker.log`
- **Task History**: `~/.config/cocompute/data/task_history.db`
