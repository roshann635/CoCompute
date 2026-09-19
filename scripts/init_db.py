"""
Database initialization and cleanup utility for CoCompute.

Usage:
  python scripts/init_db.py [--clean] [--seed-admin] [--db-url DB_URL]

Options:
  --clean        Remove stale/temporary SQLite files and storage results.
  --seed-admin   Create a default admin account if no user exists.
  --db-url       Override database URL (defaults to DATABASE_URL or sqlite:///d:/CoCompute/cocompute.db)
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


def clean_stale_data():
    """Remove old/temporary database files and result caches."""
    print("[CLEAN] Cleaning previous unnecessary and temporary data...")
    
    stale_files = [
        PROJECT_ROOT / "cocompute.db",
        PROJECT_ROOT / "task_history.db",
        PROJECT_ROOT / "master" / "test_schema.db",
        PROJECT_ROOT / "master" / "test_import.db",
        PROJECT_ROOT / "tests" / "test_model_train.pkl",
    ]
    
    for file_path in stale_files:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"  - Removed stale file: {file_path.name}")
            except Exception as e:
                print(f"  - [WARN] Could not remove {file_path.name}: {e}")

    # Clean results directories
    storage_dirs = [
        PROJECT_ROOT / "storage" / "results",
        PROJECT_ROOT / "master" / "storage" / "results",
    ]
    for s_dir in storage_dirs:
        if s_dir.exists():
            for item in s_dir.iterdir():
                if item.is_dir():
                    try:
                        shutil.rmtree(item)
                        print(f"  - Cleaned result cache: {item.name}")
                    except Exception as e:
                        print(f"  - [WARN] Could not remove {item.name}: {e}")


def init_database(db_url: str, seed_admin: bool = True):
    """Create all database tables and optionally seed the initial admin user."""
    from master.app.db.database import Base
    from master.app.db import models
    from master.app.core.security import hash_password

    print(f"[INIT] Initializing database schema at: {db_url}")

    if db_url.startswith("sqlite"):
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(db_url, pool_pre_ping=True)

    # Create tables
    Base.metadata.create_all(bind=engine)
    
    insp = inspect(engine)
    tables = insp.get_table_names()
    print(f"  - Created {len(tables)} tables: {', '.join(tables)}")

    # Seed default admin user if requested
    if seed_admin:
        import secrets
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            admin_user = session.query(models.User).filter(models.User.role == "admin").first()
            if not admin_user:
                initial_password = os.getenv("COCOMPUTE_DEFAULT_ADMIN_PASSWORD")
                if not initial_password:
                    initial_password = secrets.token_urlsafe(12)
                    print(f"  - Initial administrator password generated: {initial_password}")
                else:
                    print("  - Initial administrator user created from environment.")

                admin_user = models.User(
                    username=os.getenv("COCOMPUTE_DEFAULT_ADMIN_USERNAME", "admin"),
                    email=os.getenv("COCOMPUTE_DEFAULT_ADMIN_EMAIL", "admin@cocompute.local"),
                    password_hash=hash_password(initial_password),
                    role="admin"
                )
                session.add(admin_user)
                session.commit()
            else:
                print("  - Admin account already exists.")
        finally:
            session.close()


def main():
    parser = argparse.ArgumentParser(description="CoCompute Database Initialization & Cleanup")
    parser.add_argument("--clean", action="store_true", help="Clean stale DB files and storage results first")
    parser.add_argument("--seed-admin", action="store_true", default=True, help="Seed initial admin user")
    parser.add_argument("--no-seed-admin", dest="seed_admin", action="store_false", help="Do not seed admin user")
    parser.add_argument("--db-url", type=str, default=None, help="Database connection URL")

    args = parser.parse_args()

    if args.clean:
        clean_stale_data()

    db_url = args.db_url or os.getenv("DATABASE_URL")
    if not db_url or "postgresql://" in db_url:
        # Default to local SQLite file for local standalone setup unless postgres is explicitly provided via --db-url
        # Let's test if postgres is reachable, otherwise use SQLite
        if db_url and "postgresql://" in db_url:
            try:
                import psycopg2
                # Quick test connection
                conn = psycopg2.connect(db_url, connect_timeout=2)
                conn.close()
            except Exception:
                db_path = PROJECT_ROOT / "cocompute.db"
                db_url = f"sqlite:///{db_path.as_posix()}"

    if not db_url:
        db_path = PROJECT_ROOT / "cocompute.db"
        db_url = f"sqlite:///{db_path.as_posix()}"

    init_database(db_url, seed_admin=args.seed_admin)
    print("[SUCCESS] Database setup completed successfully!")


if __name__ == "__main__":
    main()
