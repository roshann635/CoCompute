"""
Tests for Master auto-discovery, Master Connect Code generation and parsing.
"""

from master.app.network.discovery import get_master_code
from worker.app.core_config import parse_master_code
from worker.app.network.discovery import MasterEndpoint


def test_get_master_code_deterministic():
    code1 = get_master_code("192.168.1.100", 8000)
    code2 = get_master_code("192.168.1.100", 8000)
    assert code1.startswith("CC-")
    assert code1 == code2
    assert len(code1) == 7  # 'CC-' + 4 chars


def test_get_master_code_env_override(monkeypatch):
    monkeypatch.setenv("MASTER_CODE", "CC-TEST")
    code = get_master_code("192.168.1.100", 8000)
    assert code == "CC-TEST"


def test_parse_master_code_octet_format():
    res = parse_master_code("CC-192-168-1-50-8000")
    assert res == ("192.168.1.50", 8000)


def test_master_endpoint_tuple_compatibility():
    ep = MasterEndpoint("10.0.0.5", 8000, "CC-ABCD")
    # Verify 2-tuple unpacking works
    ip, port = ep
    assert ip == "10.0.0.5"
    assert port == 8000
    assert len(ep) == 2
    # Verify attribute access works
    assert ep.ip == "10.0.0.5"
    assert ep.port == 8000
    assert ep.code == "CC-ABCD"
