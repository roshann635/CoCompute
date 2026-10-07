"""
Tests for CoCompute Doctor pre-flight diagnostic system.
"""

import asyncio
from worker.app.diagnostics.doctor import run_diagnostics, format_doctor_report


def test_run_diagnostics_structure():
    diag = asyncio.run(run_diagnostics(master_ip="127.0.0.1", master_port=99999))
    assert "status" in diag
    assert diag["status"] in ("READY", "DEGRADED", "FAILED")
    assert "checks" in diag
    assert len(diag["checks"]) >= 10

    names = [c["name"] for c in diag["checks"]]
    assert "Operating System" in names
    assert "Architecture" in names
    assert "CPU" in names
    assert "RAM" in names
    assert "Network Interface" in names
    assert "GPU Hardware" in names
    assert "Docker Daemon" in names


def test_format_doctor_report():
    diag = asyncio.run(run_diagnostics(master_ip="127.0.0.1", master_port=99999))
    report = format_doctor_report(diag)
    assert "CoCompute Doctor Diagnostics" in report
    assert "OVERALL DEPLOYMENT STATUS:" in report
