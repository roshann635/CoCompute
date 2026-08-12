"""
CoCompute Shared Configuration Loader.
Loads settings from environment variables with defaults.
"""
import os

# Server defaults
MASTER_IP = os.getenv("MASTER_IP", "127.0.0.1")
MASTER_PORT = int(os.getenv("MASTER_PORT", "8000"))
UDP_DISCOVERY_PORT = int(os.getenv("UDP_DISCOVERY_PORT", "9999"))

# Security
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "cocompute-production-secret-change-me")
WORKER_API_KEY = os.getenv("WORKER_API_KEY", "cocompute-worker-key")

# Health Thresholds
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "15"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# FR-14 Load balancing thresholds
HIGH_UTILIZATION_THRESHOLD = float(os.getenv("HIGH_UTILIZATION_THRESHOLD", "85.0"))
HIGH_RAM_THRESHOLD = float(os.getenv("HIGH_RAM_THRESHOLD", "90.0"))
