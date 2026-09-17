"""
CoCompute Hardening: Failure Policy & Retry Budget Semantics

Distinguishes between retryable, non-retryable, and worker-specific failures.
Ensures non-retryable failures fail immediately without burning retry budget.
"""

RETRYABLE_FAILURES = {
    "worker_failure",
    "network_failure",
    "timeout",
    "disconnect",
    "worker_disconnected",
    "reconnect_stale",
}

NON_RETRYABLE_FAILURES = {
    "invalid_input",
    "execution_error",
    "deterministic_crash",
    "unsupported_task",
}

RETRY_OTHER_WORKER = {
    "corrupted_result",
    "checksum_failure",
    "validation_failed",
    "oom_worker_limit",
}


def classify_failure(reason: str) -> str:
    """
    Classifies a failure reason into:
    - NON_RETRYABLE: deterministic failures that should fail the chunk/job immediately.
    - RETRY_OTHER_WORKER: failures caused by worker state/corruption; retry on a different worker.
    - RETRYABLE: transient worker/network failures; retryable.
    """
    if not reason:
        return "RETRYABLE"
    
    reason_clean = reason.lower().strip()
    
    for nr in NON_RETRYABLE_FAILURES:
        if nr in reason_clean:
            return "NON_RETRYABLE"
            
    for ro in RETRY_OTHER_WORKER:
        if ro in reason_clean:
            return "RETRY_OTHER_WORKER"
            
    for rf in RETRYABLE_FAILURES:
        if rf in reason_clean:
            return "RETRYABLE"
            
    return "RETRYABLE"


def should_retry(chunk, failure_type: str) -> bool:
    """
    Returns True if chunk can still be retried based on retry budget.
    Non-retryable failures NEVER retry.
    """
    if failure_type == "NON_RETRYABLE":
        return False
        
    normal_count = getattr(chunk, "normal_attempt_count", 0) or 0
    max_retries = getattr(chunk, "max_retries", 3) or 3
    
    return normal_count < max_retries
