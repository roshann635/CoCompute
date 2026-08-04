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


def get_hardware_info() -> dict:
    """Collect static hardware information for registration (FR-2)."""
    disk_total, _ = _get_disk_usage()
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "127.0.0.1"

    return {
        "ip_address": ip,
        "hostname": socket.gethostname(),
        "cpu_cores": psutil.cpu_count(logical=True),
        "ram_total": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "disk_total": disk_total,
        "platform": f"{platform.system()} {platform.release()}"
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
