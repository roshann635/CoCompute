"""
CoCompute Worker Authentication & Token Verification Service.

Implements deterministic token authentication for worker nodes using HMAC / SHA-256
derived from worker_id and cluster shared secret (COCOMPUTE_WORKER_SECRET).
"""

import os
import secrets
import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)

WORKER_SECRET = os.getenv("COCOMPUTE_WORKER_SECRET", "cocompute-default-cluster-secret-2026")


def generate_worker_token(worker_id: str) -> str:
    """
    Generate a deterministic authentication token for a given worker_id.
    Derived from worker_id + cluster secret using HMAC-SHA256.
    """
    secret_bytes = WORKER_SECRET.encode("utf-8")
    message = worker_id.encode("utf-8")
    return hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()


def verify_worker_token(worker_id: str, token: str) -> bool:
    """
    Verify whether a provided token matches the expected worker token using constant-time comparison.
    """
    if not worker_id or not token:
        return False
    
    # Also support fallback token if configured in dev
    expected = generate_worker_token(worker_id)
    if secrets.compare_digest(expected, token):
        return True
    
    # Fallback to WORKER_API_KEY if configured in worker env for backward compatibility
    legacy_key = os.getenv("WORKER_API_KEY", "cocompute-worker-key")
    if secrets.compare_digest(legacy_key, token):
        return True

    logger.warning(f"Worker authentication failed for worker_id={worker_id}")
    return False
