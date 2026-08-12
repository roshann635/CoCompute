import pytest
import os
import pickle
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from master.app.db import models
from master.app.engine.scheduler import (
    resource_aware_select,
    filter_available_workers,
    get_active_algorithm,
    set_active_algorithm
)
from master.app.engine.round_robin import round_robin_select
import master.app.engine.ai_scheduler
from master.app.engine.ai_scheduler import train_model, predict_best_worker

class MockWorker:
    def __init__(self, id, worker_uid, cores, ram, util, usage, status, reliability):
        self.id = id
        self.worker_uid = worker_uid
        self.cpu_cores = cores
        self.ram_total = ram
        self.cpu_utilization = util
        self.ram_usage = usage
        self.status = status
        self.reliability_score = reliability
        self.running_tasks = 0


def test_resource_aware_select():
    # Setup mock workers
    w1 = MockWorker(1, "W1", 8, 16.0, 10.0, 20.0, "online", 0.9)
    w2 = MockWorker(2, "W2", 2, 4.0, 80.0, 75.0, "online", 0.5)
    
    workers = [w1, w2]
    
    # Mock DB query
    db_mock = MagicMock()
    # Mock active tasks count query to return 0
    db_mock.query().filter().count.return_value = 0
    
    chunk = MagicMock()
    
    best_worker, score = resource_aware_select(workers, chunk, db_mock)
    
    # Worker 1 has more cores, RAM, reliability, and lower utilization, so it must be selected
    assert best_worker is not None
    assert best_worker.worker_uid == "W1"
    assert score > 0


def test_filter_available_workers():
    # Setup mock workers (W2 is overloaded with 90% CPU)
    w1 = MockWorker(1, "W1", 4, 8.0, 20.0, 30.0, "online", 0.8)
    w2 = MockWorker(2, "W2", 4, 8.0, 90.0, 30.0, "online", 0.8)
    
    db_mock = MagicMock()
    
    available, skipped = filter_available_workers([w1, w2], db_mock)
    
    assert len(available) == 1
    assert available[0].worker_uid == "W1"
    assert len(skipped) == 1
    assert skipped[0].worker_uid == "W2"


def test_round_robin_select():
    w1 = MockWorker(1, "W1", 4, 8.0, 20.0, 30.0, "online", 0.8)
    w2 = MockWorker(2, "W2", 4, 8.0, 20.0, 30.0, "online", 0.8)
    workers = [w1, w2]
    chunk = MagicMock()
    db_mock = MagicMock()
    
    # Reset rr index if necessary, or just verify sequential nature
    first = round_robin_select(workers, chunk, db_mock)
    second = round_robin_select(workers, chunk, db_mock)
    third = round_robin_select(workers, chunk, db_mock)
    
    assert first in workers
    assert second in workers
    assert third in workers
    assert first != second
    assert first == third


def test_active_algorithm_getter_setter():
    original = get_active_algorithm()
    try:
        set_active_algorithm("round_robin")
        assert get_active_algorithm() == "round_robin"
        
        set_active_algorithm("ai_predictive")
        assert get_active_algorithm() == "ai_predictive"
        
        with pytest.raises(ValueError):
            set_active_algorithm("invalid_algorithm")
    finally:
        set_active_algorithm(original)


def test_ai_scheduler_fallback():
    # Verify that if the model file is missing, it falls back to highest capacity worker
    w1 = MockWorker(1, "W1", 2, 4.0, 10.0, 10.0, "online", 0.9)
    w2 = MockWorker(2, "W2", 8, 16.0, 10.0, 10.0, "online", 0.9)
    
    # Temporarily force model path to non-existent file
    original_model_path = master.app.engine.ai_scheduler.MODEL_PATH
    master.app.engine.ai_scheduler.MODEL_PATH = "non_existent_model_file.pkl"
    
    try:
        if os.path.exists(master.app.engine.ai_scheduler.MODEL_PATH):
            os.remove(master.app.engine.ai_scheduler.MODEL_PATH)
            
        best = predict_best_worker([w1, w2])
        assert best is not None
        assert best.worker_uid == "W2"  # W2 has higher capacity (8 cores, 16GB)
    finally:
        master.app.engine.ai_scheduler.MODEL_PATH = original_model_path


def test_ai_scheduler_prediction():
    # Setup test model path
    original_model_path = master.app.engine.ai_scheduler.MODEL_PATH
    test_model_path = "tests/test_model.pkl"
    master.app.engine.ai_scheduler.MODEL_PATH = test_model_path
    
    try:
        # Create a dummy trained model bundle
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        
        X = np.array([[2, 4.0, 10.0, 10.0, 0.9, 0],
                      [8, 16.0, 10.0, 10.0, 0.9, 0]])
        y = np.array([50.0, 10.0])  # W2 is faster (10 seconds vs 50 seconds)
        
        rf = RandomForestRegressor(n_estimators=5, random_state=42)
        rf.fit(X, y)
        
        bundle = {
            "model": rf,
            "features": ["cpu_cores", "ram_total", "cpu_utilization", "ram_usage", "reliability_score", "running_tasks"]
        }
        
        with open(test_model_path, "wb") as f:
            pickle.dump(bundle, f)
            
        w1 = MockWorker(1, "W1", 2, 4.0, 10.0, 10.0, "online", 0.9)
        w2 = MockWorker(2, "W2", 8, 16.0, 10.0, 10.0, "online", 0.9)
        
        best = predict_best_worker([w1, w2])
        assert best is not None
        assert best.worker_uid == "W2"
    finally:
        if os.path.exists(test_model_path):
            os.remove(test_model_path)
        master.app.engine.ai_scheduler.MODEL_PATH = original_model_path


# Mock Session wrapper to prevent pytest closing db connection during execution
class SafeSession:
    def __init__(self, session):
        self.session = session
    def __getattr__(self, name):
        return getattr(self.session, name)
    def close(self):
        pass


def test_ai_scheduler_training(db_session):
    original_model_path = master.app.engine.ai_scheduler.MODEL_PATH
    test_model_path = "tests/test_model_train.pkl"
    master.app.engine.ai_scheduler.MODEL_PATH = test_model_path
    
    # Patch SessionLocal inside ai_scheduler module
    original_session_local = master.app.engine.ai_scheduler.SessionLocal
    master.app.engine.ai_scheduler.SessionLocal = lambda: SafeSession(db_session)
    
    try:
        # Scenario 1: Not enough samples (needs at least 10)
        success = train_model()
        assert success is False
        assert not os.path.exists(test_model_path)
        
        # Scenario 2: Create 10 completed chunks
        # Create user
        user = models.User(username="testuser", email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        
        # Create worker
        worker = models.Worker(
            worker_uid="W1",
            hostname="node1",
            status="online",
            cpu_cores=4,
            ram_total=8.0,
            reliability_score=0.9
        )
        db_session.add(worker)
        db_session.commit()
        
        # Create job and task
        job = models.Job(user_id=user.id, name="job", job_type="generic_python", status="completed")
        db_session.add(job)
        db_session.commit()
        task = models.Task(job_id=job.id, type="generic_python", status="completed")
        db_session.add(task)
        db_session.commit()
        
        now = datetime.now(timezone.utc)
        for i in range(12):
            chunk = models.TaskChunk(
                task_id=task.id,
                worker_id=worker.id,
                chunk_index=i,
                status="completed",
                start_time=now - timedelta(seconds=20),
                end_time=now
            )
            db_session.add(chunk)
        db_session.commit()
        
        # Train model with sufficient samples
        success = train_model()
        assert success is True
        assert os.path.exists(test_model_path)
        
        # Check that we can load the pickle file and it is valid
        with open(test_model_path, "rb") as f:
            bundle = pickle.load(f)
            assert "model" in bundle
            assert bundle["features"] == ["cpu_cores", "ram_total", "cpu_utilization", "ram_usage", "reliability_score", "running_tasks"]
    finally:
        if os.path.exists(test_model_path):
            os.remove(test_model_path)
        master.app.engine.ai_scheduler.SessionLocal = original_session_local
        master.app.engine.ai_scheduler.MODEL_PATH = original_model_path
