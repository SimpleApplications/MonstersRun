"""claude_agents — a small, flexible framework for building AI agents on Claude.

Public API:
    Agent       — the agentic loop (Claude + tools, runs until done).
    AgentConfig — model / system-prompt / effort configuration.
    tool        — decorator that turns a plain function into an agent tool.
    Tool        — the wrapper produced by @tool (rarely constructed directly).
"""

from .agent import Agent
from .config import AgentConfig
from .tools import Tool, tool

__all__ = ["Agent", "AgentConfig", "Tool", "tool"]
