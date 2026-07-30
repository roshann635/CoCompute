import psutil
import socket
import platform
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


def get_hardware_info() -> dict:
    """Collect static hardware information for registration."""
    return {
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "hostname": socket.gethostname(),
        "cpu_cores": psutil.cpu_count(logical=True),
        "ram_total": round(psutil.virtual_memory().total / (1024**3), 2),
        "disk_total": round(psutil.disk_usage('/').total / (1024**3), 2),
        "platform": f"{platform.system()} {platform.release()}"
    }


def get_current_metrics() -> dict:
    """Collect real-time system metrics including temperature and task count."""
    net_io = psutil.net_io_counters()

    # Try to get temperature (not available on all platforms)
    temperature = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            # Get the first available sensor
            for sensor_name, entries in temps.items():
                if entries:
                    temperature = entries[0].current
                    break
    except (AttributeError, Exception):
        pass  # Not supported on this platform

    return {
        "cpu_usage": psutil.cpu_percent(interval=None),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "network_tx": round(net_io.bytes_sent / (1024**2), 2),
        "network_rx": round(net_io.bytes_recv / (1024**2), 2),
        "running_tasks": get_running_tasks(),
        "temperature": temperature,
        "network_speed": round((net_io.bytes_sent + net_io.bytes_recv) / (1024**2), 2)
    }
