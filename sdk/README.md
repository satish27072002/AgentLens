# AgentLens SDK

Open-source observability SDK for AI agents. See what your agents actually do.

## Installation

```bash
pip install -e ./sdk
```

## Quick Start

```python
from agentlens import AgentLens

lens = AgentLens(endpoint="http://localhost:8000")

with lens.trace("MyAgent") as trace:
    # Your agent logic here...

    # Log LLM calls
    trace.log_llm_call(
        provider="openai",
        model="gpt-4o",
        prompt_tokens=200,
        completion_tokens=150,
        cost=0.003,
        duration_ms=1200,
    )

    # Log tool calls
    trace.log_tool_call(
        tool_name="search_database",
        duration_ms=350,
        status="success",
    )

# Data is automatically sent when the `with` block exits.
```

## Error Handling

Errors in your agent are captured automatically:

```python
with lens.trace("MyAgent") as trace:
    raise ValueError("Something went wrong")
# Trace is sent with status="failed" and the error message
```

You can also mark failures manually:

```python
with lens.trace("MyAgent") as trace:
    result = do_something()
    if not result:
        trace.set_error("No results found")
```
