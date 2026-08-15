"""
CoCompute Shared Network Protocol Definitions.
Contains standard action names, message types, and key names.
"""
import hashlib
import json
from typing import Any

# Message Types (Actions)
ACTION_DISCOVER = "DISCOVER"
ACTION_DISCOVER_RESPONSE = "DISCOVER_RESPONSE"
ACTION_REGISTER = "REGISTER"
ACTION_HEARTBEAT = "HEARTBEAT"
ACTION_METRICS = "METRICS"
ACTION_EXECUTE = "EXECUTE"
ACTION_RESULT = "RESULT"
ACTION_CHUNK_STATUS = "CHUNK_STATUS"   # Worker → Master progress updates
ACTION_RESCHEDULE = "RESCHEDULE"       # Internal rescheduling event

# Worker states
STATE_ONLINE = "online"
STATE_OFFLINE = "offline"
STATE_BUSY = "busy"

# Chunk status states (state machine)
CHUNK_PENDING = "pending"
CHUNK_ASSIGNED = "assigned"
CHUNK_RUNNING = "running"
CHUNK_COMPLETED = "completed"
CHUNK_FAILED = "failed"
CHUNK_TIMEOUT = "timeout"
CHUNK_RESCHEDULED = "rescheduled"

# Chunk attempt statuses
ATTEMPT_ASSIGNED = "assigned"
ATTEMPT_RUNNING = "running"
ATTEMPT_COMPLETED = "completed"
ATTEMPT_FAILED = "failed"
ATTEMPT_TIMEOUT = "timeout"

# Protocol payload keys
FIELD_CHECKSUM = "checksum"
FIELD_CHUNK_ID = "chunk_id"
FIELD_CHUNK_UID = "chunk_uid"
FIELD_RESULT_DATA = "result_data"
FIELD_GPU_METRICS = "gpu_metrics"

# Defaults
DEFAULT_UDP_PORT = 9999
DEFAULT_HTTP_PORT = 8000


def compute_checksum(data: Any) -> str:
    """Compute deterministic SHA-256 checksum of payload/result data."""
    if isinstance(data, (dict, list)):
        payload_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
    elif isinstance(data, str):
        payload_bytes = data.encode("utf-8")
    elif isinstance(data, bytes):
        payload_bytes = data
    else:
        payload_bytes = str(data).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload_bytes).hexdigest()}"


def verify_checksum(data: Any, expected_checksum: str) -> bool:
    """Verify SHA-256 checksum."""
    if not expected_checksum:
        return True
    return compute_checksum(data) == expected_checksum
