"""Independent (autonomous) agents.

An `AutonomousAgent` is given a *goal* rather than a single prompt. It works
toward that goal across as many model turns as it needs, calling tools along the
way, and decides for itself when the goal is done by calling a built-in
`complete_task` tool. A step budget bounds the run so an agent can't spin forever.

This is the "independent agent" surface of Project June: hand it a goal and a set
of tools, and let it drive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import anthropic

from .agent import Agent
from .config import AgentConfig
from .tools import Tool, tool
from .usage import Usage

# Called after each model turn: (step_number, response) -> None.
StepHook = Callable[[int, Any], None]

_GOAL_PROMPT = (
    "Your goal:\n{goal}\n\n"
    "Work toward this goal independently. Use the available tools as needed. "
    "When — and only when — the goal is fully accomplished, call the "
    "`complete_task` tool with a clear summary of the outcome. Do not ask for "
    "confirmation; proceed and finish the work yourself."
)

_NUDGE = (
    "You ended your turn without calling `complete_task`. If the goal is fully "
    "accomplished, call `complete_task` now with a summary. Otherwise, keep "
    "working toward it."
)


@dataclass
class RunResult:
    """The outcome of an autonomous run."""

    completed: bool  # True if the agent called complete_task
    result: str  # the agent's final summary (or last text if it ran out of steps)
    steps: int  # number of model turns taken
    transcript: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""

    @property
    def cost(self) -> float:
        """Estimated USD cost of the run."""
        return self.usage.cost(self.model)


class AutonomousAgent:
    def __init__(
        self,
        tools: Iterable[Tool] | None = None,
        config: AgentConfig | None = None,
        client: anthropic.Anthropic | None = None,
        on_tool: Callable[[str, dict[str, Any], str], None] | None = None,
        on_step: StepHook | None = None,
    ) -> None:
        self._final: str | None = None

        # The agent signals completion by calling this tool. The closure captures
        # the summary so the run loop can detect that the goal is done.
        @tool
        def complete_task(summary: str) -> str:
            """Call this once the goal is fully accomplished.

            Args:
                summary: A clear summary of what was accomplished and the result.
            """
            self._final = summary
            return "Task marked complete."

        all_tools: list[Tool] = list(tools or []) + [complete_task]
        self.agent = Agent(
            tools=all_tools,
            config=config or AgentConfig(),
            client=client,
            on_tool=on_tool,
        )
        self.on_step = on_step

    def run(self, goal: str, max_steps: int = 12) -> RunResult:
        """Pursue `goal` independently, up to `max_steps` model turns.

        Each call is independent: the conversation and usage are reset so the
        returned `RunResult` reflects only this run. (Reuse the instance freely.)
        """
        self._final = None
        agent = self.agent
        # Fresh conversation + accounting per run — reuse must not leak prior state.
        agent.messages = []
        agent.usage = Usage()
        agent.messages.append({"role": "user", "content": _GOAL_PROMPT.format(goal=goal)})

        steps = 0
        while steps < max_steps and self._final is None:
            response = agent.client.messages.create(**agent._request_kwargs())
            agent.usage.add(getattr(response, "usage", None))
            steps += 1

            if response.stop_reason == "refusal":
                detail = getattr(response, "stop_details", None)
                category = getattr(detail, "category", None)
                return self._result(
                    completed=False,
                    result=f"[refused] Request declined (category: {category}).",
                    steps=steps,
                )

            agent.messages.append({"role": "assistant", "content": response.content})
            if self.on_step:
                self.on_step(steps, response)

            # Let a paused server-side tool resume without a user message.
            if response.stop_reason == "pause_turn":
                continue

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if tool_uses:
                results = [agent._execute(b) for b in tool_uses]
                agent.messages.append({"role": "user", "content": results})
            elif self._final is None:
                # Ended a turn without finishing — nudge it onward.
                agent.messages.append({"role": "user", "content": _NUDGE})

        completed = self._final is not None
        result = self._final if completed else _last_text(agent.messages)
        return self._result(completed, result, steps)

    def _result(self, completed: bool, result: str, steps: int) -> RunResult:
        return RunResult(
            completed=completed,
            result=result,
            steps=steps,
            transcript=self.agent.messages,
            usage=self.agent.usage,
            model=self.agent.config.model,
        )


def _last_text(messages: list[dict[str, Any]]) -> str:
    """Best-effort extraction of the most recent assistant text."""
    for msg in reversed(messages):
        if msg["role"] != "assistant":
            continue
        content = msg["content"]
        if isinstance(content, str):
            return content
        text = "".join(
            getattr(b, "text", "") for b in content if getattr(b, "type", "") == "text"
        )
        if text.strip():
            return text.strip()
    return "[no final answer produced]"
