"""
Example: Auto-Capture with Simulated OpenAI (NO API key needed)

Demonstrates how monkey-patching works by creating a mock OpenAI client
that returns fake responses. The patching mechanism is the same as with
the real OpenAI library.

Run:
    1. Start backend: cd backend && uvicorn app.main:app --reload
    2. Run this: python examples/auto_capture_simulated.py
"""

import os
import time
import httpx
from agentlens import AgentLens

# Setup: create/login demo user
print("Setting up demo user...")
BASE_URL = "http://localhost:8000"
r = httpx.post(f"{BASE_URL}/api/auth/signup", json={
    "email": "simulated@demo.com",
    "password": "demo1234",
    "name": "Simulated Demo",
})
if r.status_code == 200:
    API_KEY = r.json()["api_key"]
    TOKEN = r.json()["token"]
elif r.status_code == 409:
    r = httpx.post(f"{BASE_URL}/api/auth/login", json={
        "email": "simulated@demo.com", "password": "demo1234",
    })
    TOKEN = r.json()["token"]
    kr = httpx.post(f"{BASE_URL}/api/keys", json={"name": "sim-demo"},
                    headers={"Authorization": f"Bearer {TOKEN}"})
    API_KEY = kr.json()["key"]

print(f"API Key: {API_KEY[:12]}...")

# Initialize auto-capture with fast flush for demo
AgentLens.init(api_key=API_KEY, endpoint=BASE_URL, flush_interval=2)

# ── Simulate what happens when openai is installed and patched ──
# We'll use the manual recorder directly to simulate auto-captured events

recorder = AgentLens._recorder

print("\nSimulating auto-captured LLM calls...\n")

# Execution 1: Customer Support Agent
with AgentLens.execution("CustomerSupportAgent"):
    print("Execution 1: CustomerSupportAgent")

    # Simulate LLM call 1
    time.sleep(0.1)
    recorder.record_llm_call(
        provider="openai", model="gpt-4o-mini",
        prompt_tokens=150, completion_tokens=200, total_tokens=350,
        cost=0.0001, duration_ms=800,
    )
    print("  LLM call 1: gpt-4o-mini (350 tokens)")

    # Simulate tool call
    recorder.record_tool_call(
        tool_name="search_knowledge_base", duration_ms=250, status="success",
    )
    print("  Tool call: search_knowledge_base")

    # Simulate LLM call 2
    time.sleep(0.1)
    recorder.record_llm_call(
        provider="openai", model="gpt-4o-mini",
        prompt_tokens=500, completion_tokens=300, total_tokens=800,
        cost=0.0003, duration_ms=1100,
    )
    print("  LLM call 2: gpt-4o-mini (800 tokens)")

# Execution 2: Research Agent
with AgentLens.execution("ResearchAgent"):
    print("\nExecution 2: ResearchAgent")

    recorder.record_llm_call(
        provider="openai", model="gpt-4o",
        prompt_tokens=200, completion_tokens=150, total_tokens=350,
        cost=0.002, duration_ms=1500,
    )
    print("  LLM call 1: gpt-4o (planning)")

    recorder.record_tool_call(
        tool_name="web_search", duration_ms=600, status="success",
    )
    print("  Tool call: web_search")

    recorder.record_llm_call(
        provider="anthropic", model="claude-3-5-sonnet-20241022",
        prompt_tokens=2000, completion_tokens=800, total_tokens=2800,
        cost=0.018, duration_ms=3000,
    )
    print("  LLM call 2: claude-3-5-sonnet (synthesis)")

print("\nWaiting for background sender to flush (3 seconds)...")
time.sleep(3)
AgentLens.shutdown()

# Verify data arrived
print("\nVerifying data in backend...")
stats = httpx.get(f"{BASE_URL}/api/stats",
                  headers={"Authorization": f"Bearer {TOKEN}"}).json()
print(f"  Total executions: {stats['total_executions']}")
print(f"  Total cost: ${stats['total_cost']:.4f}")
print(f"  Success rate: {stats['success_rate']}%")

print("\nDone! Auto-capture pipeline working.")
