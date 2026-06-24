"""Configuration for an Agent.

Kept deliberately small: the values here are the ones worth tuning per use case.
Everything else uses sensible Claude defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

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
    """

    model: str = DEFAULT_MODEL
    system: str | None = None
    max_tokens: int = 16_000
    effort: str = "high"
    thinking: bool = True
    max_iterations: int = 25
    cache: bool = True
