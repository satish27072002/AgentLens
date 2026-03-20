"""
AgentLens client — the main entry point for the SDK.

Supports two modes:

1. Auto-capture mode (AgentLens.init):
   - Monkey-patches OpenAI/Anthropic clients
   - Background thread sends events automatically
   - Developer writes ZERO logging code

2. Manual mode (AgentLens instance + trace context manager):
   - Developer explicitly logs LLM/tool calls
   - More control, works with any LLM provider
"""

import httpx
from agentlens.trace import Trace
from agentlens.recorder import EventRecorder
from agentlens.sender import BackgroundSender
from agentlens.patchers.openai_patcher import patch_openai
from agentlens.patchers.anthropic_patcher import patch_anthropic


class AgentLens:
    """
    Main SDK client.

    Two ways to use:

    AUTO-CAPTURE (recommended):
        AgentLens.init(api_key="al_...")
        # All OpenAI/Anthropic calls now automatically captured.

    MANUAL:
        lens = AgentLens(api_key="al_...")
        with lens.trace("MyAgent") as trace:
            trace.log_llm_call(...)
    """

    # Singleton instance for auto-capture mode
    _instance: "AgentLens | None" = None
    _recorder: EventRecorder | None = None
    _sender: BackgroundSender | None = None

    def __init__(
        self,
        api_key: str,
        endpoint: str = "http://localhost:8000",
        timeout: float = 10.0,
        silent: bool = True,
    ):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.silent = silent
        self._client = httpx.Client(
            timeout=timeout,
            headers={"X-API-Key": api_key},
        )

    # ──────────────────────────────────────────
    # Auto-capture mode (class methods)
    # ──────────────────────────────────────────

    @classmethod
    def init(
        cls,
        api_key: str,
        endpoint: str = "http://localhost:8000",
        flush_interval: float = 5.0,
    ) -> "AgentLens":
        """
        Initialize auto-capture mode.

        This does three things:
        1. Creates a singleton AgentLens instance
        2. Monkey-patches OpenAI and Anthropic clients
        3. Starts a background sender thread

        After calling this, all OpenAI/Anthropic calls are automatically
        captured and sent to the backend.

        Args:
            api_key: Your AgentLens API key (starts with "al_")
            endpoint: Backend URL
            flush_interval: Seconds between sending batches (default: 5)
        """
        instance = cls(api_key=api_key, endpoint=endpoint)
        cls._instance = instance

        # Create recorder and sender
        cls._recorder = EventRecorder()
        cls._sender = BackgroundSender(
            endpoint=endpoint,
            api_key=api_key,
            recorder=cls._recorder,
            flush_interval=flush_interval,
        )

        # Patch LLM clients
        patched = []
        if patch_openai(cls._recorder):
            patched.append("OpenAI")
        if patch_anthropic(cls._recorder):
            patched.append("Anthropic")

        if patched:
            providers = " + ".join(patched)
            print(f"[AgentLens] Auto-capture enabled for {providers}")
        else:
            print("[AgentLens] Warning: No LLM libraries found to patch. "
                  "Install 'openai' or 'anthropic' for auto-capture.")

        return instance

    @classmethod
    def execution(cls, agent_name: str = "default"):
        """
        Context manager for grouping LLM calls into an execution.

        Use when you want to group related calls together:

            AgentLens.init(api_key="al_...")

            with AgentLens.execution("ResearchAgent"):
                # All OpenAI calls here belong to one execution
                openai.chat.completions.create(...)
                openai.chat.completions.create(...)

            with AgentLens.execution("SummaryAgent"):
                # These belong to a different execution
                openai.chat.completions.create(...)
        """
        return _ExecutionContext(agent_name, cls._recorder)

    @classmethod
    def shutdown(cls):
        """Stop the background sender and flush remaining events."""
        if cls._sender:
            cls._sender.stop()
            cls._sender._final_flush()

    # ──────────────────────────────────────────
    # Manual mode (instance methods)
    # ──────────────────────────────────────────

    def trace(self, agent_name: str, metadata: dict | None = None) -> "Trace":
        """
        Create a new trace for manual logging.

        Use as a context manager:
            with lens.trace("MyAgent") as trace:
                trace.log_llm_call(...)
        """
        return Trace(
            agent_name=agent_name,
            metadata=metadata,
            client=self._client,
            endpoint=self.endpoint,
            silent=self.silent,
        )

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass


class _ExecutionContext:
    """
    Context manager for grouping auto-captured calls into an execution.

    Sets the agent name and execution ID on the recorder when entering,
    clears them when exiting. This way the background sender knows
    which calls belong together.
    """

    def __init__(self, agent_name: str, recorder: EventRecorder | None):
        self._agent_name = agent_name
        self._recorder = recorder

    def __enter__(self):
        if self._recorder:
            self._recorder.start_execution(self._agent_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._recorder:
            self._recorder.end_execution()
        return False
