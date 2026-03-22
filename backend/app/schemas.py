"""
Pydantic schemas — define what data looks like going in and out of the API.

Why separate from models.py?
- models.py = database shape (how data is stored)
- schemas.py = API shape (how data is sent/received)

This separation lets you:
- Validate incoming data automatically (Pydantic rejects bad requests)
- Control what fields are exposed in responses (hide internal fields)
- Have different shapes for create vs read operations
"""

from datetime import datetime
from pydantic import BaseModel


# ──────────────────────────────────────────────
# Auth schemas
# ──────────────────────────────────────────────

class SignupRequest(BaseModel):
    """Data needed to create a new account."""
    email: str
    password: str
    name: str | None = None


class LoginRequest(BaseModel):
    """Data needed to log in."""
    email: str
    password: str


class AuthResponse(BaseModel):
    """Returned after successful signup or login."""
    user_id: str
    token: str
    api_key: str | None = None  # Only returned on signup (first key auto-created)


class UserResponse(BaseModel):
    """User profile data (returned by GET /api/auth/me)."""
    id: str
    email: str
    name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    """Request to generate a new API key."""
    name: str = "Default"


class ApiKeyResponse(BaseModel):
    """API key as returned in responses (key is masked except on creation)."""
    id: str
    name: str
    key_preview: str  # last 8 chars only, e.g. "...abc12345"
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(BaseModel):
    """Returned when a new key is created — shows the FULL key (only time it's visible)."""
    id: str
    name: str
    key: str  # full key — developer must copy it now
    created_at: datetime


# ──────────────────────────────────────────────
# Request schemas (data coming IN from the SDK)
# ──────────────────────────────────────────────

class LLMCallCreate(BaseModel):
    """Schema for a single LLM call sent by the SDK."""
    id: str
    provider: str | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    duration_ms: int | None = None
    timestamp: datetime | None = None


class ToolCallCreate(BaseModel):
    """Schema for a single tool call sent by the SDK."""
    id: str
    tool_name: str | None = None
    duration_ms: int | None = None
    status: str | None = None
    error_message: str | None = None
    timestamp: datetime | None = None


class TraceCreate(BaseModel):
    """
    The main payload the SDK sends to POST /api/traces.
    Contains one execution with its associated LLM and tool calls.
    """
    id: str
    agent_name: str
    status: str = "completed"
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    total_cost: float = 0.0
    total_tokens: int = 0
    error_message: str | None = None
    metadata_json: str | None = None
    llm_calls: list[LLMCallCreate] = []
    tool_calls: list[ToolCallCreate] = []


# ──────────────────────────────────────────────
# Response schemas (data going OUT to the frontend)
# ──────────────────────────────────────────────

class LLMCallResponse(BaseModel):
    """LLM call as returned in API responses."""
    id: str
    execution_id: str
    provider: str | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cost: float | None = None
    duration_ms: int | None = None
    timestamp: datetime | None = None

    model_config = {"from_attributes": True}


class ToolCallResponse(BaseModel):
    """Tool call as returned in API responses."""
    id: str
    execution_id: str
    tool_name: str | None = None
    duration_ms: int | None = None
    status: str | None = None
    error_message: str | None = None
    timestamp: datetime | None = None

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    """Execution summary for list views (no nested calls)."""
    id: str
    agent_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None
    total_cost: float
    total_tokens: int
    error_message: str | None = None

    model_config = {"from_attributes": True}


class ExecutionDetailResponse(ExecutionResponse):
    """Execution with nested LLM and tool calls (for detail view)."""
    llm_calls: list[LLMCallResponse] = []
    tool_calls: list[ToolCallResponse] = []


class ExecutionListResponse(BaseModel):
    """Paginated list of executions."""
    executions: list[ExecutionResponse]
    total: int
    skip: int
    limit: int


class StatsResponse(BaseModel):
    """Dashboard summary statistics."""
    total_executions: int
    successful_executions: int = 0
    total_cost: float
    avg_duration_ms: float
    success_rate: float
    total_llm_calls: int = 0
    executions_today: int
