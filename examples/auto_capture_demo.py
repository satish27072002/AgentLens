"""
Example: Auto-Capture Demo (requires openai package + API key)

Shows the "2 lines of code" experience:
1. AgentLens.init(api_key="...")
2. Make OpenAI calls as normal — everything is automatically captured.

Run:
    1. Start backend: cd backend && uvicorn app.main:app --reload
    2. Set your keys:
         export AGENTLENS_API_KEY=al_your_key_here
         export OPENAI_API_KEY=sk-...
    3. Run this: python examples/auto_capture_demo.py

Get your AgentLens API key from the Settings page after logging in.
If you don't have an OpenAI API key, use examples/auto_capture_simulated.py instead.
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

# ════════════════════════════════════════════
#  THIS IS ALL THE DEVELOPER NEEDS TO ADD:
# ════════════════════════════════════════════
AgentLens.init(api_key=API_KEY, endpoint="http://localhost:8000", flush_interval=2)
# ════════════════════════════════════════════

# Now use OpenAI as normal — AgentLens captures everything automatically
import openai

client = openai.OpenAI()

print("\nMaking OpenAI calls (auto-captured by AgentLens)...\n")

# Group calls into an execution
with AgentLens.execution("ResearchAgent"):
    # Call 1: Plan the research
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What are 3 key trends in AI for 2026? Be brief."}],
        max_tokens=200,
    )
    print(f"Call 1 response: {response.choices[0].message.content[:100]}...")
    print(f"  Tokens: {response.usage.total_tokens}")

    # Call 2: Summarize
    response2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Summarize this in one sentence: " + response.choices[0].message.content},
        ],
        max_tokens=100,
    )
    print(f"Call 2 response: {response2.choices[0].message.content[:100]}...")
    print(f"  Tokens: {response2.usage.total_tokens}")

print("\nWaiting for background sender to flush (3 seconds)...")
time.sleep(3)
AgentLens.shutdown()

print("\nDone! Check your AgentLens dashboard at http://localhost:5173")
