"""
AgentLens SDK — Instrument your AI agents with observability.

Two modes of usage:

MODE 1: Auto-capture (recommended) — 1 line of setup
    from agentlens import AgentLens
    AgentLens.init(api_key="al_...")
    # All OpenAI/Anthropic calls are now automatically captured.

MODE 2: Manual logging — explicit control
    from agentlens import AgentLens
    lens = AgentLens(api_key="al_...")
    with lens.trace("MyAgent") as trace:
        trace.log_llm_call(provider="openai", model="gpt-4o", ...)
"""

from agentlens.client import AgentLens

__version__ = "0.2.0"
__all__ = ["AgentLens"]
