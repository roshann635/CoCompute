"""
Round Robin Scheduler — baseline comparison scheduler.
Cycles through online workers sequentially, assigning one chunk per worker in order.
"""
import logging
from sqlalchemy.orm import Session
from ..db import models

logger = logging.getLogger(__name__)

_round_robin_index = 0


def round_robin_select(workers: list[models.Worker], chunk: models.TaskChunk, db: Session) -> models.Worker | None:
    """
    Select the next worker in a round-robin fashion.
    Returns the selected worker, or None if no workers are available.
    """
    global _round_robin_index
    
    if not workers:
        return None
    
    selected = workers[_round_robin_index % len(workers)]
    _round_robin_index = (_round_robin_index + 1) % len(workers)
    
    logger.info(f"[RoundRobin] Selected worker {selected.worker_uid} for chunk {chunk.id} (index {_round_robin_index})")
    return selected
