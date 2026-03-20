"""
SQLAlchemy models — define the database tables.

Three tables:
- executions: One row per agent run (the top-level unit)
- llm_calls: One row per LLM API call within an execution
- tool_calls: One row per tool/function call within an execution

Each execution has many llm_calls and tool_calls (one-to-many relationship).
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Execution(Base):
    """
    An agent execution — one complete run of an AI agent.

    Example: A customer support agent handles one user question.
    That's one execution, which might involve 3 LLM calls and 2 tool calls.
    """
    __tablename__ = "executions"

    id = Column(String, primary_key=True)                          # UUID as string
    agent_name = Column(String, nullable=False)                    # e.g. "CustomerSupportAgent"
    status = Column(String, default="running")                     # running | completed | failed
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)                   # Total execution time
    total_cost = Column(Float, default=0.0)                        # Sum of all LLM call costs
    total_tokens = Column(Integer, default=0)                      # Sum of all tokens used
    error_message = Column(Text, nullable=True)                    # NULL if no error
    metadata_json = Column(Text, nullable=True)                    # Extra data as JSON string
    created_at = Column(DateTime, server_default=func.now())

    # Relationships — lets you do execution.llm_calls to get all related calls
    llm_calls = relationship("LLMCall", back_populates="execution", cascade="all, delete-orphan")
    tool_calls = relationship("ToolCall", back_populates="execution", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_executions_agent_name", "agent_name"),
        Index("idx_executions_started_at", "started_at"),
    )


class LLMCall(Base):
    """
    A single LLM API call within an execution.

    Tracks which model was used, how many tokens, what it cost, and how long it took.
    """
    __tablename__ = "llm_calls"

    id = Column(String, primary_key=True)
    execution_id = Column(String, ForeignKey("executions.id"), nullable=False)
    provider = Column(String, nullable=True)                       # openai, anthropic, etc.
    model = Column(String, nullable=True)                          # gpt-4o, claude-3, etc.
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    execution = relationship("Execution", back_populates="llm_calls")

    __table_args__ = (
        Index("idx_llm_calls_execution_id", "execution_id"),
    )


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
    status = Column(String, nullable=True)                         # success | error
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    execution = relationship("Execution", back_populates="tool_calls")

    __table_args__ = (
        Index("idx_tool_calls_execution_id", "execution_id"),
    )
