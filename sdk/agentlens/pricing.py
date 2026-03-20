"""
Model pricing lookup — calculates cost from token usage.

Prices are per 1K tokens. Update periodically as providers change pricing.
If a model isn't in the table, cost returns 0 (safe default).
"""

# Prices per 1K tokens (as of early 2026)
MODEL_PRICING: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "o1": {"input": 0.015, "output": 0.06},
    "o1-mini": {"input": 0.003, "output": 0.012},
    # Anthropic
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculate the cost of an LLM call based on model and token counts.

    Returns 0.0 if the model isn't in the pricing table.
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        # Try partial match (e.g., "gpt-4o-2024-08-06" → "gpt-4o")
        for known_model, prices in MODEL_PRICING.items():
            if model and model.startswith(known_model):
                pricing = prices
                break

    if not pricing:
        return 0.0

    input_cost = (prompt_tokens / 1000) * pricing["input"]
    output_cost = (completion_tokens / 1000) * pricing["output"]
    return round(input_cost + output_cost, 6)
