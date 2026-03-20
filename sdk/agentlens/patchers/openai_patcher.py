"""
OpenAI monkey-patcher — wraps openai.chat.completions.create to auto-capture telemetry.

How monkey-patching works:
1. We save a reference to the ORIGINAL function
2. We define a WRAPPER function that:
   a. Records the start time
   b. Calls the original function
   c. Extracts token usage from the response
   d. Records the event in the recorder
   e. Returns the original response (developer sees no difference)
3. We replace the original function with our wrapper

The developer's code calls what they THINK is openai's function,
but it's actually our wrapper. They get the same result — we just
also capture the metadata.
"""

import time
from typing import TYPE_CHECKING

from agentlens.pricing import calculate_cost

if TYPE_CHECKING:
    from agentlens.recorder import EventRecorder


def patch_openai(recorder: "EventRecorder") -> bool:
    """
    Patch OpenAI's chat completions create method (sync and async).

    Returns True if patching succeeded, False if openai isn't installed.
    """
    try:
        import openai
    except ImportError:
        return False

    # ── Patch sync: openai.chat.completions.create ──
    _patch_sync_create(openai, recorder)

    # ── Patch async: openai.AsyncOpenAI if available ──
    _patch_async_create(openai, recorder)

    return True


def _patch_sync_create(openai_module, recorder: "EventRecorder"):
    """Patch the synchronous OpenAI client's chat.completions.create."""
    original_init = openai_module.OpenAI.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # After the client is initialized, patch its create method
        original_create = self.chat.completions.create

        def tracked_create(*args, **kwargs):
            return _wrap_create(original_create, recorder, "openai", *args, **kwargs)

        self.chat.completions.create = tracked_create

    openai_module.OpenAI.__init__ = patched_init


def _patch_async_create(openai_module, recorder: "EventRecorder"):
    """Patch the async OpenAI client's chat.completions.create."""
    try:
        original_init = openai_module.AsyncOpenAI.__init__

        def patched_async_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            original_create = self.chat.completions.create

            async def tracked_async_create(*args, **kwargs):
                return await _wrap_async_create(original_create, recorder, "openai", *args, **kwargs)

            self.chat.completions.create = tracked_async_create

        openai_module.AsyncOpenAI.__init__ = patched_async_init
    except AttributeError:
        pass  # AsyncOpenAI not available


def _wrap_create(original_fn, recorder: "EventRecorder", provider: str, *args, **kwargs):
    """
    Wrapper for sync LLM calls.

    Key design:
    - try/finally ensures we record even if the call fails
    - We re-raise exceptions so the developer's error handling works
    - We extract usage from the response object
    """
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

        if response and hasattr(response, "usage") and response.usage:
            prompt_tokens = response.usage.prompt_tokens or 0
            completion_tokens = response.usage.completion_tokens or 0
            total_tokens = response.usage.total_tokens or 0

        cost = calculate_cost(model, prompt_tokens, completion_tokens)

        recorder.record_llm_call(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            duration_ms=duration_ms,
            error=error,
        )


async def _wrap_async_create(original_fn, recorder: "EventRecorder", provider: str, *args, **kwargs):
    """Wrapper for async LLM calls — same logic as sync."""
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
            prompt_tokens = response.usage.prompt_tokens or 0
            completion_tokens = response.usage.completion_tokens or 0
            total_tokens = response.usage.total_tokens or 0

        cost = calculate_cost(model, prompt_tokens, completion_tokens)

        recorder.record_llm_call(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            duration_ms=duration_ms,
            error=error,
        )
