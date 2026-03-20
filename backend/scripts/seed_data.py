"""
Seed Data Generator for AgentLens.

Generates 75 realistic-looking agent executions across 5 different agents,
spread over the last 30 days. Each execution has realistic LLM calls and
tool calls with varied costs, durations, and success/failure rates.

Usage:
    python scripts/seed_data.py                    # default: localhost:8000
    python scripts/seed_data.py http://your-url    # custom backend URL

What it creates:
    - 75 executions across 5 agent types
    - ~120 LLM calls (some executions have multiple)
    - ~90 tool calls
    - ~10% failure rate (realistic)
    - Data spread over last 30 days
"""

import sys
import uuid
import random
import httpx
from datetime import datetime, timedelta, timezone

# ─────────────────────────────────────
# Configuration
# ─────────────────────────────────────

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
NUM_EXECUTIONS = 75

# Agent definitions — each has realistic characteristics
AGENTS = [
    {
        "name": "CustomerSupportAgent",
        "models": ["gpt-4o-mini", "gpt-4o"],
        "tools": ["search_knowledge_base", "get_customer_info", "create_ticket"],
        "avg_duration_ms": 4000,
        "avg_cost": 0.008,
        "failure_rate": 0.08,       # 8% fail
        "llm_calls_range": (1, 3),  # 1-3 LLM calls per execution
        "tool_calls_range": (1, 3),
        "weight": 30,               # 30% of executions
    },
    {
        "name": "ResearchAgent",
        "models": ["gpt-4o", "claude-3-5-sonnet"],
        "tools": ["web_search", "arxiv_search", "summarize_paper"],
        "avg_duration_ms": 12000,
        "avg_cost": 0.035,
        "failure_rate": 0.12,
        "llm_calls_range": (2, 5),
        "tool_calls_range": (2, 4),
        "weight": 20,
    },
    {
        "name": "CodeReviewAgent",
        "models": ["gpt-4o", "claude-3-5-sonnet"],
        "tools": ["git_diff", "run_linter", "run_tests", "post_comment"],
        "avg_duration_ms": 8000,
        "avg_cost": 0.02,
        "failure_rate": 0.05,
        "llm_calls_range": (1, 3),
        "tool_calls_range": (2, 4),
        "weight": 20,
    },
    {
        "name": "DataPipelineAgent",
        "models": ["gpt-4o-mini"],
        "tools": ["query_database", "transform_data", "upload_s3"],
        "avg_duration_ms": 6000,
        "avg_cost": 0.004,
        "failure_rate": 0.15,       # pipelines fail more often
        "llm_calls_range": (1, 2),
        "tool_calls_range": (1, 3),
        "weight": 15,
    },
    {
        "name": "EmailDraftAgent",
        "models": ["gpt-4o-mini"],
        "tools": ["get_context", "draft_email", "send_email"],
        "avg_duration_ms": 3000,
        "avg_cost": 0.003,
        "failure_rate": 0.03,
        "llm_calls_range": (1, 2),
        "tool_calls_range": (1, 2),
        "weight": 15,
    },
]

# Error messages for failed executions
ERROR_MESSAGES = [
    "OpenAI API rate limit exceeded (429)",
    "Request timeout after 30000ms",
    "Context length exceeded: 128000 tokens",
    "Invalid API key or expired token",
    "Connection refused: upstream service unavailable",
    "JSONDecodeError: Unexpected token in response",
    "Tool 'search_database' returned empty result set",
    "Max retries (3) exceeded for LLM call",
]

# LLM pricing (approximate cost per 1K tokens)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
}


# ─────────────────────────────────────
# Data generation
# ─────────────────────────────────────

def pick_agent() -> dict:
    """Weighted random agent selection."""
    weights = [a["weight"] for a in AGENTS]
    return random.choices(AGENTS, weights=weights, k=1)[0]


def random_timestamp(days_back: int = 30) -> datetime:
    """Random datetime within the last N days, biased toward recent."""
    # Use exponential distribution to bias toward recent dates
    days_ago = min(random.expovariate(0.1), days_back)
    hours = random.uniform(8, 22)  # Business hours mostly
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return base.replace(hour=int(hours), minute=random.randint(0, 59),
                        second=random.randint(0, 59), microsecond=0)


def vary(value: float, variance: float = 0.4) -> float:
    """Add realistic variance to a value (±40% by default)."""
    factor = random.uniform(1 - variance, 1 + variance)
    return max(0, value * factor)


def generate_llm_call(agent: dict, timestamp: datetime) -> dict:
    """Generate a single realistic LLM call."""
    model = random.choice(agent["models"])
    pricing = MODEL_PRICING[model]

    prompt_tokens = random.randint(100, 2000)
    completion_tokens = random.randint(50, 1500)
    total_tokens = prompt_tokens + completion_tokens

    cost = (prompt_tokens / 1000 * pricing["input"] +
            completion_tokens / 1000 * pricing["output"])

    duration_ms = random.randint(500, 5000)

    return {
        "id": str(uuid.uuid4()),
        "provider": "openai" if "gpt" in model else "anthropic",
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost": round(cost, 6),
        "duration_ms": duration_ms,
        "timestamp": (timestamp + timedelta(milliseconds=random.randint(100, 2000))).isoformat(),
    }


def generate_tool_call(agent: dict, timestamp: datetime) -> dict:
    """Generate a single realistic tool call."""
    tool_name = random.choice(agent["tools"])
    is_error = random.random() < 0.05  # 5% of tool calls fail

    return {
        "id": str(uuid.uuid4()),
        "tool_name": tool_name,
        "duration_ms": random.randint(50, 3000),
        "status": "error" if is_error else "success",
        "error_message": "Tool execution failed: timeout" if is_error else None,
        "timestamp": (timestamp + timedelta(milliseconds=random.randint(100, 3000))).isoformat(),
    }


def generate_execution() -> dict:
    """Generate a complete execution with LLM and tool calls."""
    agent = pick_agent()
    started_at = random_timestamp()
    is_failed = random.random() < agent["failure_rate"]

    duration_ms = int(vary(agent["avg_duration_ms"]))
    completed_at = started_at + timedelta(milliseconds=duration_ms)

    # Generate LLM calls
    num_llm = random.randint(*agent["llm_calls_range"])
    llm_calls = [generate_llm_call(agent, started_at) for _ in range(num_llm)]

    # Generate tool calls
    num_tools = random.randint(*agent["tool_calls_range"])
    tool_calls = [generate_tool_call(agent, started_at) for _ in range(num_tools)]

    total_cost = sum(c["cost"] for c in llm_calls)
    total_tokens = sum(c["total_tokens"] for c in llm_calls)

    return {
        "id": str(uuid.uuid4()),
        "agent_name": agent["name"],
        "status": "failed" if is_failed else "completed",
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_ms": duration_ms,
        "total_cost": round(total_cost, 6),
        "total_tokens": total_tokens,
        "error_message": random.choice(ERROR_MESSAGES) if is_failed else None,
        "llm_calls": llm_calls,
        "tool_calls": tool_calls,
    }


# ─────────────────────────────────────
# Main
# ─────────────────────────────────────

def create_demo_user() -> tuple[str, str]:
    """Create a demo user account and return (jwt_token, api_key)."""
    DEMO_EMAIL = "demo@agentlens.dev"
    DEMO_PASSWORD = "demo1234"
    DEMO_NAME = "Demo User"

    # Try signup first
    r = httpx.post(f"{BASE_URL}/api/auth/signup", json={
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "name": DEMO_NAME,
    }, timeout=10)

    if r.status_code == 200:
        data = r.json()
        print(f"  Created demo user: {DEMO_EMAIL}")
        return data["token"], data["api_key"]

    # If user already exists, log in
    if r.status_code == 409:
        r = httpx.post(f"{BASE_URL}/api/auth/login", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
        }, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"  Demo user already exists, logged in")
            # We need an API key — list existing ones via the /api/keys endpoint
            keys_r = httpx.get(f"{BASE_URL}/api/keys", headers={
                "Authorization": f"Bearer {data['token']}",
            }, timeout=10)
            if keys_r.status_code == 200 and keys_r.json():
                # We can't get the full key from listing, so generate a new one
                new_key_r = httpx.post(f"{BASE_URL}/api/keys", json={"name": "Seed Script"}, headers={
                    "Authorization": f"Bearer {data['token']}",
                }, timeout=10)
                if new_key_r.status_code == 201:
                    return data["token"], new_key_r.json()["key"]

    print(f"ERROR: Failed to create/login demo user: {r.status_code} {r.text}")
    sys.exit(1)


def main():
    print(f"AgentLens Seed Data Generator")
    print(f"Target: {BASE_URL}")
    print(f"Generating {NUM_EXECUTIONS} executions...")
    print()

    # Check backend is reachable
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"ERROR: Backend returned {r.status_code}. Is the server running?")
            sys.exit(1)
    except httpx.ConnectError:
        print(f"ERROR: Cannot connect to {BASE_URL}. Start the server first:")
        print(f"  cd backend && uvicorn app.main:app --reload")
        sys.exit(1)

    # Create demo user and get API key
    token, api_key = create_demo_user()
    headers = {"X-API-Key": api_key}
    print(f"  API Key: {api_key[:12]}...")
    print()

    success = 0
    failed = 0
    total_cost = 0.0

    for i in range(NUM_EXECUTIONS):
        execution = generate_execution()
        r = httpx.post(f"{BASE_URL}/api/traces", json=execution, headers=headers, timeout=10)

        if r.status_code == 201:
            success += 1
            total_cost += execution["total_cost"]
            status_icon = "✅" if execution["status"] == "completed" else "❌"
            print(f"  {status_icon} [{i+1}/{NUM_EXECUTIONS}] {execution['agent_name']}"
                  f" | ${execution['total_cost']:.4f}"
                  f" | {execution['duration_ms']}ms"
                  f" | {execution['status']}")
        else:
            failed += 1
            print(f"  ⚠️  [{i+1}/{NUM_EXECUTIONS}] HTTP {r.status_code}: {r.text}")

    print()
    print(f"═══════════════════════════════════════")
    print(f"  Seed complete: {success} created, {failed} errors")
    print(f"  Total simulated cost: ${total_cost:.4f}")
    print(f"═══════════════════════════════════════")
    print()
    print(f"Demo login credentials:")
    print(f"  Email:    demo@agentlens.dev")
    print(f"  Password: demo1234")
    print()
    print(f"View your data:")
    print(f"  Dashboard:  {BASE_URL}/docs")
    print(f"  Stats:      curl -H 'Authorization: Bearer {token[:20]}...' {BASE_URL}/api/stats")


if __name__ == "__main__":
    main()
