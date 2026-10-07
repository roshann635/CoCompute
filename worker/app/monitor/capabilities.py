"""
CoCompute Worker Automatic Capability Detection Engine.

Discovers hardware specs, platform architecture, GPU/CUDA features,
Docker daemon availability, and supported task types with robust, safe fallbacks.
"""

import sys
import os
import platform
import shutil
import subprocess
import socket
import logging
from typing import Dict, Any, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)

AGENT_VERSION = "3.1.0"
PROTOCOL_VERSION = "1.0"
SUPPORTED_TASK_VERSIONS = ["1.0"]
DEFAULT_SUPPORTED_TASKS = [
    "sort",
    "matrix_mult",
    "prime_search",
    "data_clean",
    "compression",
    "generic_python"
]


def detect_os_and_arch() -> tuple[str, str]:
    """Detect normalized OS name and CPU architecture."""
    raw_system = platform.system()
    if raw_system == "Windows":
        os_name = "Windows"
    elif raw_system == "Linux":
        os_name = "Linux"
    elif raw_system == "Darwin":
        os_name = "macOS"
    else:
        os_name = raw_system or "Unknown"

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "x64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("i386", "i686", "x86"):
        arch = "x86"
    else:
        arch = machine or "unknown"

    return os_name, arch


def detect_cpu_info() -> Dict[str, Any]:
    """Detect CPU model, physical and logical core counts, and frequency."""
    cores = os.cpu_count() or 1
    if psutil:
        try:
            cores = psutil.cpu_count(logical=True) or cores
        except Exception:
            pass

    freq_ghz = 0.0
    if psutil:
        try:
            freq = psutil.cpu_freq()
            if freq:
                freq_ghz = round((freq.current or freq.max or 0.0) / 1000.0, 2)
        except Exception:
            pass

    model = "Unknown CPU"
    system = platform.system()
    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            model = str(val).strip()
        except Exception:
            model = platform.processor() or "Unknown CPU"
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        model = line.split(":", 1)[1].strip()
                        break
        except Exception:
            model = platform.processor() or "Unknown CPU"
    elif system == "Darwin":
        try:
            model = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], timeout=2).decode().strip()
        except Exception:
            model = platform.processor() or "Unknown CPU"
    else:
        model = platform.processor() or "Unknown CPU"

    return {
        "cpu_cores": cores,
        "cpu_model": model,
        "cpu_frequency": freq_ghz
    }


def detect_memory_and_disk() -> Dict[str, float]:
    """Detect total RAM (GB) and main disk capacity (GB)."""
    ram_gb = 4.0
    disk_gb = 20.0

    if psutil:
        try:
            ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        except Exception:
            pass

        paths_to_try = ["C:\\", "D:\\"] if sys.platform.startswith("win") else ["/"]
        for p in paths_to_try:
            try:
                usage = psutil.disk_usage(p)
                disk_gb = round(usage.total / (1024 ** 3), 2)
                break
            except Exception:
                continue

    return {
        "ram_gb": ram_gb,
        "disk_gb": disk_gb
    }


def detect_gpu_capabilities() -> Dict[str, Any]:
    """
    Detect GPU presence, model, total VRAM, and CUDA capability.
    Uses PyTorch if present, or queries nvidia-smi with safe timeouts.
    """
    gpu_info = {
        "gpu": False,
        "gpu_count": 0,
        "gpu_model": "None",
        "vram_gb": 0.0,
        "cuda": None,
        "cuda_available": False
    }

    # 1. Try PyTorch CUDA if available in current python environment
    try:
        import torch
        if torch.cuda.is_available():
            count = torch.cuda.device_count()
            if count > 0:
                gpu_info["gpu"] = True
                gpu_info["gpu_count"] = count
                gpu_info["gpu_model"] = torch.cuda.get_device_name(0)
                props = torch.cuda.get_device_properties(0)
                gpu_info["vram_gb"] = round(props.total_memory / (1024 ** 3), 2)
                gpu_info["cuda_available"] = True
                major, minor = torch.cuda.get_device_capability(0)
                gpu_info["cuda"] = f"{major}.{minor}"
                return gpu_info
    except Exception:
        pass

    # 2. Probe nvidia-smi CLI
    if shutil.which("nvidia-smi"):
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits"
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=2).decode().strip()
            lines = [l.strip() for l in out.split("\n") if l.strip()]
            if lines:
                parts = [p.strip() for p in lines[0].split(",")]
                gpu_info["gpu"] = True
                gpu_info["gpu_count"] = len(lines)
                gpu_info["gpu_model"] = parts[0]
                if len(parts) >= 2:
                    try:
                        total_mb = float(parts[1])
                        gpu_info["vram_gb"] = round(total_mb / 1024.0, 2)
                    except ValueError:
                        pass
                gpu_info["cuda_available"] = True
                gpu_info["cuda"] = "detected"
        except Exception:
            pass

    return gpu_info


def detect_docker_availability() -> bool:
    """Check if Docker CLI is installed and the daemon is reachable."""
    if shutil.which("docker") is None:
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=2
        )
        return res.returncode == 0
    except Exception:
        return False


def get_supported_task_types() -> List[str]:
    """Retrieve all task types supported by local worker runtime."""
    try:
        from shared.sdk.registry import TaskRegistry
        tasks = TaskRegistry.list_tasks()
        if tasks:
            return tasks
    except Exception:
        pass
    return list(DEFAULT_SUPPORTED_TASKS)


def detect_worker_capabilities(worker_uid: str, is_local: bool = False) -> Dict[str, Any]:
    """
    Collect comprehensive worker capability snapshot.
    Guaranteed to return safe explicit values for all expected fields.
    """
    os_name, arch = detect_os_and_arch()
    cpu = detect_cpu_info()
    mem = detect_memory_and_disk()
    gpu = detect_gpu_capabilities()
    docker_ok = detect_docker_availability()
    tasks = get_supported_task_types()

    try:
        hostname = os.getenv("WORKER_HOSTNAME") or socket.gethostname()
    except Exception:
        hostname = "cocompute-worker"

    return {
        "worker_uid": worker_uid,
        "hostname": hostname,
        "worker_type": "LOCAL" if is_local else "PHYSICAL",
        "os": os_name,
        "architecture": arch,
        "cpu_cores": cpu["cpu_cores"],
        "cpu_model": cpu["cpu_model"],
        "cpu_frequency": cpu["cpu_frequency"],
        "ram_gb": mem["ram_gb"],
        "disk_gb": mem["disk_gb"],
        "gpu": gpu["gpu"],
        "gpu_count": gpu["gpu_count"],
        "gpu_model": gpu["gpu_model"],
        "vram_gb": gpu["vram_gb"],
        "cuda": gpu["cuda"],
        "cuda_available": gpu["cuda_available"],
        "docker": docker_ok,
        "protocol_version": PROTOCOL_VERSION,
        "agent_version": AGENT_VERSION,
        "supported_task_versions": SUPPORTED_TASK_VERSIONS,
        "supported_tasks": tasks
    }
