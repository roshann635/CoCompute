from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..db import database, models
from ..schemas import auth as schemas
from ..core.security import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter()

# Default institutional quotas by role
ROLE_QUOTAS = {
    "student": {
        "max_concurrent_jobs": 2,
        "max_workers_per_job": 5,
        "max_gpu_count": 0,
        "max_vram_gb": 0.0,
        "max_cpu_hours_per_day": 20.0,
        "priority": "NORMAL"
    },
    "researcher": {
        "max_concurrent_jobs": 5,
        "max_workers_per_job": 20,
        "max_gpu_count": 4,
        "max_vram_gb": 32.0,
        "max_cpu_hours_per_day": 100.0,
        "priority": "HIGH"
    },
    "faculty": {
        "max_concurrent_jobs": 10,
        "max_workers_per_job": 50,
        "max_gpu_count": 8,
        "max_vram_gb": 64.0,
        "max_cpu_hours_per_day": 250.0,
        "priority": "HIGH"
    },
    "admin": {
        "max_concurrent_jobs": 50,
        "max_workers_per_job": 100,
        "max_gpu_count": 16,
        "max_vram_gb": 128.0,
        "max_cpu_hours_per_day": 1000.0,
        "priority": "CRITICAL"
    }
}


@router.post("/register", response_model=schemas.TokenResponse)
def register(user_in: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Register a new user account with institutional quota assignment."""
    existing = db.query(models.User).filter(
        (models.User.username == user_in.username) | (models.User.email == user_in.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered"
        )
    
    user_count = db.query(models.User).count()
    role = "admin" if user_count == 0 else (user_in.role or "researcher").lower()
    quotas = ROLE_QUOTAS.get(role, ROLE_QUOTAS["researcher"])
    
    db_user = models.User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=role,
        max_concurrent_jobs=quotas["max_concurrent_jobs"],
        max_workers_per_job=quotas["max_workers_per_job"],
        max_gpu_count=quotas["max_gpu_count"],
        max_vram_gb=quotas["max_vram_gb"],
        max_cpu_hours_per_day=quotas["max_cpu_hours_per_day"],
        priority=quotas["priority"]
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    token = create_access_token(data={"sub": str(db_user.id), "role": db_user.role})
    return schemas.TokenResponse(access_token=token, user=schemas.UserResponse.model_validate(db_user))


@router.post("/login", response_model=schemas.TokenResponse)
def login(creds: schemas.UserLogin, db: Session = Depends(database.get_db)):
    """Authenticate and return a JWT."""
    user = db.query(models.User).filter(models.User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return schemas.TokenResponse(access_token=token, user=schemas.UserResponse.model_validate(user))


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return current_user


@router.get("/users", response_model=List[schemas.UserResponse])
def list_all_users(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all registered institutional users (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(models.User).all()


@router.put("/users/{user_id}/quota", response_model=schemas.UserResponse)
def update_user_quota(
    user_id: int,
    quota_in: schemas.UserQuotaUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update institutional resource quotas for a user (Admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if quota_in.role:
        target_user.role = quota_in.role
    if quota_in.max_concurrent_jobs is not None:
        target_user.max_concurrent_jobs = quota_in.max_concurrent_jobs
    if quota_in.max_workers_per_job is not None:
        target_user.max_workers_per_job = quota_in.max_workers_per_job
    if quota_in.max_gpu_count is not None:
        target_user.max_gpu_count = quota_in.max_gpu_count
    if quota_in.max_vram_gb is not None:
        target_user.max_vram_gb = quota_in.max_vram_gb
    if quota_in.max_cpu_hours_per_day is not None:
        target_user.max_cpu_hours_per_day = quota_in.max_cpu_hours_per_day
    if quota_in.priority:
        target_user.priority = quota_in.priority

    db.commit()
    db.refresh(target_user)
    return target_user
