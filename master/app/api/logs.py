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
    message: str = Query(default=None, description="Filter by message content (partial match)"),
    job_id: int = Query(default=None, description="Filter by job ID (matches logs with job_id in metadata)"),
    chunk_id: int = Query(default=None, description="Filter by chunk ID (matches logs with chunk_id in metadata)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(database.get_db),
):
    """
    Retrieve system logs with optional filtering by level, source, message, job_id, and chunk_id.
    job_id and chunk_id filtering searches the JSON metadata column.
    """
    query = db.query(models.Log)

    if level:
        query = query.filter(models.Log.level == level.upper())
    if source:
        query = query.filter(models.Log.source.ilike(f"%{source}%"))
    if message:
        query = query.filter(models.Log.message.ilike(f"%{message}%"))
    # job_id and chunk_id: filter via JSON cast (PostgreSQL-compatible)
    if job_id is not None:
        query = query.filter(
            models.Log.log_metadata.op("->>")(  "job_id") == str(job_id)
        )
    if chunk_id is not None:
        query = query.filter(
            models.Log.log_metadata.op("->>")(  "chunk_id") == str(chunk_id)
        )

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
