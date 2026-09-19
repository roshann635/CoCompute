"""
CoCompute Hardening: Master Leadership & Split-Brain Prevention

Enforces single-active Master via database-backed lease.
Only the Master holding an active lease can schedule or mutate cluster state.
"""

from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy import update, or_
from ..db.models import MasterLease

logger = logging.getLogger("cocompute.master.leadership")

LEASE_DURATION_SEC = 30
HEARTBEAT_INTERVAL_SEC = 10


def ensure_lease_row(db):
    """Ensure the master_lease singleton row (id=1) exists."""
    lease = db.query(MasterLease).filter(MasterLease.id == 1).first()
    if not lease:
        try:
            lease = MasterLease(
                id=1,
                incarnation_id="uninitialized",
                hostname="none",
                lease_acquired_at=datetime.fromtimestamp(0, tz=timezone.utc),
                lease_expires_at=datetime.fromtimestamp(0, tz=timezone.utc),
                heartbeat_at=datetime.fromtimestamp(0, tz=timezone.utc),
            )
            db.add(lease)
            db.commit()
        except Exception:
            db.rollback()


def acquire_or_renew_lease(db, incarnation_id: str, hostname: str = "master-host", force: bool = False) -> bool:
    """
    Attempts to acquire or renew the master leadership lease via atomic check.
    Returns True if this incarnation is the active leader.
    """
    ensure_lease_row(db)
    now = datetime.now(timezone.utc)
    new_expires = now + timedelta(seconds=LEASE_DURATION_SEC)
    
    try:
        lease = db.query(MasterLease).filter(MasterLease.id == 1).first()
        if not lease:
            return False
            
        exp = lease.lease_expires_at
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
            
        can_acquire = (
            force or
            lease.incarnation_id == incarnation_id or
            exp is None or
            exp < now
        )
        if not can_acquire:
            return False
            
        lease.incarnation_id = incarnation_id
        lease.hostname = hostname
        lease.lease_acquired_at = now
        lease.lease_expires_at = new_expires
        lease.heartbeat_at = now
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"[Leadership] Error during lease acquisition: {e}")
        return False


def is_leader(db, incarnation_id: str) -> bool:
    """Check if this incarnation currently holds the valid, unexpired lease."""
    if not incarnation_id:
        return False
    now = datetime.now(timezone.utc)
    lease = db.query(MasterLease).filter(MasterLease.id == 1).first()
    if not lease:
        return False
    
    if lease.incarnation_id == incarnation_id:
        if lease.lease_expires_at:
            exp = lease.lease_expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp >= now:
                return True
    return False


def release_lease(db, incarnation_id: str):
    """Voluntarily release leadership lease on graceful shutdown."""
    now = datetime.now(timezone.utc)
    try:
        db.execute(
            update(MasterLease).where(
                MasterLease.id == 1,
                MasterLease.incarnation_id == incarnation_id
            ).values(
                lease_expires_at=now
            )
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[Leadership] Could not release lease: {e}")
