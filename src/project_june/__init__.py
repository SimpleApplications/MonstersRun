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
from .aio import AsyncAgent, AsyncAutonomousAgent, AsyncOrchestrator
from .autonomous import AutonomousAgent, RunResult
from .config import AgentConfig
from .delegation import agent_tool
from .evals import (
    EvalCase,
    EvalReport,
    EvalResult,
    all_of,
    any_of,
    completed,
    contains,
    cost_under,
    is_json,
    matches,
    negate,
    run_eval,
    steps_under,
)
from .memory import MemoryStore, memory_tools
from .mcp_bridge import MCPProvider, MCPToolSpec, StaticMCPProvider, mcp_tools
from .orchestrator import Orchestrator, OrchestratorResult, Task, synthesize
from .tools import Tool, tool
from .tracing import save_run
from .usage import Usage

__all__ = [
    "Agent",
    "AsyncAgent",
    "AsyncAutonomousAgent",
    "AsyncOrchestrator",
    "AutonomousAgent",
    "RunResult",
    "AgentConfig",
    "MemoryStore",
    "memory_tools",
    "MCPProvider",
    "MCPToolSpec",
    "StaticMCPProvider",
    "mcp_tools",
    "Orchestrator",
    "OrchestratorResult",
    "Task",
    "synthesize",
    "save_run",
    "EvalCase",
    "EvalReport",
    "EvalResult",
    "run_eval",
    "contains",
    "completed",
    "all_of",
    "any_of",
    "negate",
    "matches",
    "is_json",
    "cost_under",
    "steps_under",
    "agent_tool",
    "Tool",
    "tool",
    "Usage",
]

__version__ = "0.1.0"
