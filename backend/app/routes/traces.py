"""
POST /api/traces — Receive telemetry data from the SDK.

MODIFIED for Phase 2: Now requires an API key header (X-API-Key).
The API key is looked up to find the user_id, which is stored on the execution.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Execution, LLMCall, ToolCall
from app.schemas import TraceCreate
from app.dependencies import get_user_from_api_key

router = APIRouter()


@router.post("/api/traces", status_code=201)
def create_trace(
    trace: TraceCreate,
    user: User = Depends(get_user_from_api_key),
    db: Session = Depends(get_db),
):
    """
    Ingest a complete execution trace from the SDK.

    Requires: X-API-Key header with a valid API key.

    The API key resolves to a user_id, which is stored on the execution.
    This is what makes multi-tenancy work — each execution belongs to a user.
    """
    # Check if execution already exists (idempotency)
    existing = db.query(Execution).filter(Execution.id == trace.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Execution already exists")

    # Create the execution record — now with user_id
    execution = Execution(
        id=trace.id,
        user_id=user.id,
        agent_name=trace.agent_name,
        status=trace.status,
        started_at=trace.started_at,
        completed_at=trace.completed_at,
        duration_ms=trace.duration_ms,
        total_cost=trace.total_cost,
        total_tokens=trace.total_tokens,
        error_message=trace.error_message,
        metadata_json=trace.metadata_json,
    )
    db.add(execution)

    # Create LLM call records
    for llm_call in trace.llm_calls:
        db.add(
            LLMCall(
                id=llm_call.id,
                execution_id=trace.id,
                provider=llm_call.provider,
                model=llm_call.model,
                prompt_tokens=llm_call.prompt_tokens,
                completion_tokens=llm_call.completion_tokens,
                total_tokens=llm_call.total_tokens,
                cost=llm_call.cost,
                duration_ms=llm_call.duration_ms,
                timestamp=llm_call.timestamp,
            )
        )

    # Create tool call records
    for tool_call in trace.tool_calls:
        db.add(
            ToolCall(
                id=tool_call.id,
                execution_id=trace.id,
                tool_name=tool_call.tool_name,
                duration_ms=tool_call.duration_ms,
                status=tool_call.status,
                error_message=tool_call.error_message,
                timestamp=tool_call.timestamp,
            )
        )

    db.commit()

    return {"status": "ok", "execution_id": trace.id}
