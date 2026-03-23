"""
Example: Auto-Capture with Simulated OpenAI (NO OpenAI API key needed)

Demonstrates how monkey-patching works by using the manual recorder
to simulate auto-captured events. No external API keys required.

Run:
    1. Start backend: cd backend && uvicorn app.main:app --reload
    2. Set your AgentLens key: export AGENTLENS_API_KEY=al_your_key_here
    3. Run this: python examples/auto_capture_simulated.py

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

BASE_URL = os.getenv("AGENTLENS_ENDPOINT", "http://localhost:8000")

# Initialize auto-capture with fast flush for demo
AgentLens.init(api_key=API_KEY, endpoint=BASE_URL, flush_interval=2)

# Use the manual recorder to simulate auto-captured events
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

print("\nDone! Check your AgentLens dashboard at http://localhost:5173")
