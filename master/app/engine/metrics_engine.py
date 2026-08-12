"""
Metrics Engine — Redis-backed real-time metrics caching and time-series storage.

Provides:
  - Sub-millisecond cluster snapshot reads via Redis cache
  - Time-bucketed per-minute metric aggregates using Redis sorted sets
  - Reduces database load for dashboard polling

Redis keys used:
  cocompute:cluster:snapshot       — Latest cluster snapshot (JSON string, TTL 10s)
  cocompute:metrics:timeseries     — Sorted set of minute-bucketed metrics (score = timestamp)
  cocompute:worker:{uid}:latest    — Latest metrics per worker (hash)
"""
import os
import json
import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TIMESERIES_MAX_ENTRIES = 1440  # Keep 24 hours of per-minute entries
SNAPSHOT_TTL_SECONDS = 10

# Redis client singleton
_redis_client = None


def get_redis_client():
    """Get or create the Redis client singleton."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    try:
        import redis
        _redis_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=True,
        )
        # Test connection
        _redis_client.ping()
        logger.info(f"Metrics Engine: Connected to Redis at {REDIS_URL}")
        return _redis_client
    except Exception as e:
        logger.warning(f"Metrics Engine: Redis unavailable ({e}). Operating in DB-only mode.")
        _redis_client = None
        return None


def cache_cluster_snapshot(snapshot: dict) -> bool:
    """
    Cache the latest cluster snapshot in Redis for fast dashboard reads.
    Called by the dashboard broadcast loop every ~3 seconds.
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        client.setex(
            "cocompute:cluster:snapshot",
            SNAPSHOT_TTL_SECONDS,
            json.dumps(snapshot, default=str),
        )
        return True
    except Exception as e:
        logger.debug(f"Redis cache write error: {e}")
        return False


def get_cached_snapshot() -> dict | None:
    """
    Read the latest cluster snapshot from Redis cache.
    Returns None if cache miss or Redis unavailable.
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        data = client.get("cocompute:cluster:snapshot")
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.debug(f"Redis cache read error: {e}")
        return None


def record_metric_point(cluster_data: dict) -> bool:
    """
    Record a time-bucketed metric point (per-minute aggregate).
    Stores in a Redis sorted set for time-series queries.
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        now = datetime.now(timezone.utc)
        # Bucket to the minute
        minute_key = now.strftime("%Y-%m-%dT%H:%M:00Z")
        timestamp_score = now.timestamp()

        point = {
            "timestamp": minute_key,
            "online_nodes": cluster_data.get("online_nodes", 0),
            "active_cores": cluster_data.get("active_cores", 0),
            "avg_cpu": cluster_data.get("avg_cpu_usage", 0),
            "avg_ram": round(
                sum(cluster_data.get("aggregated_ram", 0) for _ in [1]) / max(1, 1), 1
            ) if isinstance(cluster_data.get("aggregated_ram"), (int, float)) else 0,
            "efficiency": cluster_data.get("efficiency", 0),
            "tasks_running": cluster_data.get("tasks", {}).get("running", 0)
                if isinstance(cluster_data.get("tasks"), dict)
                else 0,
            "tasks_completed": cluster_data.get("tasks", {}).get("completed", 0)
                if isinstance(cluster_data.get("tasks"), dict)
                else 0,
            "tasks_pending": cluster_data.get("tasks", {}).get("pending", 0)
                if isinstance(cluster_data.get("tasks"), dict)
                else 0,
        }

        # Add to sorted set (score = unix timestamp for ordering)
        client.zadd(
            "cocompute:metrics:timeseries",
            {json.dumps(point): timestamp_score},
        )

        # Trim old entries (keep last 24 hours)
        cutoff = timestamp_score - (86400)  # 24 hours ago
        client.zremrangebyscore("cocompute:metrics:timeseries", "-inf", cutoff)

        return True
    except Exception as e:
        logger.debug(f"Redis timeseries write error: {e}")
        return False


def update_worker_metrics(worker_uid: str, metrics: dict) -> bool:
    """Cache latest metrics for a specific worker."""
    client = get_redis_client()
    if not client:
        return False

    try:
        key = f"cocompute:worker:{worker_uid}:latest"
        client.hset(key, mapping={
            "cpu_usage": str(metrics.get("cpu_usage", 0)),
            "ram_usage": str(metrics.get("ram_usage", 0)),
            "disk_usage": str(metrics.get("disk_usage", 0)),
            "running_tasks": str(metrics.get("running_tasks", 0)),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        client.expire(key, 30)  # Expire if no heartbeat for 30s
        return True
    except Exception as e:
        logger.debug(f"Redis worker cache error: {e}")
        return False


def get_timeseries(minutes: int = 60) -> list[dict]:
    """
    Retrieve time-series metric points from Redis.
    Returns up to `minutes` worth of per-minute data points.
    """
    client = get_redis_client()
    if not client:
        return []

    try:
        now = time.time()
        cutoff = now - (minutes * 60)

        # Get entries from sorted set
        entries = client.zrangebyscore(
            "cocompute:metrics:timeseries",
            cutoff, "+inf",
            withscores=False,
        )

        result = []
        for entry in entries:
            try:
                point = json.loads(entry)
                result.append(point)
            except (json.JSONDecodeError, TypeError):
                continue

        return result
    except Exception as e:
        logger.debug(f"Redis timeseries read error: {e}")
        return []


def get_redis_health() -> dict:
    """Get Redis connection health status."""
    client = get_redis_client()
    if not client:
        return {"status": "disconnected", "message": "Redis client not available"}

    try:
        info = client.info("server")
        memory = client.info("memory")
        return {
            "status": "connected",
            "redis_version": info.get("redis_version", "unknown"),
            "used_memory_human": memory.get("used_memory_human", "unknown"),
            "connected_clients": client.info("clients").get("connected_clients", 0),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
