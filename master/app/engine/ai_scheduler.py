"""
AI-Powered Predictive Scheduler.

Uses a Random Forest Regressor to predict task completion time per worker.
Features used for prediction:
  - CPU cores
  - RAM total
  - Current CPU utilization
  - Current RAM usage
  - Reliability score
  - Running tasks count

The model is trained periodically on completed task data.
This module is called by the unified scheduler (scheduler.py) when algorithm=ai_predictive.
"""
import logging
import os
import pickle
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from ..db.database import SessionLocal
from ..db import models

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("AI_MODEL_PATH", "model.pkl")
MIN_TRAINING_SAMPLES = 10
_last_train_time = None


def train_model() -> bool:
    """
    Train an RF model on completed task chunk data.
    Features: cpu_cores, ram_total, cpu_utilization, ram_usage, reliability_score, running_tasks
    Target: execution duration in seconds
    """
    global _last_train_time
    db = SessionLocal()
    try:
        chunks = db.query(models.TaskChunk).filter(models.TaskChunk.status == "completed").all()
        if len(chunks) < MIN_TRAINING_SAMPLES:
            logger.debug(f"Not enough data to train ({len(chunks)}/{MIN_TRAINING_SAMPLES}).")
            return False

        data = []
        for chunk in chunks:
            if not chunk.start_time or not chunk.end_time:
                continue
            worker = db.query(models.Worker).filter(models.Worker.id == chunk.worker_id).first()
            if not worker:
                continue

            duration = (chunk.end_time - chunk.start_time).total_seconds()
            if duration <= 0:
                continue

            data.append({
                "cpu_cores": worker.cpu_cores or 1,
                "ram_total": worker.ram_total or 1.0,
                "cpu_utilization": worker.cpu_utilization or 0.0,
                "ram_usage": worker.ram_usage or 0.0,
                "reliability_score": worker.reliability_score or 0.5,
                "running_tasks": worker.running_tasks or 0,
                "duration": duration
            })

        if len(data) < MIN_TRAINING_SAMPLES:
            return False

        df = pd.DataFrame(data)
        feature_cols = ["cpu_cores", "ram_total", "cpu_utilization", "ram_usage", "reliability_score", "running_tasks"]
        X = df[feature_cols]
        y = df["duration"]

        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X, y)

        with open(MODEL_PATH, "wb") as f:
            pickle.dump({"model": model, "features": feature_cols}, f)

        _last_train_time = datetime.now(timezone.utc)
        logger.info(f"AI Scheduler model trained on {len(data)} samples. Features: {feature_cols}")
        return True

    except Exception as e:
        logger.error(f"Error training AI model: {e}")
        return False
    finally:
        db.close()


def predict_best_worker(workers: list[models.Worker]) -> models.Worker | None:
    """
    Predict which worker will complete a task fastest using the trained model.
    Falls back to a resource-aware heuristic if no model is available.
    """
    if not workers:
        return None

    if not os.path.exists(MODEL_PATH):
        # Fallback: highest capacity worker
        return max(workers, key=lambda w: (w.cpu_cores * 10) + (w.ram_total * 2))

    try:
        with open(MODEL_PATH, "rb") as f:
            bundle = pickle.load(f)

        model = bundle["model"]
        feature_cols = bundle["features"]

        best_worker = None
        min_duration = float("inf")

        for worker in workers:
            features = pd.DataFrame([{
                "cpu_cores": worker.cpu_cores or 1,
                "ram_total": worker.ram_total or 1.0,
                "cpu_utilization": worker.cpu_utilization or 0.0,
                "ram_usage": worker.ram_usage or 0.0,
                "reliability_score": worker.reliability_score or 0.5,
                "running_tasks": worker.running_tasks or 0,
            }], columns=feature_cols)

            predicted = model.predict(features)[0]

            if predicted < min_duration:
                min_duration = predicted
                best_worker = worker

        return best_worker

    except Exception as e:
        logger.error(f"AI prediction error: {e}")
        return max(workers, key=lambda w: (w.cpu_cores * 10) + (w.ram_total * 2))


async def periodic_training_loop():
    """
    Background loop that periodically retrains the AI model.
    Runs every 120 seconds.
    """
    import asyncio
    logger.info("Starting AI Model Training Loop...")

    while True:
        try:
            train_model()
        except Exception as e:
            logger.error(f"Training loop error: {e}")
        await asyncio.sleep(120)
