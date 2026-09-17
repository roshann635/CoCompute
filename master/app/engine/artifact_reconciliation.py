"""
CoCompute Hardening: Artifact Reconciliation Service

Detects and resolves discrepancies between filesystem artifacts and DB ResultArtifact records:
- Files without DB records (orphaned files) -> creates missing DB records
- DB records without files -> marks records as missing/corrupt
"""

import os
import logging
from ..db import models
from ..storage.file_store import RESULTS_DIR, compute_file_checksum

logger = logging.getLogger("cocompute.master.artifact_reconciliation")


def reconcile_artifacts(db) -> dict:
    """
    Executes artifact reconciliation between filesystem and database.
    """
    report = {
        "orphans_registered": 0,
        "missing_records_flagged": 0,
    }

    try:
        # 1. Scan filesystem for job directories
        if os.path.exists(RESULTS_DIR):
            for entry in os.listdir(RESULTS_DIR):
                job_dir = os.path.join(RESULTS_DIR, entry)
                if os.path.isdir(job_dir) and entry.isdigit():
                    job_id = int(entry)
                    result_path = os.path.join(job_dir, "result.json")
                    if os.path.exists(result_path):
                        # Check if DB has active record
                        existing = db.query(models.ResultArtifact).filter(
                            models.ResultArtifact.job_id == job_id,
                            models.ResultArtifact.storage_location == result_path,
                            models.ResultArtifact.lifecycle_state == "active"
                        ).first()

                        if not existing:
                            # Orphaned file without DB record -> register it
                            job = db.query(models.Job).filter(models.Job.id == job_id).first()
                            if job:
                                checksum = compute_file_checksum(result_path)
                                artifact = models.ResultArtifact(
                                    job_id=job.id,
                                    storage_location=result_path,
                                    size_bytes=os.path.getsize(result_path),
                                    checksum_sha256=checksum,
                                    lifecycle_state="active"
                                )
                                db.add(artifact)
                                report["orphans_registered"] += 1

        # 2. Scan DB records to verify files still exist on disk
        active_artifacts = db.query(models.ResultArtifact).filter(
            models.ResultArtifact.lifecycle_state == "active"
        ).all()

        for art in active_artifacts:
            if not os.path.exists(art.storage_location):
                art.lifecycle_state = "missing"
                report["missing_records_flagged"] += 1

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[ArtifactReconciliation] Error: {e}")

    return report
