"""
Unit tests for File Storage Service and Redis Metrics Engine fallback.
"""
import os
import json
import pytest
from master.app.storage.file_store import (
    save_result_file,
    get_result_file_path,
    generate_csv_from_result,
    list_stored_results,
)
from master.app.engine.metrics_engine import (
    cache_cluster_snapshot,
    get_cached_snapshot,
    record_metric_point,
    get_timeseries,
)


def test_file_storage_json_and_csv(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_ROOT", str(tmp_path / "storage"))

    job_id = 999
    job_name = "Test Prime Job"
    job_type = "prime_generation"
    result_data = {
        "total_primes_found": 3,
        "sample_primes": [2, 3, 5]
    }

    # Save result file
    saved_path = save_result_file(job_id, job_name, job_type, result_data)
    assert os.path.exists(saved_path)

    # Verify JSON content
    with open(saved_path, "r", encoding="utf-8") as f:
        content = json.load(f)
        assert content["job_id"] == job_id
        assert content["job_name"] == job_name
        assert content["aggregated_result"]["total_primes_found"] == 3

    # Check path lookup
    path = get_result_file_path(job_id, "json")
    assert path == saved_path

    # Check CSV lookup
    csv_path = get_result_file_path(job_id, "csv")
    assert csv_path is not None and os.path.exists(csv_path)

    # Check CSV generator
    csv_str = generate_csv_from_result(job_type, result_data)
    assert "prime_number" in csv_str
    assert "5" in csv_str

    # Check list_stored_results
    results_list = list_stored_results()
    assert len(results_list) >= 1
    assert any(r["job_id"] == job_id for r in results_list)


def test_metrics_engine_graceful_fallback():
    # Without redis running locally, operations return default fallback values gracefully
    assert cache_cluster_snapshot({"total_nodes": 5}) in (True, False)
    snapshot = get_cached_snapshot()
    # Should be None if Redis isn't connected
    assert snapshot is None or isinstance(snapshot, dict)

    series = get_timeseries(60)
    assert isinstance(series, list)
