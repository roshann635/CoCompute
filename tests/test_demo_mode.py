"""
Tests for transparent Demo Mode cluster launcher.
"""

import os
from worker.app.monitor.capabilities import detect_worker_capabilities


def test_demo_worker_identity_tagging():
    # Verify local worker has worker_type LOCAL
    caps = detect_worker_capabilities("local-worker-01-abc", is_local=True)
    assert caps["worker_type"] == "LOCAL"
    assert caps["worker_uid"] == "local-worker-01-abc"

    # Verify physical worker has worker_type PHYSICAL
    caps_phys = detect_worker_capabilities("phys-worker-01-xyz", is_local=False)
    assert caps_phys["worker_type"] == "PHYSICAL"
    assert caps_phys["worker_uid"] == "phys-worker-01-xyz"


def test_demo_worker_hostname_override(monkeypatch):
    monkeypatch.setenv("WORKER_HOSTNAME", "LOCAL-AGENT-05")
    caps = detect_worker_capabilities("local-worker-05", is_local=True)
    assert caps["hostname"] == "LOCAL-AGENT-05"
