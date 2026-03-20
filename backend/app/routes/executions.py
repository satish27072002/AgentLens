"""
GET endpoints for executions — serves data to the frontend dashboard.

MODIFIED for Phase 2: Now requires JWT auth and filters by user_id.
Each user only sees their own executions (multi-tenancy).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import User, Execution
from app.schemas import ExecutionListResponse, ExecutionDetailResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/api/executions", response_model=ExecutionListResponse)
def list_executions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    agent_name: str | None = Query(None, description="Filter by agent name"),
    status: str | None = Query(None, description="Filter by status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List executions for the current user (paginated).

    The key change from Phase 1: we filter by user_id.
    User A only sees User A's data. This one WHERE clause is multi-tenancy.
    """
    query = db.query(Execution).filter(Execution.user_id == user.id)

    if agent_name:
        query = query.filter(Execution.agent_name == agent_name)
    if status:
        query = query.filter(Execution.status == status)

    total = query.count()
    executions = query.order_by(Execution.started_at.desc()).offset(skip).limit(limit).all()

    return ExecutionListResponse(
        executions=executions,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/api/executions/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution(
    execution_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single execution with all its LLM calls and tool calls.

    Also filters by user_id — User A can't view User B's execution
    even if they know the execution ID.
    """
    execution = (
        db.query(Execution)
        .options(joinedload(Execution.llm_calls), joinedload(Execution.tool_calls))
        .filter(Execution.id == execution_id, Execution.user_id == user.id)
        .first()
    )

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution
