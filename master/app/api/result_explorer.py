"""
Universal Server-Side Data Explorer REST API — CoCompute 4.0.

Provides server-side pagination, searching, and filtering for huge result sets:
  - mode=preview: First 100 rows
  - mode=sample: Random / stratified sample
  - mode=full_query: Paginated table slice
"""

import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from master.app.db import models
from master.app.db.database import get_db

router = APIRouter(prefix="/api/v1/jobs", tags=["result-explorer"])


@router.get("/{job_id}/explorer")
def explore_job_results(
    job_id: int,
    mode: str = Query("full_query", description="preview, sample, or full_query"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns a server-side paginated, searchable slice of the job result.
    Prevents overwhelming the React frontend with multi-million-record payloads.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    raw_result = job.aggregated_result
    if raw_result is None:
        return {
            "job_id": job.id,
            "status": job.status,
            "semantic_type": job.result_semantic_type or "empty",
            "total_records": 0,
            "page": page,
            "limit": limit,
            "data": [],
            "quality": job.result_quality or {}
        }

    # Normalize to iterable rows
    rows: List[Any] = []
    columns: List[str] = []

    if isinstance(raw_result, list):
        rows = raw_result
        if rows and isinstance(rows[0], dict):
            columns = list(rows[0].keys())
        elif rows and isinstance(rows[0], list):
            columns = [f"Col_{i}" for i in range(len(rows[0]))]
        else:
            columns = ["Value"]
            rows = [{"Value": v} for v in rows]
    elif isinstance(raw_result, dict):
        if "data" in raw_result and isinstance(raw_result["data"], list):
            rows = raw_result["data"]
            if rows and isinstance(rows[0], dict):
                columns = list(rows[0].keys())
        else:
            rows = [raw_result]
            columns = list(raw_result.keys())

    total_records = len(rows)

    # Filter/Search
    if search:
        search_lower = search.lower()
        rows = [r for r in rows if search_lower in str(r).lower()]

    # Mode Handling
    if mode == "preview":
        sliced_data = rows[:100]
    elif mode == "sample":
        import random
        sample_k = min(len(rows), 100)
        sliced_data = random.sample(rows, sample_k) if rows else []
    else: # full_query pagination
        offset = (page - 1) * limit
        sliced_data = rows[offset:offset + limit]

    return {
        "job_id": job.id,
        "job_uid": job.job_uid,
        "status": job.status,
        "semantic_type": job.result_semantic_type or "table",
        "total_records": total_records,
        "filtered_count": len(rows),
        "page": page,
        "limit": limit,
        "columns": columns,
        "data": sliced_data,
        "quality": job.result_quality or {"quality_score": 100.0}
    }
