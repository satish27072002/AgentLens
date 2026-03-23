"""
Background sender — ships events to the backend without blocking the developer's code.

Runs in a daemon thread that wakes up every `flush_interval` seconds,
grabs accumulated events from the recorder, groups them by execution,
and sends them to POST /api/traces.

Critical design decisions:
- Daemon thread: exits automatically when the main program exits
- try/except on send: NEVER crash the developer's code
- Groups events by execution_id before sending (backend expects one execution per request)
"""

import sys
import uuid
import atexit
import logging
import threading
from datetime import datetime, timezone
from typing import TYPE_CHECKING

logger = logging.getLogger("agentlens")

import httpx

if TYPE_CHECKING:
    from agentlens.recorder import EventRecorder


class BackgroundSender:
    """
    Periodically sends accumulated events to the backend.

    Args:
        endpoint: Backend URL
        api_key: API key for authentication
        recorder: EventRecorder to read events from
        flush_interval: Seconds between flushes (default: 5)
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        recorder: "EventRecorder",
        flush_interval: float = 5.0,
    ):
        self._endpoint = endpoint
        self._api_key = api_key
        self._recorder = recorder
        self._flush_interval = flush_interval
        self._running = True
        self._client = httpx.Client(
            timeout=10,
            headers={"X-API-Key": api_key},
        )

        # Start the background thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        # Flush remaining events when the program exits
        atexit.register(self._final_flush)

    def _run(self):
        """Main loop — sleep, then flush."""
        stop_event = threading.Event()
        while self._running:
            stop_event.wait(timeout=self._flush_interval)
            if self._running:
                self._flush()

    def _flush(self):
        """Grab events from recorder and send them grouped by execution."""
        events = self._recorder.flush()
        if not events:
            return

        # Group events by execution_id
        executions: dict[str, list[dict]] = {}
        for event in events:
            exec_id = event.get("execution_id", "unknown")
            if exec_id not in executions:
                executions[exec_id] = []
            executions[exec_id].append(event)

        # Send each execution as a separate trace
        for exec_id, exec_events in executions.items():
            self._send_execution(exec_id, exec_events)

    def _send_execution(self, execution_id: str, events: list[dict]):
        """Convert events into a trace payload and send to backend."""
        llm_calls = [e for e in events if e["type"] == "llm_call"]
        tool_calls = [e for e in events if e["type"] == "tool_call"]

        # Get agent name from the first event
        agent_name = events[0].get("agent_name", "default")

        # Calculate totals
        total_cost = sum(e.get("cost", 0) for e in llm_calls)
        total_tokens = sum(e.get("total_tokens", 0) for e in llm_calls)

        # Determine timestamps
        timestamps = [e["timestamp"] for e in events]
        started_at = min(timestamps)
        completed_at = max(timestamps)

        # Determine status — failed if any event has an error
        has_error = any(e.get("error") for e in events)
        error_msg = next((e["error"] for e in events if e.get("error")), None)

        # Calculate duration from first to last event
        durations = [e.get("duration_ms", 0) for e in events]
        total_duration = sum(durations)

        payload = {
            "id": execution_id,
            "agent_name": agent_name,
            "status": "failed" if has_error else "completed",
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": total_duration,
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "error_message": error_msg,
            "llm_calls": [
                {
                    "id": e["id"],
                    "provider": e.get("provider"),
                    "model": e.get("model"),
                    "prompt_tokens": e.get("prompt_tokens"),
                    "completion_tokens": e.get("completion_tokens"),
                    "total_tokens": e.get("total_tokens"),
                    "cost": e.get("cost"),
                    "duration_ms": e.get("duration_ms"),
                    "timestamp": e.get("timestamp"),
                }
                for e in llm_calls
            ],
            "tool_calls": [
                {
                    "id": e["id"],
                    "tool_name": e.get("tool_name"),
                    "duration_ms": e.get("duration_ms"),
                    "status": e.get("status"),
                    "error_message": e.get("error_message"),
                    "timestamp": e.get("timestamp"),
                }
                for e in tool_calls
            ],
        }

        try:
            resp = self._client.post(f"{self._endpoint}/api/traces", json=payload)
            if resp.status_code >= 400:
                logger.warning(
                    "AgentLens: failed to send trace (HTTP %d): %s",
                    resp.status_code,
                    resp.text[:200],
                )
        except Exception as exc:
            # Log but NEVER crash the developer's code
            logger.debug("AgentLens: failed to send trace: %s", exc)

    def _final_flush(self):
        """Called at program exit — send any remaining events."""
        self._running = False
        self._flush()

    def stop(self):
        """Stop the background thread."""
        self._running = False
