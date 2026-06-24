"""Agent-as-tool: let an agent delegate subtasks to independent sub-agents.

`agent_tool(...)` returns a `Tool` that, when called, spins up a fresh
`AutonomousAgent` to pursue the delegated task and returns its result. Give that
tool to an outer agent and you get hierarchical, independent agents: a coordinator
that farms specialized subtasks out to focused workers, each with its own tools
and context.

    researcher = agent_tool(
        "research", "Delegate a research question to a focused sub-agent.",
        tools=[web_search],
    )
    coordinator = Agent(tools=[researcher, ...])
"""

from __future__ import annotations

from typing import Any

import anthropic

from .autonomous import AutonomousAgent
from .config import AgentConfig
from .tools import Tool


def agent_tool(
    name: str,
    description: str,
    tools: list[Tool] | None = None,
    config: AgentConfig | None = None,
    client: anthropic.Anthropic | None = None,
    max_steps: int = 8,
    param: str = "task",
) -> Tool:
    """Build a Tool that delegates its input to a fresh AutonomousAgent.

    Args:
        name: The tool name the outer agent sees.
        description: What this sub-agent is good for (the outer agent reads this
            to decide when to delegate).
        tools: Tools available to the sub-agent.
        config: Config for the sub-agent (defaults to AgentConfig()).
        client: Shared Anthropic client (recommended; reuses the connection pool).
        max_steps: Step budget for each delegated run.
        param: The name of the single string input (default "task").
    """
    sub_tools = list(tools or [])

    def call(**kwargs: Any) -> str:
        task = kwargs.get(param, "")
        sub = AutonomousAgent(tools=sub_tools, config=config, client=client)
        result = sub.run(task, max_steps=max_steps)
        if not result.completed:
            return f"[sub-agent did not complete in {result.steps} steps] {result.result}"
        return result.result

    schema = {
        "type": "object",
        "properties": {
            param: {"type": "string", "description": "The subtask to delegate."}
        },
        "required": [param],
        "additionalProperties": False,
    }
    return Tool(name=name, description=description, input_schema=schema, func=call)
