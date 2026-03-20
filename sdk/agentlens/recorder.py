"""
Event recorder — thread-safe collection of LLM/tool call events.

The recorder sits between the patchers (which capture events) and
the sender (which ships them to the backend). It's a simple thread-safe
list with some convenience methods.

Flow: Patcher captures event → recorder.record() → sender reads & flushes
"""

import uuid
import threading
from datetime import datetime, timezone
from typing import Any


class EventRecorder:
    """
    Thread-safe event collector.

    Events are accumulated in memory and periodically flushed
    by the BackgroundSender.
    """

    def __init__(self):
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._current_execution_id: str | None = None
        self._current_agent_name: str = "default"

    def start_execution(self, agent_name: str) -> str:
        """Start a new execution context. Returns the execution_id."""
        self._current_execution_id = str(uuid.uuid4())
        self._current_agent_name = agent_name
        return self._current_execution_id

    def end_execution(self):
        """End the current execution context."""
        self._current_execution_id = None
        self._current_agent_name = "default"

    @property
    def execution_id(self) -> str:
        """Get or create the current execution ID."""
        if not self._current_execution_id:
            self._current_execution_id = str(uuid.uuid4())
        return self._current_execution_id

    def record_llm_call(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        cost: float,
        duration_ms: int,
        error: str | None = None,
    ):
        """Record an LLM API call event."""
        event = {
            "type": "llm_call",
            "id": str(uuid.uuid4()),
            "execution_id": self.execution_id,
            "agent_name": self._current_agent_name,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "duration_ms": duration_ms,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._events.append(event)

    def record_tool_call(
        self,
        tool_name: str,
        duration_ms: int,
        status: str = "success",
        error_message: str | None = None,
    ):
        """Record a tool/function call event."""
        event = {
            "type": "tool_call",
            "id": str(uuid.uuid4()),
            "execution_id": self.execution_id,
            "agent_name": self._current_agent_name,
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "status": status,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._lock:
            self._events.append(event)

    def flush(self) -> list[dict[str, Any]]:
        """
        Return all accumulated events and clear the buffer.

        Called by the BackgroundSender. Thread-safe.
        """
        with self._lock:
            events = self._events.copy()
            self._events.clear()
        return events
