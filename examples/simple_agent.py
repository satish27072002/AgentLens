"""
Example 1: Simple Agent (no external API keys needed)

Simulates an agent that makes LLM calls and tool calls.
Shows the basic SDK usage pattern.

Run:
    1. Start backend: cd backend && uvicorn app.main:app --reload
    2. Set your key:  export AGENTLENS_API_KEY=al_your_key_here
    3. Run this:      python examples/simple_agent.py

Get your AgentLens API key from the Settings page after logging in.
"""

import os
import sys
import time
from agentlens import AgentLens

# Get API key from environment
API_KEY = os.getenv("AGENTLENS_API_KEY", "")
if not API_KEY:
    print("Error: AGENTLENS_API_KEY not set.")
    print("  1. Log into the AgentLens dashboard")
    print("  2. Go to Settings → Create API Key")
    print("  3. Run: export AGENTLENS_API_KEY=al_your_key_here")
    sys.exit(1)

ENDPOINT = os.getenv("AGENTLENS_ENDPOINT", "http://localhost:8000")

# Connect to the backend
lens = AgentLens(api_key=API_KEY, endpoint=ENDPOINT, silent=False)

print("Running simple agent with AgentLens tracing...\n")

# ─── Execution 1: Successful agent run ───
with lens.trace("SimpleAgent") as trace:
    print(f"Execution ID: {trace.execution_id}")

    # Simulate an LLM call
    time.sleep(0.1)  # Pretend this takes time
    trace.log_llm_call(
        provider="openai",
        model="gpt-4o-mini",
        prompt_tokens=150,
        completion_tokens=200,
        cost=0.002,
        duration_ms=800,
    )
    print("  Logged LLM call: gpt-4o-mini")

    # Simulate a tool call
    time.sleep(0.05)
    trace.log_tool_call(
        tool_name="search_knowledge_base",
        duration_ms=250,
        status="success",
    )
    print("  Logged tool call: search_knowledge_base")

    # Simulate a second LLM call (using search results)
    time.sleep(0.1)
    trace.log_llm_call(
        provider="openai",
        model="gpt-4o-mini",
        prompt_tokens=400,
        completion_tokens=300,
        cost=0.004,
        duration_ms=1100,
    )
    print("  Logged LLM call: gpt-4o-mini (with context)")

print("Execution 1 sent successfully!\n")

# ─── Execution 2: Failed agent run ───
print("Running a failing agent...")
try:
    with lens.trace("SimpleAgent") as trace:
        trace.log_llm_call(
            provider="openai",
            model="gpt-4o",
            prompt_tokens=100,
            completion_tokens=50,
            cost=0.001,
            duration_ms=500,
        )
        # Simulate an error
        raise ValueError("API returned unexpected format")
except ValueError:
    print("Execution 2 failed (error captured in trace)\n")

# ─── Execution 3: Manual error marking ───
with lens.trace("SimpleAgent", metadata={"version": "1.2", "environment": "staging"}) as trace:
    trace.log_llm_call(
        provider="anthropic",
        model="claude-3-5-sonnet",
        prompt_tokens=300,
        completion_tokens=0,
        cost=0.0009,
        duration_ms=2000,
    )
    # Mark as failed without raising an exception
    trace.set_error("LLM returned empty response after 3 retries")
    print("Execution 3 marked as failed manually\n")

print("Done! Check your dashboard at http://localhost:5173")
