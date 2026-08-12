"""
File Storage API — download and export job results.

Endpoints:
  GET /api/v1/files/jobs                      — List all stored result files
  GET /api/v1/files/jobs/{job_id}/download     — Download result as JSON
  GET /api/v1/files/jobs/{job_id}/export/csv   — Export result as CSV
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import io

from ..db import database, models
from ..storage.file_store import (
    get_result_file_path,
    list_stored_results,
    save_result_file,
    generate_csv_from_result,
)

router = APIRouter()


@router.get("/jobs")
def list_result_files():
    """List all stored result files with metadata (size, date, job info)."""
    return {"files": list_stored_results()}


@router.get("/jobs/{job_id}/download")
def download_result_json(job_id: int, db: Session = Depends(database.get_db)):
    """
    Download the aggregated result for a job as a JSON file.
    If the file doesn't exist on disk yet, generates it on the fly from the DB.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.aggregated_result:
        raise HTTPException(status_code=404, detail="No aggregated result available for this job")

    # Try to serve from disk first
    file_path = get_result_file_path(job_id, "json")
    if not file_path:
        # Generate on the fly and save
        file_path = save_result_file(
            job_id=job.id,
            job_name=job.name,
            job_type=job.job_type,
            aggregated_result=job.aggregated_result,
            metadata={
                "status": job.status,
                "total_tasks": job.total_tasks,
                "completed_tasks": job.completed_tasks,
                "failed_tasks": job.failed_tasks,
            },
        )

    safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
    return FileResponse(
        path=file_path,
        filename=f"{safe_name}_result.json",
        media_type="application/json",
    )


@router.get("/jobs/{job_id}/export/csv")
def export_result_csv(job_id: int, db: Session = Depends(database.get_db)):
    """
    Export the aggregated result as a CSV file.
    Generates CSV on the fly from the aggregated result based on job type.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.aggregated_result:
        raise HTTPException(status_code=404, detail="No aggregated result available for this job")

    # Try disk first
    file_path = get_result_file_path(job_id, "csv")
    if file_path:
        safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
        return FileResponse(
            path=file_path,
            filename=f"{safe_name}_result.csv",
            media_type="text/csv",
        )

    # Generate on the fly
    csv_content = generate_csv_from_result(job.job_type, job.aggregated_result)
    if not csv_content:
        raise HTTPException(status_code=404, detail="CSV export not available for this job type or no data")

    safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_result.csv"'},
    )
