"""
File Storage API — download and export job results & full artifact bundles.

Endpoints:
  GET /api/v1/files/jobs                      — List all stored result files
  GET /api/v1/files/jobs/{job_id}/download     — Download result as JSON
  GET /api/v1/files/jobs/{job_id}/export/csv   — Export result as CSV
  GET /api/v1/files/jobs/{job_id}/export/txt   — Export result as Plain Text
  GET /api/v1/files/jobs/{job_id}/export/zip   — Download full artifact bundle (.zip)
  GET /api/v1/files/jobs/{job_id}/artifacts    — Browse artifact bundle & MinIO URLs
"""

import io
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..db import database, models
from ..storage.file_store import (
    get_result_file_path,
    list_stored_results,
    save_result_file,
    generate_csv_from_result,
    generate_artifact_bundle_zip,
)
from ..services.minio_service import minio_service

router = APIRouter()


@router.get("/jobs")
def list_result_files():
    """List all stored result files with metadata."""
    return {"files": list_stored_results()}


@router.get("/jobs/{job_id}/download")
def download_result_json(job_id: int, db: Session = Depends(database.get_db)):
    """Download the aggregated result for a job as a JSON file."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = get_result_file_path(job_id, "json")
    if not file_path and job.aggregated_result:
        file_path = save_result_file(
            job_id=job.id,
            job_name=job.name or f"job_{job_id}",
            job_type=job.job_type,
            aggregated_result=job.aggregated_result,
            metadata={"job_uid": job.job_uid, "status": job.status}
        )

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Result file not found")

    safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
    return FileResponse(
        path=file_path,
        filename=f"{safe_name}_result.json",
        media_type="application/json",
    )


@router.get("/jobs/{job_id}/export/csv")
def export_result_csv(job_id: int, db: Session = Depends(database.get_db)):
    """Export the aggregated result as a CSV file."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = get_result_file_path(job_id, "csv")
    if file_path and os.path.exists(file_path):
        safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
        return FileResponse(
            path=file_path,
            filename=f"{safe_name}_result.csv",
            media_type="text/csv",
        )

    if not job.aggregated_result:
        raise HTTPException(status_code=404, detail="No result available for CSV export")

    csv_content = generate_csv_from_result(job.job_type, job.aggregated_result)
    if not csv_content:
        raise HTTPException(status_code=404, detail="CSV export not available for this job type")

    safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_result.csv"'},
    )


@router.get("/jobs/{job_id}/export/txt")
def export_result_txt(job_id: int, db: Session = Depends(database.get_db)):
    """Export the aggregated result as plain text."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = get_result_file_path(job_id, "txt")
    if not file_path or not os.path.exists(file_path):
        if job.aggregated_result:
            save_result_file(job_id, job.name or f"job_{job_id}", job.job_type, job.aggregated_result)
            file_path = get_result_file_path(job_id, "txt")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="TXT export not found")

    safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
    return FileResponse(
        path=file_path,
        filename=f"{safe_name}_result.txt",
        media_type="text/plain",
    )


@router.get("/jobs/{job_id}/export/zip")
def download_artifact_bundle_zip(job_id: int, db: Session = Depends(database.get_db)):
    """Download the complete persistent artifact bundle as a ZIP archive."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    zip_path = generate_artifact_bundle_zip(job_id, job, db)
    safe_name = (job.name or f"job_{job_id}").replace(" ", "_").replace("/", "_")
    return FileResponse(
        path=zip_path,
        filename=f"{safe_name}_artifact_bundle.zip",
        media_type="application/zip"
    )


@router.get("/jobs/{job_id}/artifacts")
def get_job_artifacts(job_id: int, db: Session = Depends(database.get_db)):
    """Browse artifact bundle metadata and MinIO presigned download URLs."""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    minio_bundle_url = minio_service.get_download_url(f"minio://artifacts/{job.job_uid or job.id}/artifact_bundle.json")
    minio_checkpoint_url = minio_service.get_download_url(job.checkpoint_location) if job.checkpoint_location else None

    return {
        "job_id": job.id,
        "job_uid": job.job_uid,
        "job_type": job.job_type,
        "result_location": job.result_location,
        "checkpoint_location": job.checkpoint_location,
        "minio_bundle_url": minio_bundle_url,
        "minio_checkpoint_url": minio_checkpoint_url,
        "local_exports": {
            "json": f"/api/v1/files/jobs/{job.id}/download",
            "csv": f"/api/v1/files/jobs/{job.id}/export/csv",
            "txt": f"/api/v1/files/jobs/{job.id}/export/txt",
            "zip": f"/api/v1/files/jobs/{job.id}/export/zip"
        }
    }
