"""FR-15: Active cluster alerts API — worker disconnections, job failures, SLA breaches."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import database
from ..engine.analytics import get_cluster_alerts

router = APIRouter()


@router.get("/")
def get_alerts(db: Session = Depends(database.get_db)):
    """
    FR-15: Return all active cluster alerts including:
    - Worker disconnections (offline in last 10 min)
    - Failed jobs (last hour)
    - SLA-breaching task chunks (running > 5 minutes)
    - High-utilization workers (skipped by FR-14 scheduler)
    """
    return {"alerts": get_cluster_alerts(db), "count": len(get_cluster_alerts(db))}


@router.get("/count")
def get_alert_count(db: Session = Depends(database.get_db)):
    """Get just the count of active alerts (lightweight for polling)."""
    alerts = get_cluster_alerts(db)
    errors = sum(1 for a in alerts if a.get("severity") == "error")
    warnings = sum(1 for a in alerts if a.get("severity") == "warning")
    return {"total": len(alerts), "errors": errors, "warnings": warnings}
