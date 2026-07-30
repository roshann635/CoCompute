"""
Local Task History — SQLite-based persistence for worker task execution records.

Ensures the worker maintains its own history of executed tasks,
independent of the master's centralized database (SRS FR-11).
"""
import sqlite3
import json
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("WORKER_HISTORY_DB", "task_history.db")


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection, creating the schema if needed."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            result_summary TEXT,
            error_message TEXT,
            start_time TEXT,
            end_time TEXT,
            execution_time_seconds REAL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_history_chunk_id
        ON task_history(chunk_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_task_history_status
        ON task_history(status)
    """)
    conn.commit()
    return conn


def save_task_record(
    chunk_id: int,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    execution_time: float | None = None,
) -> None:
    """Save a completed task record to local history."""
    try:
        conn = _get_connection()
        # Truncate large results to keep the DB manageable
        result_summary = None
        if result:
            summary = json.dumps(result)
            result_summary = summary[:2000] if len(summary) > 2000 else summary

        conn.execute(
            """INSERT INTO task_history
               (chunk_id, status, result_summary, error_message,
                start_time, end_time, execution_time_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (chunk_id, status, result_summary, error,
             start_time, end_time, execution_time),
        )
        conn.commit()
        conn.close()
        logger.debug(f"Saved task history for chunk {chunk_id} (status={status})")
    except Exception as e:
        logger.error(f"Failed to save task history: {e}")


def get_task_history(limit: int = 100) -> list[dict]:
    """Retrieve recent task history records."""
    try:
        conn = _get_connection()
        cursor = conn.execute(
            "SELECT * FROM task_history ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Failed to retrieve task history: {e}")
        return []


def get_task_stats() -> dict:
    """Get aggregate statistics from local task history."""
    try:
        conn = _get_connection()
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total_tasks,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as failed,
                AVG(execution_time_seconds) as avg_execution_time,
                MIN(execution_time_seconds) as min_execution_time,
                MAX(execution_time_seconds) as max_execution_time
            FROM task_history
        """)
        row = dict(cursor.fetchone())
        conn.close()
        return {
            "total_tasks": row["total_tasks"] or 0,
            "completed": row["completed"] or 0,
            "failed": row["failed"] or 0,
            "avg_execution_time": round(row["avg_execution_time"], 3) if row["avg_execution_time"] else 0,
            "min_execution_time": round(row["min_execution_time"], 3) if row["min_execution_time"] else 0,
            "max_execution_time": round(row["max_execution_time"], 3) if row["max_execution_time"] else 0,
        }
    except Exception as e:
        logger.error(f"Failed to get task stats: {e}")
        return {"total_tasks": 0, "completed": 0, "failed": 0, "avg_execution_time": 0}
