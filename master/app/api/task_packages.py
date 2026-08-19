"""
Task Package Registry & Pre-Flight Compatibility REST API — CoCompute 4.0.
"""

import hashlib
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from master.app.db import models
from master.app.db.database import get_db
from master.app.schemas import task_package as schemas
from master.app.engine.task_validator import validate_task_security, run_compatibility_test
from shared.sdk.task_contract import BaseTaskDefinition

router = APIRouter(prefix="/api/v1/tasks/packages", tags=["task-packages"])


@router.post("", response_model=schemas.TaskPackageResponse)
def create_task_package(
    req: schemas.TaskPackageCreate,
    db: Session = Depends(get_db)
):
    """
    Registers a new user-defined task package in the CoCompute Task Registry.
    Runs static AST security validation upfront.
    """
    # 1. Static Security Inspection
    sec_report = validate_task_security(req.script_code)
    if not sec_report["is_safe"]:
        raise HTTPException(
            status_code=400,
            detail=f"Task code failed security validation: {', '.join(sec_report['violations'])}"
        )

    # Compute code hash
    code_hash = hashlib.sha256(req.script_code.encode("utf-8")).hexdigest()
    pkg_uid = f"PKG-{uuid.uuid4().hex[:8].upper()}"

    db_pkg = models.TaskPackage(
        package_uid=pkg_uid,
        name=req.name,
        version=req.version,
        description=req.description,
        author="system_user",
        runtime=req.runtime,
        is_public=req.is_public,
        code_hash=code_hash,
        manifest=req.manifest.dict(),
        script_code=req.script_code,
        entrypoint=req.entrypoint,
        is_verified=False
    )
    db.add(db_pkg)
    db.commit()
    db.refresh(db_pkg)
    return db_pkg


@router.get("", response_model=List[schemas.TaskPackageResponse])
def list_task_packages(
    search: Optional[str] = Query(None),
    public_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Lists all available registered Task Packages in the registry.
    """
    query = db.query(models.TaskPackage)
    if public_only:
        query = query.filter(models.TaskPackage.is_public == True)
    if search:
        query = query.filter(models.TaskPackage.name.ilike(f"%{search}%"))
    return query.order_by(models.TaskPackage.created_at.desc()).all()


@router.get("/{pkg_id}", response_model=schemas.TaskPackageResponse)
def get_task_package(pkg_id: int, db: Session = Depends(get_db)):
    pkg = db.query(models.TaskPackage).filter(models.TaskPackage.id == pkg_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Task package not found")
    return pkg


@router.post("/{pkg_id}/test", response_model=schemas.TaskTestResponse)
def test_task_package(
    pkg_id: int,
    req: schemas.TaskTestRequest,
    db: Session = Depends(get_db)
):
    """
    Runs the Pre-Flight Compatibility Test validating all 5 hooks before cluster submission.
    """
    pkg = db.query(models.TaskPackage).filter(models.TaskPackage.id == pkg_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Task package not found")

    code_to_test = req.script_code or pkg.script_code

    # Instantiate task definition safely
    local_scope = {}
    try:
        exec(code_to_test, local_scope)
        task_cls = local_scope.get(pkg.entrypoint) or local_scope.get("Task")
        if not task_cls:
            raise ValueError(f"Entrypoint class '{pkg.entrypoint}' not found in script.")
        task_instance = task_cls()
    except Exception as e:
        return schemas.TaskTestResponse(
            passed=False,
            recommendation="Failed instantiation",
            report={"error": f"Failed to instantiate task class: {str(e)}"}
        )

    report = run_compatibility_test(task_instance, req.sample_input)
    pkg.is_verified = report["passed"]
    pkg.compatibility_report = report
    db.commit()

    return schemas.TaskTestResponse(
        passed=report["passed"],
        recommendation=report["recommendation"],
        report=report
    )
