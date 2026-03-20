"""
Trace — the context manager that collects execution data.

This is the core of the SDK. When you write:

    with lens.trace("MyAgent") as trace:
        trace.log_llm_call(...)
        trace.log_tool_call(...)

Here's what happens:
1. __enter__: Records the start time, generates a unique execution ID
2. Your code runs, calling log_llm_call() and log_tool_call() to record events
3. __exit__: Records the end time, calculates duration, sends everything to the backend

Python context manager protocol:
- __enter__ is called when the `with` block starts
- __exit__ is called when the `with` block ends (even if an exception occurs)
"""

import json
import uuid
import time
from datetime import datetime, timezone
from typing import Any

import httpx


class Trace:
    """
    Collects LLM calls and tool calls during an agent execution,
    then sends the complete trace to the backend on exit.
    """

    def __init__(
        self,
        agent_name: str,
        metadata: dict | None,
        client: httpx.Client,
        endpoint: str,
        silent: bool,
    ):
        self.agent_name = agent_name
        self.metadata = metadata
        self._client = client
        self._endpoint = endpoint
        self._silent = silent

        # Generated on __enter__
        self.execution_id: str = ""
        self._start_time: float = 0.0
        self._started_at: datetime | None = None

        # Collected during execution
        self._llm_calls: list[dict] = []
        self._tool_calls: list[dict] = []
        self._error_message: str | None = None
        self._status: str = "completed"

    def __enter__(self) -> "Trace":
        """Start the trace — record start time and generate execution ID."""
        self.execution_id = str(uuid.uuid4())
        self._start_time = time.monotonic()
        self._started_at = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """
        End the trace — calculate duration and send data to backend.

        If an exception occurred in the `with` block:
        - We capture it as the error_message
        - We set status to "failed"
        - We still send the trace (so you can see failures in the dashboard)
        - We return False (re-raises the exception — we don't swallow it)
        """
        duration_ms = int((time.monotonic() - self._start_time) * 1000)
        completed_at = datetime.now(timezone.utc)

        # If an exception happened in the with block, record it
        if exc_type is not None:
            self._status = "failed"
            self._error_message = f"{exc_type.__name__}: {exc_val}"

        # Calculate totals from collected LLM calls
        total_cost = sum(c.get("cost", 0) or 0 for c in self._llm_calls)
        total_tokens = sum(c.get("total_tokens", 0) or 0 for c in self._llm_calls)

        # Build the payload matching the backend's TraceCreate schema
        payload = {
            "id": self.execution_id,
            "agent_name": self.agent_name,
            "status": self._status,
            "started_at": self._started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_ms": duration_ms,
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "error_message": self._error_message,
            "metadata_json": json.dumps(self.metadata) if self.metadata else None,
            "llm_calls": self._llm_calls,
            "tool_calls": self._tool_calls,
        }

        self._send(payload)

        # Return False = don't suppress exceptions from the with block
        return False

    def log_llm_call(
        self,
        provider: str | None = None,
        model: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        cost: float | None = None,
        duration_ms: int | None = None,
    ) -> str:
        """
        Record an LLM API call.

        Call this after each LLM call in your agent. Returns the call ID.

        Example:
            response = openai.chat.completions.create(...)
            trace.log_llm_call(
                provider="openai",
                model="gpt-4o",
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cost=0.003,
                duration_ms=1200,
            )
        """
        call_id = str(uuid.uuid4())

        # Auto-calculate total_tokens if not provided
        if total_tokens is None and prompt_tokens and completion_tokens:
            total_tokens = prompt_tokens + completion_tokens

        self._llm_calls.append({
            "id": call_id,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": cost,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return call_id

    def log_tool_call(
        self,
        tool_name: str,
        duration_ms: int | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> str:
        """
        Record a tool/function call.

        Call this after each tool use in your agent. Returns the call ID.

        Example:
            result = my_search_tool(query)
            trace.log_tool_call(
                tool_name="search_database",
                duration_ms=350,
                status="success",
            )
        """
        call_id = str(uuid.uuid4())

        self._tool_calls.append({
            "id": call_id,
            "tool_name": tool_name,
            "duration_ms": duration_ms,
            "status": status,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return call_id

    def set_error(self, message: str):
        """
        Manually mark this execution as failed.

        Use this when you want to mark a failure without raising an exception.

        Example:
            if not result:
                trace.set_error("No results found after 3 retries")
        """
        self._status = "failed"
        self._error_message = message

    def _send(self, payload: dict):
        """Send the trace payload to the backend."""
        try:
            response = self._client.post(
                f"{self._endpoint}/api/traces",
                json=payload,
            )
            if response.status_code not in (200, 201):
                if not self._silent:
                    print(f"[AgentLens] Warning: Backend returned {response.status_code}: {response.text}")
        except Exception as e:
            if not self._silent:
                print(f"[AgentLens] Warning: Failed to send trace: {e}")
            # Never crash the user's agent because monitoring failed
