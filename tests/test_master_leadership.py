"""
Test Suite: Master Leadership Lease & Split-Brain Prevention
Tests lease acquisition, renewal, CAS contention between multiple masters, and expiry takeover.
"""

import pytest
from datetime import datetime, timezone, timedelta
from master.app.engine.leadership import (
    acquire_or_renew_lease, is_leader, release_lease, ensure_lease_row
)
from master.app.db import models


def test_master_lease_acquisition_and_leadership(db_session):
    """Verifies that a master instance can acquire and maintain leadership."""
    incarnation_1 = "master-node-01"
    
    # Initial acquisition
    acquired = acquire_or_renew_lease(db_session, incarnation_1, "host-a")
    assert acquired is True
    assert is_leader(db_session, incarnation_1) is True
    assert is_leader(db_session, "master-node-02") is False


def test_master_split_brain_protection(db_session):
    """Verifies that two simultaneous masters cannot hold leadership concurrently."""
    master_a = "master-node-a"
    master_b = "master-node-b"
    
    # Master A takes lease
    acquired_a = acquire_or_renew_lease(db_session, master_a, "host-a")
    assert acquired_a is True
    
    # Master B attempts to take unexpired lease -> REJECTED
    acquired_b = acquire_or_renew_lease(db_session, master_b, "host-b")
    assert acquired_b is False
    
    # Master A remains the sole leader
    assert is_leader(db_session, master_a) is True
    assert is_leader(db_session, master_b) is False


def test_master_lease_expiry_takeover(db_session):
    """Verifies that if Master A's lease expires, Master B can take over."""
    master_a = "master-node-a"
    master_b = "master-node-b"
    
    acquire_or_renew_lease(db_session, master_a, "host-a")
    
    # Manually expire Master A's lease
    lease = db_session.query(models.MasterLease).filter(models.MasterLease.id == 1).first()
    lease.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db_session.commit()
    
    # Master A is no longer leader
    assert is_leader(db_session, master_a) is False
    
    # Master B can now take over
    acquired_b = acquire_or_renew_lease(db_session, master_b, "host-b")
    assert acquired_b is True
    assert is_leader(db_session, master_b) is True
