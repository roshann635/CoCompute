"""
Tests for platform-safe path resolution and configuration persistence.
"""

import os
from pathlib import Path
from worker.app.core_config import (
    get_base_dir,
    get_config_path,
    get_log_dir,
    get_log_path,
    get_data_dir,
    load_config,
    save_config
)


def test_paths_are_valid():
    base = get_base_dir()
    assert isinstance(base, Path)
    assert base.exists()

    cfg_path = get_config_path()
    assert isinstance(cfg_path, Path)
    assert str(base) in str(cfg_path)

    log_path = get_log_path()
    assert isinstance(log_path, Path)
    assert str(base) in str(log_path)

    data_dir = get_data_dir()
    assert isinstance(data_dir, Path)
    assert data_dir.exists()


def test_config_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    save_config({"master_ip": "192.168.1.99", "master_port": 8000, "master_code": "CC-9999"})
    loaded = load_config()

    assert loaded.get("master_ip") == "192.168.1.99"
    assert loaded.get("master_port") == 8000
    assert loaded.get("master_code") == "CC-9999"
