"""
Tests for CoCompute Worker Capability Detection Engine.
"""

import pytest
from worker.app.monitor.capabilities import (
    detect_os_and_arch,
    detect_cpu_info,
    detect_memory_and_disk,
    detect_gpu_capabilities,
    detect_docker_availability,
    detect_worker_capabilities,
    AGENT_VERSION,
    PROTOCOL_VERSION
)


def test_detect_os_and_arch():
    os_name, arch = detect_os_and_arch()
    assert os_name in ("Windows", "Linux", "macOS", "Unknown")
    assert arch in ("x64", "arm64", "x86", "unknown")


def test_detect_cpu_info():
    cpu = detect_cpu_info()
    assert "cpu_cores" in cpu
    assert isinstance(cpu["cpu_cores"], int)
    assert cpu["cpu_cores"] >= 1
    assert "cpu_model" in cpu
    assert isinstance(cpu["cpu_model"], str)
    assert "cpu_frequency" in cpu


def test_detect_memory_and_disk():
    mem = detect_memory_and_disk()
    assert "ram_gb" in mem
    assert "disk_gb" in mem
    assert mem["ram_gb"] > 0
    assert mem["disk_gb"] > 0


def test_detect_gpu_capabilities():
    gpu = detect_gpu_capabilities()
    assert "gpu" in gpu
    assert isinstance(gpu["gpu"], bool)
    assert "gpu_count" in gpu
    assert isinstance(gpu["gpu_count"], int)
    assert "vram_gb" in gpu
    assert "cuda_available" in gpu


def test_detect_docker_availability():
    docker_avail = detect_docker_availability()
    assert isinstance(docker_avail, bool)


def test_detect_worker_capabilities_physical():
    caps = detect_worker_capabilities("test-worker-physical", is_local=False)
    assert caps["worker_uid"] == "test-worker-physical"
    assert caps["worker_type"] == "PHYSICAL"
    assert caps["agent_version"] == AGENT_VERSION
    assert caps["protocol_version"] == PROTOCOL_VERSION
    assert "supported_tasks" in caps
    assert isinstance(caps["supported_tasks"], list)
    assert len(caps["supported_tasks"]) > 0
    assert "sort" in caps["supported_tasks"]
    assert "matrix_mult" in caps["supported_tasks"]


def test_detect_worker_capabilities_local():
    caps = detect_worker_capabilities("test-worker-local", is_local=True)
    assert caps["worker_uid"] == "test-worker-local"
    assert caps["worker_type"] == "LOCAL"
