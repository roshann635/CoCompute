"""
CoCompute Redis Queue & Rescheduling Pub/Sub Service.

Handles:
  - Priority-based job intake queues (jobs:high, jobs:normal)
  - Real-time fault recovery and rescheduling events on channel 'cocompute:reschedule'
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class QueueService:
    def __init__(self, redis_url: str = REDIS_URL):
        self.redis_url = redis_url
        self.r = None
        self.pubsub = None
        self.available = False
        self._local_subscribers = []
        self._local_queues = {"jobs:high": [], "jobs:normal": []}

        try:
            import redis
            self.r = redis.Redis.from_url(redis_url, decode_responses=True)
            self.r.ping()
            self.pubsub = self.r.pubsub()
            self.available = True
            logger.info(f"Connected to Redis Queue at {redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable at {redis_url} ({e}). Using in-memory fallback queue.")

    # ── Job queue ───────────────────────────────────────────────────────────

    def enqueue_job(self, job_id: str, priority: str = "NORMAL", metadata: Optional[Dict[str, Any]] = None) -> None:
        queue = "jobs:high" if priority.upper() == "HIGH" else "jobs:normal"
        payload = {
            "job_id": str(job_id),
            "priority": priority.upper(),
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        data_str = json.dumps(payload)
        
        if self.available and self.r:
            try:
                self.r.rpush(queue, data_str)
                logger.info(f"Enqueued job {job_id} into {queue}")
                return
            except Exception as e:
                logger.error(f"Redis enqueue error: {e}")

        # Local in-memory queue fallback
        self._local_queues[queue].append(payload)
        logger.info(f"[In-Memory] Enqueued job {job_id} into {queue}")

    def dequeue_job(self, timeout: int = 5) -> Optional[dict]:
        if self.available and self.r:
            try:
                for queue in ["jobs:high", "jobs:normal"]:
                    result = self.r.blpop(queue, timeout=timeout)
                    if result:
                        _, data = result
                        return json.loads(data)
            except Exception as e:
                logger.error(f"Redis dequeue error: {e}")

        # Local fallback
        for queue in ["jobs:high", "jobs:normal"]:
            if self._local_queues[queue]:
                return self._local_queues[queue].pop(0)
        return None

    # ── Rescheduling events ─────────────────────────────────────────────────

    def publish_reschedule(self, job_id: str, chunk_ids: list[str], reason: str) -> None:
        event = {
            "event": "RESCHEDULE",
            "job_id": str(job_id),
            "chunk_ids": [str(c) for c in chunk_ids],
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        event_str = json.dumps(event)

        if self.available and self.r:
            try:
                self.r.publish("cocompute:reschedule", event_str)
                logger.info(f"Published RESCHEDULE event for job {job_id} ({len(chunk_ids)} chunks): {reason}")
                return
            except Exception as e:
                logger.error(f"Redis publish_reschedule error: {e}")

        # Local fallback dispatch
        for callback in self._local_subscribers:
            try:
                callback({"data": event_str, "type": "message", "channel": "cocompute:reschedule"})
            except Exception as e:
                logger.error(f"Error in local reschedule subscriber: {e}")

    def subscribe_reschedule(self, callback: Callable) -> None:
        if self.available and self.pubsub:
            try:
                self.pubsub.subscribe(**{"cocompute:reschedule": callback})
                self.pubsub.run_in_thread(sleep_time=0.01, daemon=True)
                logger.info("Subscribed to Redis channel 'cocompute:reschedule'")
                return
            except Exception as e:
                logger.error(f"Redis subscribe_reschedule error: {e}")

        self._local_subscribers.append(callback)
        logger.info("Registered local callback for reschedule events")


# Singleton instance
queue_service = QueueService()
