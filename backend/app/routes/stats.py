"""
GET /api/stats — Summary statistics for the dashboard.

MODIFIED for Phase 2: Now requires JWT auth and filters by user_id.
Each user sees stats computed only from their own executions.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Execution
from app.schemas import StatsResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/api/stats", response_model=StatsResponse)
def get_stats(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute and return dashboard summary statistics for the current user.

    The only change from Phase 1: every query includes .filter(user_id == user.id).
    """
    base_query = db.query(Execution).filter(Execution.user_id == user.id)

    total_executions = base_query.count()

    total_cost = db.query(func.sum(Execution.total_cost)).filter(
        Execution.user_id == user.id
    ).scalar() or 0.0

    avg_duration = db.query(func.avg(Execution.duration_ms)).filter(
        Execution.user_id == user.id
    ).scalar() or 0.0

    if total_executions > 0:
        completed_count = base_query.filter(Execution.status == "completed").count()
        success_rate = (completed_count / total_executions) * 100
    else:
        success_rate = 0.0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    executions_today = base_query.filter(Execution.started_at >= today_start).count()

    return StatsResponse(
        total_executions=total_executions,
        total_cost=round(total_cost, 4),
        avg_duration_ms=round(avg_duration, 1),
        success_rate=round(success_rate, 1),
        executions_today=executions_today,
    )
