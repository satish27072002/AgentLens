"""
SQLAlchemy models — define the database tables.

Five tables:
- users: Developer accounts (signup/login)
- api_keys: API keys for SDK authentication (linked to users)
- executions: One row per agent run (linked to users via user_id)
- llm_calls: One row per LLM API call within an execution
- tool_calls: One row per tool/function call within an execution
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """
    A developer account.

    Users authenticate via Auth0 (OAuth2/OIDC). No passwords stored locally.
    The auth0_sub field links the Auth0 identity to this local user record.

    On first login, the backend auto-creates a User row using the Auth0 profile.
    API keys are generated for SDK authentication (separate from Auth0).
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True)  # UUID as string
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(
        String, nullable=True
    )  # Nullable — Auth0 users don't have local passwords
    auth0_sub = Column(
        String, unique=True, nullable=True
    )  # Auth0 user ID, e.g. "auth0|abc123"
    name = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    api_keys = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    executions = relationship("Execution", back_populates="user")


class ApiKey(Base):
    """
    An API key for SDK authentication.

    Each user can have multiple keys (e.g., one for dev, one for prod).
    Keys have an "al_" prefix (like Stripe's "sk_" prefix) so developers
    can easily identify which service a key belongs to.
    """

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key_value = Column(String, unique=True, nullable=False)  # e.g. "al_k7x9m2abc..."
    name = Column(String, default="Default")  # user-friendly label
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_key_value", "key_value"),
        Index("idx_api_keys_user_id", "user_id"),
    )


class Execution(Base):
    """
    An agent execution — one complete run of an AI agent.

    Example: A customer support agent handles one user question.
    That's one execution, which might involve 3 LLM calls and 2 tool calls.

    user_id links this execution to the developer who sent it via their API key.
    This is what makes multi-tenancy work — each query filters by user_id.
    """

    __tablename__ = "executions"

    id = Column(String, primary_key=True)  # UUID as string
    user_id = Column(
        String, ForeignKey("users.id"), nullable=True
    )  # nullable for backward compat
    agent_name = Column(String, nullable=False)  # e.g. "CustomerSupportAgent"
    status = Column(String, default="running")  # running | completed | failed
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Total execution time
    total_cost = Column(Float, default=0.0)  # Sum of all LLM call costs
    total_tokens = Column(Integer, default=0)  # Sum of all tokens used
    error_message = Column(Text, nullable=True)  # NULL if no error
    metadata_json = Column(Text, nullable=True)  # Extra data as JSON string
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="executions")
    llm_calls = relationship(
        "LLMCall", back_populates="execution", cascade="all, delete-orphan"
    )
    tool_calls = relationship(
        "ToolCall", back_populates="execution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_executions_agent_name", "agent_name"),
        Index("idx_executions_started_at", "started_at"),
        Index("idx_executions_user_id", "user_id"),
    )


class LLMCall(Base):
    """
    A single LLM API call within an execution.

    Tracks which model was used, how many tokens, what it cost, and how long it took.
    """

    __tablename__ = "llm_calls"

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False)
    provider = Column(String, nullable=True)  # openai, anthropic, etc.
    model = Column(String, nullable=True)  # gpt-4o, claude-3, etc.
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    execution = relationship("Execution", back_populates="llm_calls")

    __table_args__ = (Index("idx_llm_calls_execution_id", "execution_id"),)


class ToolCall(Base):
    """
    A single tool/function call within an execution.

    Example: An agent calling a "search_database" or "send_email" tool.
    """

    __tablename__ = "tool_calls"

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False)
    tool_name = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String, nullable=True)  # success | error
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    execution = relationship("Execution", back_populates="tool_calls")

    __table_args__ = (Index("idx_tool_calls_execution_id", "execution_id"),)
