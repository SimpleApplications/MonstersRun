"""Project June — a framework for building independent (autonomous) Claude agents.

Public API:
    Agent           — the core agentic loop (Claude + tools, one turn to done).
    AutonomousAgent — an agent that pursues a goal independently across turns,
                      deciding for itself when the goal is complete.
    AgentConfig     — model / system-prompt / effort configuration.
    tool            — decorator that turns a plain function into an agent tool.
    Tool            — the wrapper produced by @tool.
"""

from .agent import Agent
from .autonomous import AutonomousAgent, RunResult
from .config import AgentConfig
from .tools import Tool, tool

__all__ = [
    "Agent",
    "AutonomousAgent",
    "RunResult",
    "AgentConfig",
    "Tool",
    "tool",
]

__version__ = "0.1.0"
