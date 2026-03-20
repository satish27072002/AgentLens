"""
GET endpoints for executions — serves data to the frontend dashboard.

Two endpoints:
- GET /api/executions      — List all executions (paginated, for the table)
- GET /api/executions/{id} — Get one execution with its LLM/tool calls (for detail page)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Execution
from app.schemas import ExecutionListResponse, ExecutionDetailResponse

router = APIRouter()


@router.get("/api/executions", response_model=ExecutionListResponse)
def list_executions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    agent_name: str | None = Query(None, description="Filter by agent name"),
    status: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """
    List executions with pagination and optional filters.

    Used by the dashboard's execution table.
    Returns newest first so the most recent runs appear at the top.
    """
    query = db.query(Execution)

    # Apply filters if provided
    if agent_name:
        query = query.filter(Execution.agent_name == agent_name)
    if status:
        query = query.filter(Execution.status == status)

    # Get total count (before pagination) for the frontend to show "Page X of Y"
    total = query.count()

    # Get paginated results, newest first
    executions = query.order_by(Execution.started_at.desc()).offset(skip).limit(limit).all()

    return ExecutionListResponse(
        executions=executions,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/api/executions/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """
    Get a single execution with all its LLM calls and tool calls.

    Used by the execution detail page.
    joinedload() tells SQLAlchemy to fetch the related calls in one query
    instead of making separate queries (N+1 problem prevention).
    """
    execution = (
        db.query(Execution)
        .options(joinedload(Execution.llm_calls), joinedload(Execution.tool_calls))
        .filter(Execution.id == execution_id)
        .first()
    )

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution
