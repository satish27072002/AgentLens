"""
Example 2: Multi-Step Research Agent (no external API keys needed)

Simulates a research agent that:
1. Takes a user question
2. Searches the web
3. Reads relevant pages
4. Synthesizes an answer

Shows how a real multi-step agent would use the SDK.

Run:
    1. Start backend: cd backend && uvicorn app.main:app --reload
    2. Set your key:  export AGENTLENS_API_KEY=al_your_key_here
    3. Run this:      python examples/multi_step_agent.py

Get your AgentLens API key from the Settings page after logging in.
"""

import os
import sys
import time
import random
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

lens = AgentLens(api_key=API_KEY, endpoint=ENDPOINT, silent=False)


def simulate_research(query: str):
    """Simulate a multi-step research agent."""

    with lens.trace("ResearchAgent", metadata={"query": query}) as trace:
        print(f"\nResearch Agent | Query: '{query}'")
        print(f"   Execution ID: {trace.execution_id}")

        # Step 1: Plan the research approach
        time.sleep(0.1)
        trace.log_llm_call(
            provider="openai",
            model="gpt-4o",
            prompt_tokens=200,
            completion_tokens=150,
            cost=0.002,
            duration_ms=900,
        )
        print("   Step 1: Planned research approach (gpt-4o)")

        # Step 2: Search the web
        time.sleep(0.05)
        trace.log_tool_call(
            tool_name="web_search",
            duration_ms=random.randint(200, 800),
            status="success",
        )
        print("   Step 2: Searched the web")

        # Step 3: Read top 3 results
        for i in range(3):
            time.sleep(0.03)
            trace.log_tool_call(
                tool_name="read_webpage",
                duration_ms=random.randint(300, 1500),
                status="success",
            )
        print("   Step 3: Read 3 web pages")

        # Step 4: Synthesize answer
        time.sleep(0.15)
        trace.log_llm_call(
            provider="openai",
            model="gpt-4o",
            prompt_tokens=2000,
            completion_tokens=800,
            cost=0.013,
            duration_ms=2500,
        )
        print("   Step 4: Synthesized answer (gpt-4o)")

        # Step 5: Fact-check
        time.sleep(0.1)
        trace.log_llm_call(
            provider="anthropic",
            model="claude-3-5-sonnet",
            prompt_tokens=1500,
            completion_tokens=400,
            cost=0.0105,
            duration_ms=1800,
        )
        print("   Step 5: Fact-checked with Claude")

    print("   Research complete!")


# Run several research queries
queries = [
    "What are the latest advances in quantum computing?",
    "How does transformer architecture work in LLMs?",
    "Compare Kubernetes vs Docker Swarm for production",
]

print("Multi-Step Research Agent Demo")
print("=" * 50)

for query in queries:
    simulate_research(query)

print(f"\nDone! {len(queries)} research traces sent.")
print("Check your dashboard at http://localhost:5173")
