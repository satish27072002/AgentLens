"""
Example 1: Simple Agent (no API keys needed)

Simulates an agent that makes LLM calls and tool calls.
Shows the basic SDK usage pattern.

Run:
    1. Start backend: cd backend && uvicorn app.main:app --reload
    2. Run this:      python examples/simple_agent.py
    3. Check data:    curl http://localhost:8000/api/stats
"""

import time
from agentlens import AgentLens

# Connect to the backend
lens = AgentLens(endpoint="http://localhost:8000", silent=False)

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

print("✅ Execution 1 sent successfully!\n")

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
    print("❌ Execution 2 failed (error captured in trace)\n")

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
    print("⚠️  Execution 3 marked as failed manually\n")

print("Done! Check your data:")
print("  Stats:      http://localhost:8000/api/stats")
print("  Executions: http://localhost:8000/api/executions")
