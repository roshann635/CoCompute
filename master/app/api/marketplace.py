"""
Marketplace & Compute Pool REST API — CoCompute 3.0.

Provides:
  - GET  /api/v1/marketplace/pool — Aggregate cluster capacity, hardware pools, and utilization %
  - GET  /api/v1/credits/balance  — User credit allowance and daily usage
  - GET  /api/v1/credits/history  — User credit transaction ledger
  - POST /api/v1/credits/allocate — Admin credit allocation / reload
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from ..db.database import get_db
from ..db import models
from ..core.security import get_current_user, get_current_admin_user
from ..schemas.marketplace import (
    ComputePoolSummary,
    CreditBalanceResponse,
    CreditTransactionResponse,
    AllocateCreditsRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/marketplace", tags=["Marketplace & Compute Pool"])
credits_router = APIRouter(prefix="/api/v1/credits", tags=["Compute Credits"])


@router.get("/pool", response_model=ComputePoolSummary)
def get_compute_pool_summary(db: Session = Depends(get_db)):
    """
    Returns unified aggregate cluster compute pool metrics (cores, RAM, GPUs, VRAM, utilization).
    """
    workers = db.query(models.Worker).filter(models.Worker.trust_status != "rejected").all()
    online_workers = [w for w in workers if w.status in ("online", "idle", "busy")]
    busy_workers = [w for w in workers if w.status == "busy"]
    simulated_workers = [w for w in workers if getattr(w, "is_simulated", False)]

    total_cores = sum(w.cpu_cores or 0 for w in online_workers)
    total_ram = sum(w.ram_total or 0.0 for w in online_workers)
    total_gpus = sum(w.gpu_count or 0 for w in online_workers)
    total_vram = sum(w.vram_total or 0.0 for w in online_workers)

    avg_cpu = (sum(w.cpu_utilization or 0.0 for w in online_workers) / len(online_workers)) if online_workers else 0.0
    avg_ram = (sum(w.ram_usage or 0.0 for w in online_workers) / len(online_workers)) if online_workers else 0.0
    pool_util = round((avg_cpu * 0.6) + (avg_ram * 0.4), 2)

    active_jobs = db.query(models.Job).filter(models.Job.status == "running").count()
    queued_jobs = db.query(models.Job).filter(models.Job.status == "pending").count()

    return ComputePoolSummary(
        total_workers=len(workers),
        online_workers=len(online_workers),
        busy_workers=len(busy_workers),
        total_cpu_cores=total_cores,
        total_ram_gb=round(total_ram, 1),
        total_gpus=total_gpus,
        total_vram_gb=round(total_vram, 1),
        avg_cpu_utilization=round(avg_cpu, 1),
        avg_ram_utilization=round(avg_ram, 1),
        pool_utilization_pct=pool_util,
        active_jobs_count=active_jobs,
        queued_jobs_count=queued_jobs,
        simulated_workers_count=len(simulated_workers)
    )


@credits_router.get("/balance", response_model=CreditBalanceResponse)
def get_user_credit_balance(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    balance = getattr(current_user, "credits_balance", 500.0) or 500.0
    quota = getattr(current_user, "credits_daily_quota", 500.0) or 500.0
    consumed = getattr(current_user, "credits_consumed_today", 0.0) or 0.0
    remaining = max(0.0, balance)

    return CreditBalanceResponse(
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role or "researcher",
        credits_balance=round(balance, 2),
        credits_daily_quota=round(quota, 2),
        credits_consumed_today=round(consumed, 2),
        remaining_today=round(remaining, 2)
    )


@credits_router.get("/history", response_model=List[CreditTransactionResponse])
def get_credit_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    txs = db.query(models.CreditTransaction).filter(
        models.CreditTransaction.user_id == current_user.id
    ).order_by(models.CreditTransaction.id.desc()).limit(50).all()
    return txs


@credits_router.post("/allocate", response_model=CreditBalanceResponse)
def allocate_credits(
    req: AllocateCreditsRequest,
    admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    target_user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {req.user_id} not found")

    target_user.credits_balance = (target_user.credits_balance or 0.0) + req.amount
    db.add(models.CreditTransaction(
        user_id=target_user.id,
        amount=req.amount,
        description=req.description or f"Allocated by Admin ({admin_user.username})"
    ))
    db.commit()

    return CreditBalanceResponse(
        user_id=target_user.id,
        username=target_user.username,
        role=target_user.role or "user",
        credits_balance=target_user.credits_balance,
        credits_daily_quota=target_user.credits_daily_quota or 500.0,
        credits_consumed_today=target_user.credits_consumed_today or 0.0,
        remaining_today=target_user.credits_balance
    )
