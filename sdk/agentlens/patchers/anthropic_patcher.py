"""
Anthropic monkey-patcher — wraps anthropic.messages.create to auto-capture telemetry.

Same pattern as the OpenAI patcher, but adapted for Anthropic's different
response structure (input_tokens/output_tokens instead of prompt_tokens/completion_tokens).
"""

import time
from typing import TYPE_CHECKING

from agentlens.pricing import calculate_cost

if TYPE_CHECKING:
    from agentlens.recorder import EventRecorder


def patch_anthropic(recorder: "EventRecorder") -> bool:
    """
    Patch Anthropic's messages.create method.

    Returns True if patching succeeded, False if anthropic isn't installed.
    """
    try:
        import anthropic
    except ImportError:
        return False

    # Patch sync client
    original_init = anthropic.Anthropic.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        original_create = self.messages.create

        def tracked_create(*args, **kwargs):
            return _wrap_create(original_create, recorder, *args, **kwargs)

        self.messages.create = tracked_create

    anthropic.Anthropic.__init__ = patched_init

    # Patch async client
    try:
        original_async_init = anthropic.AsyncAnthropic.__init__

        def patched_async_init(self, *args, **kwargs):
            original_async_init(self, *args, **kwargs)
            original_create = self.messages.create

            async def tracked_async_create(*args, **kwargs):
                return await _wrap_async_create(original_create, recorder, *args, **kwargs)

            self.messages.create = tracked_async_create

        anthropic.AsyncAnthropic.__init__ = patched_async_init
    except AttributeError:
        pass

    return True


def _wrap_create(original_fn, recorder: "EventRecorder", *args, **kwargs):
    """Wrapper for sync Anthropic calls."""
    start = time.monotonic()
    model = kwargs.get("model", "unknown")
    error = None
    response = None

    try:
        response = original_fn(*args, **kwargs)
        return response
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        # Anthropic uses .usage.input_tokens / .usage.output_tokens
        if response and hasattr(response, "usage") and response.usage:
            prompt_tokens = getattr(response.usage, "input_tokens", 0) or 0
            completion_tokens = getattr(response.usage, "output_tokens", 0) or 0
            total_tokens = prompt_tokens + completion_tokens

        cost = calculate_cost(model, prompt_tokens, completion_tokens)

        recorder.record_llm_call(
            provider="anthropic",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            duration_ms=duration_ms,
            error=error,
        )


async def _wrap_async_create(original_fn, recorder: "EventRecorder", *args, **kwargs):
    """Wrapper for async Anthropic calls."""
    start = time.monotonic()
    model = kwargs.get("model", "unknown")
    error = None
    response = None

    try:
        response = await original_fn(*args, **kwargs)
        return response
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        raise
    finally:
        duration_ms = int((time.monotonic() - start) * 1000)

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if response and hasattr(response, "usage") and response.usage:
            prompt_tokens = getattr(response.usage, "input_tokens", 0) or 0
            completion_tokens = getattr(response.usage, "output_tokens", 0) or 0
            total_tokens = prompt_tokens + completion_tokens

        cost = calculate_cost(model, prompt_tokens, completion_tokens)

        recorder.record_llm_call(
            provider="anthropic",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            duration_ms=duration_ms,
            error=error,
        )
