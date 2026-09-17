import os
os.environ["DATABASE_URL"] = "sqlite:///./test_cocompute.db"
import pytest
import sys

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from master.app.db.database import Base

@pytest.fixture(name="db_session", scope="function")
def fixture_db_session():
    # Setup SQLite in-memory DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
