"""
CoCompute MinIO Object Storage Service.

Provides object storage management for:
  - chunks: task chunk binary inputs
  - results: task chunk outputs & partial results
  - checkpoints: model training & fine-tuning checkpoints
  - artifacts: per-job persistent artifact bundles
  - models: final trained & fine-tuned model weights
"""

import os
import io
import json
import hashlib
import logging
from datetime import timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


class MinioService:
    def __init__(
        self,
        endpoint: str = MINIO_ENDPOINT,
        access_key: str = MINIO_ACCESS_KEY,
        secret_key: str = MINIO_SECRET_KEY,
        secure: bool = MINIO_SECURE,
    ):
        self.endpoint = endpoint
        self.client = None
        self.available = False
        
        try:
            from minio import Minio
            self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
            self._ensure_buckets(["chunks", "results", "checkpoints", "artifacts", "models"])
            self.available = True
            logger.info(f"MinIO client connected to {endpoint}")
        except Exception as e:
            logger.warning(f"MinIO unavailable at {endpoint} ({e}). Falling back to local storage adapter.")

    def _ensure_buckets(self, names: list[str]):
        if not self.client:
            return
        for name in names:
            try:
                if not self.client.bucket_exists(name):
                    self.client.make_bucket(name)
            except Exception as e:
                logger.debug(f"Bucket check/create error for {name}: {e}")

    def upload_chunk(self, job_id: str, chunk_id: str, data: bytes) -> str:
        """Returns MinIO path: minio://chunks/{job_id}/{chunk_id}.bin"""
        path = f"{job_id}/{chunk_id}.bin"
        if self.available and self.client:
            try:
                self.client.put_object("chunks", path, io.BytesIO(data), len(data))
                return f"minio://chunks/{path}"
            except Exception as e:
                logger.error(f"MinIO upload_chunk error: {e}")
        
        # Local fallback storage
        local_dir = os.path.join("storage", "chunks", job_id)
        os.makedirs(local_dir, exist_ok=True)
        local_file = os.path.join(local_dir, f"{chunk_id}.bin")
        with open(local_file, "wb") as f:
            f.write(data)
        return f"minio://chunks/{path}"

    def upload_result(self, job_id: str, attempt_id: str, data: bytes) -> Tuple[str, str]:
        """Returns (minio_path, sha256_checksum)"""
        path = f"{job_id}/{attempt_id}.bin"
        checksum = hashlib.sha256(data).hexdigest()
        
        if self.available and self.client:
            try:
                self.client.put_object("results", path, io.BytesIO(data), len(data))
                return f"minio://results/{path}", checksum
            except Exception as e:
                logger.error(f"MinIO upload_result error: {e}")

        # Local fallback storage
        local_dir = os.path.join("storage", "results", job_id)
        os.makedirs(local_dir, exist_ok=True)
        local_file = os.path.join(local_dir, f"{attempt_id}.bin")
        with open(local_file, "wb") as f:
            f.write(data)
        return f"minio://results/{path}", checksum

    def upload_checkpoint(self, job_id: str, step: int, data: bytes) -> str:
        """Returns minio://checkpoints/{job_id}/step_{step}.pt"""
        path = f"{job_id}/step_{step}.pt"
        if self.available and self.client:
            try:
                self.client.put_object("checkpoints", path, io.BytesIO(data), len(data))
                return f"minio://checkpoints/{path}"
            except Exception as e:
                logger.error(f"MinIO upload_checkpoint error: {e}")

        local_dir = os.path.join("storage", "checkpoints", job_id)
        os.makedirs(local_dir, exist_ok=True)
        local_file = os.path.join(local_dir, f"step_{step}.pt")
        with open(local_file, "wb") as f:
            f.write(data)
        return f"minio://checkpoints/{path}"

    def upload_artifact_bundle(self, job_id: str, bundle: dict) -> str:
        """Returns minio://artifacts/{job_id}/artifact_bundle.json"""
        data = json.dumps(bundle, default=str, indent=2).encode("utf-8")
        path = f"{job_id}/artifact_bundle.json"
        
        if self.available and self.client:
            try:
                self.client.put_object("artifacts", path, io.BytesIO(data), len(data))
                return f"minio://artifacts/{path}"
            except Exception as e:
                logger.error(f"MinIO upload_artifact_bundle error: {e}")

        local_dir = os.path.join("storage", "artifacts", job_id)
        os.makedirs(local_dir, exist_ok=True)
        local_file = os.path.join(local_dir, "artifact_bundle.json")
        with open(local_file, "wb") as f:
            f.write(data)
        return f"minio://artifacts/{path}"

    def get_download_url(self, minio_path: str, expires_hours: int = 1) -> str:
        """Generate presigned URL for download."""
        if not minio_path or not minio_path.startswith("minio://"):
            return minio_path
        
        clean_path = minio_path.replace("minio://", "")
        parts = clean_path.split("/", 1)
        if len(parts) != 2:
            return minio_path
        
        bucket, obj = parts[0], parts[1]
        
        if self.available and self.client:
            try:
                return self.client.presigned_get_object(bucket, obj, expires=timedelta(hours=expires_hours))
            except Exception as e:
                logger.error(f"Error generating presigned URL for {minio_path}: {e}")
        
        # Fallback local REST URL
        return f"/api/v1/files/download?path={clean_path}"


# Singleton instance
minio_service = MinioService()
