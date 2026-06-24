"""Configuration for an Agent.

Kept deliberately small: the values here are the ones worth tuning per use case.
Everything else uses sensible Claude defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# Default to the most capable Opus-tier model. Override with CLAUDE_AGENT_MODEL
# or by passing model=... to AgentConfig.
DEFAULT_MODEL = os.environ.get("CLAUDE_AGENT_MODEL", "claude-opus-4-8")


@dataclass
class AgentConfig:
    """Tunable knobs for an Agent.

    Attributes:
        model: Claude model id. Defaults to claude-opus-4-8.
        system: System prompt — defines the agent's role and behavior.
        max_tokens: Per-response output cap. 16k is a safe non-streaming default.
        effort: Reasoning depth / token spend: "low" | "medium" | "high" | "max".
            "high" is the usual sweet spot for agentic work.
        thinking: When True, enable adaptive thinking (Claude decides how much to
            think per turn). The recommended mode for capable models.
        max_iterations: Safety bound on the tool-use loop so a misbehaving agent
            can't loop forever.
        cache: When True, cache the tools + system prefix (prompt caching) so
            multi-turn loops pay the prefix cost once. Cheap and almost always
            worth it for agentic loops.
        max_context_tokens: If set, compact the message history to stay under this
            estimated token budget on long runs (drops the oldest exchanges,
            keeps the task + recent turns). None disables compaction.
        max_retries: How many times the SDK retries transient errors (429/500/
            overloaded) with exponential backoff before giving up.
        request_timeout: Per-request timeout in seconds (None = SDK default).
        server_tools: Raw Anthropic server-tool specs to include in every request
            (e.g. {"type": "web_search_20260209", "name": "web_search"}). These
            run server-side; the agent loop never executes them locally.
    """

    model: str = DEFAULT_MODEL
    system: str | None = None
    max_tokens: int = 16_000
    effort: str = "high"
    thinking: bool = True
    max_iterations: int = 25
    cache: bool = True
    max_context_tokens: int | None = None
    max_retries: int = 4
    request_timeout: float | None = None
    server_tools: list[dict[str, Any]] = field(default_factory=list)

    def client_kwargs(self) -> dict:
        """Constructor kwargs for the Anthropic client (retries/timeout)."""
        kwargs: dict = {"max_retries": self.max_retries}
        if self.request_timeout is not None:
            kwargs["timeout"] = self.request_timeout
        return kwargs
