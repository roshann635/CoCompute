"""
Projects API — multi-user project grouping & institutional resource organization.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..db import database, models
from ..schemas import project as schemas
from ..core.security import get_current_user

router = APIRouter()


@router.post("/", response_model=schemas.ProjectResponse)
def create_project(
    project_in: schemas.ProjectCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new project for the current user."""
    count = db.query(models.Project).count()
    project_uid = f"PROJECT-{count + 1:02d}"

    project = models.Project(
        project_uid=project_uid,
        name=project_in.name,
        description=project_in.description,
        user_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/", response_model=List[schemas.ProjectResponse])
def list_projects(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List projects for the current user (or all projects if admin)."""
    if current_user.role == "admin":
        projects = db.query(models.Project).all()
    else:
        projects = db.query(models.Project).filter(models.Project.user_id == current_user.id).all()

    # Annotate with job count
    res = []
    for p in projects:
        j_count = db.query(models.Job).filter(models.Job.project_id == p.id).count()
        item = schemas.ProjectResponse.model_validate(p)
        item.job_count = j_count
        res.append(item)
    return res


@router.get("/{project_id}", response_model=schemas.ProjectDetailResponse)
def get_project_detail(
    project_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get project details and contained jobs."""
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    jobs = db.query(models.Job).filter(models.Job.project_id == project.id).all()
    item = schemas.ProjectDetailResponse.model_validate(project)
    item.jobs = jobs
    item.job_count = len(jobs)
    return item
