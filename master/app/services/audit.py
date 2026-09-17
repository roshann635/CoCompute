"""
CoCompute Hardening: Structured Audit Logging Service

Records high-integrity security, resource, scheduling, and job lifecycle events.
"""

from typing import Optional, Dict, Any
import logging
from ..db import models

logger = logging.getLogger("cocompute.master.audit")


def log_audit_event(
    db,
    actor: str,
    action: str,
    role: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    outcome: str = "success",
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Optional[models.AuditLog]:
    """
    Creates an immutable audit log entry in the database.
    """
    try:
        audit_entry = models.AuditLog(
            actor=actor or "system",
            role=role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            outcome=outcome,
            details=details,
            ip_address=ip_address,
            session_id=session_id,
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        return audit_entry
    except Exception as e:
        db.rollback()
        logger.error(f"[Audit] Failed to record audit log entry ({action}): {e}")
        return None
