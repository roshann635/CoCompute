"""System log retrieval API for the dashboard log viewer."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..db import database, models

router = APIRouter()


@router.get("/")
def get_logs(
    level: str = Query(default=None, description="Filter by log level (INFO, WARNING, ERROR, CRITICAL)"),
    source: str = Query(default=None, description="Filter by source module (partial match)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(database.get_db),
):
    """Retrieve system logs with optional filtering by level and source."""
    query = db.query(models.Log)

    if level:
        query = query.filter(models.Log.level == level.upper())
    if source:
        query = query.filter(models.Log.source.ilike(f"%{source}%"))

    total = query.count()
    logs = query.order_by(desc(models.Log.timestamp)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "level": log.level,
                "source": log.source,
                "message": log.message,
                "metadata": log.log_metadata,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in logs
        ],
    }
