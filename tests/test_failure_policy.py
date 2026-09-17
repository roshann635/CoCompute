"""
Test Suite: Failure Policy & Retry Budget Isolation
Tests failure classification, retry budget separation, and non-retryable immediate failure.
"""

import pytest
from master.app.engine.failure_policy import classify_failure, should_retry
from master.app.db import models


def test_failure_classification():
    """Verify classification of different error types."""
    assert classify_failure("Worker disconnected unexpectedly") == "RETRYABLE"
    assert classify_failure("Timeout waiting for result") == "RETRYABLE"
    assert classify_failure("Invalid_input: array cannot be empty") == "NON_RETRYABLE"
    assert classify_failure("Deterministic Execution_Error in bytecode") == "NON_RETRYABLE"
    assert classify_failure("Checksum_failure detected in buffer") == "RETRY_OTHER_WORKER"
    assert classify_failure("Validation_failed: multiset mismatch") == "RETRY_OTHER_WORKER"


def test_should_retry_budget_enforcement():
    """Verify retry budget is respected and non-retryable errors fail immediately."""
    class DummyChunk:
        def __init__(self, normal_count=0, max_retries=3):
            self.normal_attempt_count = normal_count
            self.max_retries = max_retries

    chunk = DummyChunk(normal_count=0, max_retries=3)
    
    # Retryable within budget
    assert should_retry(chunk, "RETRYABLE") is True
    
    # Non-retryable fails immediately without burning budget
    assert should_retry(chunk, "NON_RETRYABLE") is False
    
    # Exhausted budget
    chunk.normal_attempt_count = 3
    assert should_retry(chunk, "RETRYABLE") is False
