import psutil
import socket
import platform
import sys
import threading

# Thread-safe running task counter
_running_tasks = 0
_lock = threading.Lock()


def increment_running_tasks():
    global _running_tasks
    with _lock:
        _running_tasks += 1


def decrement_running_tasks():
    global _running_tasks
    with _lock:
        _running_tasks = max(0, _running_tasks - 1)


def get_running_tasks() -> int:
    with _lock:
        return _running_tasks


def _get_disk_usage() -> tuple[float, float]:
    """
    Cross-platform disk usage.
    Returns (total_gb, usage_percent).
    Uses C:\\ on Windows and / on Linux/macOS.
    """
    if sys.platform.startswith("win"):
        paths_to_try = ["C:\\", "D:\\", "/"]
    else:
        paths_to_try = ["/"]

    for path in paths_to_try:
        try:
            usage = psutil.disk_usage(path)
            return (
                round(usage.total / (1024 ** 3), 2),
                round(usage.percent, 1)
            )
        except (PermissionError, FileNotFoundError, OSError):
            continue

    # Final fallback: 0 values to avoid crashing
    return 0.0, 0.0


def _get_cpu_model() -> str:
    """Cross-platform method to get CPU model name."""
    import sys
    system = platform.system()
    if system == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            model, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return str(model).strip()
        except Exception:
            return platform.processor() or "Unknown CPU"
    elif system == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    elif system == "Darwin":
        try:
            import subprocess
            return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
        except Exception:
            pass
    return platform.processor() or "Unknown CPU"


def _get_mac_address() -> str:
    """Get the formatted MAC address of the host."""
    import uuid
    mac = uuid.getnode()
    return ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))


def _get_cpu_frequency() -> float:
    """Get CPU frequency in GHz."""
    try:
        freq = psutil.cpu_freq()
        if freq:
            return round((freq.current or freq.max or 0.0) / 1000.0, 2)
    except Exception:
        pass
    return 0.0


def get_hardware_info() -> dict:
    """Collect static hardware information for registration (FR-2)."""
    disk_total, _ = _get_disk_usage()
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "127.0.0.1"

    import sys
    return {
        "ip_address": ip,
        "hostname": socket.gethostname(),
        "cpu_cores": psutil.cpu_count(logical=True),
        "ram_total": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "disk_total": disk_total,
        "platform": f"{platform.system()} {platform.release()}",
        "cpu_model": _get_cpu_model(),
        "cpu_frequency": _get_cpu_frequency(),
        "mac_address": _get_mac_address(),
        "agent_version": "1.0.0",
        "python_version": sys.version.split()[0]
    }


def get_current_metrics() -> dict:
    """Collect real-time system metrics including temperature and task count (FR-3)."""
    net_io = psutil.net_io_counters()
    _, disk_percent = _get_disk_usage()

    # Try to get temperature (not available on all platforms)
    temperature = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for sensor_name, entries in temps.items():
                if entries:
                    temperature = entries[0].current
                    break
    except (AttributeError, Exception):
        pass  # Not supported on this platform

    return {
        "cpu_usage": psutil.cpu_percent(interval=None),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": disk_percent,
        "network_tx": round(net_io.bytes_sent / (1024 ** 2), 2),
        "network_rx": round(net_io.bytes_recv / (1024 ** 2), 2),
        "running_tasks": get_running_tasks(),
        "temperature": temperature,
        "network_speed": round((net_io.bytes_sent + net_io.bytes_recv) / (1024 ** 2), 2)
    }
