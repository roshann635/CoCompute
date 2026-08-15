"""
CoCompute Integrity Verification Service.

Provides cryptographic SHA-256 computation and verification utilities
to guarantee result integrity across all worker nodes before acceptance
into aggregation pipelines.
"""

import hashlib
import json
from typing import Any, Union


def compute_sha256(data: Union[bytes, str, dict, list, Any]) -> str:
    """
    Compute deterministic SHA-256 hex digest for bytes, strings, or JSON-serializable structures.
    """
    if isinstance(data, bytes):
        raw_bytes = data
    elif isinstance(data, str):
        raw_bytes = data.encode("utf-8")
    else:
        raw_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def verify_checksum(data: Union[bytes, str, dict, list, Any], expected: str) -> bool:
    """
    Verify if computed SHA-256 matches expected checksum hex string.
    """
    if not expected:
        return False
    computed = compute_sha256(data)
    return computed.lower() == expected.lower()
