"""
Example 2: Multi-Step Research Agent (no API keys needed)

Simulates a research agent that:
1. Takes a user question
2. Searches the web
3. Reads relevant pages
4. Synthesizes an answer

Shows how a real multi-step agent would use the SDK.

Run:
    1. Start backend: cd backend && uvicorn app.main:app --reload
    2. Run this:      python examples/multi_step_agent.py
"""

import time
import random
from agentlens import AgentLens

lens = AgentLens(endpoint="http://localhost:8000", silent=False)


def simulate_research(query: str):
    """Simulate a multi-step research agent."""

    with lens.trace("ResearchAgent", metadata={"query": query}) as trace:
        print(f"\n📖 Research Agent | Query: '{query}'")
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

    print("   ✅ Research complete!")


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

print(f"\nDone! {len(queries)} research traces sent to AgentLens.")
print("Check: http://localhost:8000/api/executions")
