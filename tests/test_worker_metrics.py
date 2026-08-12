import pytest
from worker.app.monitor.metrics import get_hardware_info, get_current_metrics

def test_get_hardware_info():
    info = get_hardware_info()
    assert "ip_address" in info
    assert "hostname" in info
    assert "cpu_cores" in info
    assert "ram_total" in info
    assert "disk_total" in info
    assert "platform" in info
    assert "cpu_model" in info
    assert "cpu_frequency" in info
    assert "mac_address" in info
    assert info["agent_version"] == "1.0.0"
    assert "python_version" in info


def test_get_current_metrics():
    metrics = get_current_metrics()
    assert "cpu_usage" in metrics
    assert "ram_usage" in metrics
    assert "disk_usage" in metrics
    assert "network_tx" in metrics
    assert "network_rx" in metrics
    assert "running_tasks" in metrics
    assert "network_speed" in metrics
