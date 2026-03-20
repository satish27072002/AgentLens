"""
GET /api/stats — Summary statistics for the dashboard.

Returns aggregated numbers for the stat cards at the top of the dashboard:
- Total executions
- Total cost
- Average duration
- Success rate
- Executions today
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Execution
from app.schemas import StatsResponse

router = APIRouter()


@router.get("/api/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """
    Compute and return dashboard summary statistics.

    All stats are computed from the executions table using SQL aggregations.
    This is efficient — the database does the math, not Python.
    """
    total_executions = db.query(func.count(Execution.id)).scalar() or 0

    total_cost = db.query(func.sum(Execution.total_cost)).scalar() or 0.0

    avg_duration = db.query(func.avg(Execution.duration_ms)).scalar() or 0.0

    # Success rate = completed / total (avoid division by zero)
    if total_executions > 0:
        completed_count = (
            db.query(func.count(Execution.id))
            .filter(Execution.status == "completed")
            .scalar() or 0
        )
        success_rate = (completed_count / total_executions) * 100
    else:
        success_rate = 0.0

    # Executions today — filter by date
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    executions_today = (
        db.query(func.count(Execution.id))
        .filter(Execution.started_at >= today_start)
        .scalar() or 0
    )

    return StatsResponse(
        total_executions=total_executions,
        total_cost=round(total_cost, 4),
        avg_duration_ms=round(avg_duration, 1),
        success_rate=round(success_rate, 1),
        executions_today=executions_today,
    )
