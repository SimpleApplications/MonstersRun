"""Async agents and orchestration.

Mirrors the synchronous `Agent` / `AutonomousAgent` / `Orchestrator` on top of
`anthropic.AsyncAnthropic`, so you can fan thousands of independent agents out
with asyncio instead of a thread pool. The message bookkeeping and tool
execution are reused from the sync `Agent` (they're pure/local); only the API
call is awaited.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Iterable

import anthropic

from .agent import Agent, EventHook
from .autonomous import RunResult, _GOAL_PROMPT, _NUDGE, _last_text
from .config import AgentConfig
from .orchestrator import OrchestratorResult, Task
from .tools import Tool, tool
from .usage import Usage

# A sentinel client for the wrapped sync Agent — it does the bookkeeping, never
# makes a network call (the async client does), so this is never used.
_UNUSED_CLIENT = object()


class AsyncAgent:
    """Async version of `Agent`: same tool-use loop, awaited API calls."""

    def __init__(
        self,
        tools: Iterable[Tool] | None = None,
        config: AgentConfig | None = None,
        client: anthropic.AsyncAnthropic | None = None,
        on_tool: EventHook | None = None,
    ) -> None:
        self._core = Agent(tools=tools, config=config, client=_UNUSED_CLIENT, on_tool=on_tool)
        self.client = client or anthropic.AsyncAnthropic(**self._core.config.client_kwargs())

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self._core.messages

    @property
    def usage(self) -> Usage:
        return self._core.usage

    @property
    def config(self) -> AgentConfig:
        return self._core.config

    async def run(self, prompt: str) -> str:
        self._core.messages.append({"role": "user", "content": prompt})
        for _ in range(self._core.config.max_iterations):
            response = await self.client.messages.create(**self._core._request_kwargs())
            done, text = self._core._advance(response)
            if done:
                return text  # type: ignore[return-value]
        return "[stopped] Reached max_iterations without a final answer."


class AsyncAutonomousAgent:
    """Async version of `AutonomousAgent`."""

    def __init__(
        self,
        tools: Iterable[Tool] | None = None,
        config: AgentConfig | None = None,
        client: anthropic.AsyncAnthropic | None = None,
        on_tool: EventHook | None = None,
    ) -> None:
        self._final: str | None = None

        @tool
        def complete_task(summary: str) -> str:
            """Call this once the goal is fully accomplished.

            Args:
                summary: A clear summary of what was accomplished and the result.
            """
            self._final = summary
            return "Task marked complete."

        all_tools: list[Tool] = list(tools or []) + [complete_task]
        self.agent = AsyncAgent(tools=all_tools, config=config, client=client, on_tool=on_tool)

    async def run(self, goal: str, max_steps: int = 12) -> RunResult:
        self._final = None
        core = self.agent._core
        core.messages = []
        core.usage = Usage()
        core.messages.append({"role": "user", "content": _GOAL_PROMPT.format(goal=goal)})

        steps = 0
        while steps < max_steps and self._final is None:
            response = await self.agent.client.messages.create(**core._request_kwargs())
            core.usage.add(getattr(response, "usage", None))
            steps += 1

            if response.stop_reason == "refusal":
                detail = getattr(response, "stop_details", None)
                category = getattr(detail, "category", None)
                return self._result(False, f"[refused] Request declined (category: {category}).", steps)

            core.messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason == "pause_turn":
                continue

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if tool_uses:
                results = [core._execute(b) for b in tool_uses]
                core.messages.append({"role": "user", "content": results})
            elif self._final is None:
                core.messages.append({"role": "user", "content": _NUDGE})

        completed = self._final is not None
        result = self._final if completed else _last_text(core.messages)
        return self._result(completed, result, steps)

    def _result(self, completed: bool, result: str, steps: int) -> RunResult:
        core = self.agent._core
        return RunResult(
            completed=completed,
            result=result,
            steps=steps,
            transcript=core.messages,
            usage=core.usage,
            model=core.config.model,
        )


class AsyncOrchestrator:
    """Run many independent async agents concurrently with an asyncio semaphore."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: anthropic.AsyncAnthropic | None = None,
        max_concurrency: int = 16,
        on_result: Callable[[str, RunResult], None] | None = None,
    ) -> None:
        self.config = config or AgentConfig()
        self.client = client or anthropic.AsyncAnthropic(**self.config.client_kwargs())
        self.max_concurrency = max_concurrency
        self.on_result = on_result

    async def run(self, tasks: Iterable[Task]) -> OrchestratorResult:
        task_list = list(tasks)
        labels = [t.label or f"task-{i}" for i, t in enumerate(task_list)]
        sem = asyncio.Semaphore(self.max_concurrency)

        async def run_one(idx: int, task: Task) -> RunResult:
            async with sem:
                agent = AsyncAutonomousAgent(
                    tools=task.tools,
                    config=task.config or self.config,
                    client=self.client,
                )
                result = await agent.run(task.goal, max_steps=task.max_steps)
                if self.on_result:
                    self.on_result(labels[idx], result)
                return result

        results = await asyncio.gather(*(run_one(i, t) for i, t in enumerate(task_list)))
        return OrchestratorResult(results=list(results), labels=labels)

    async def map_goals(
        self,
        goals: Iterable[str],
        tools: list[Tool] | None = None,
        max_steps: int = 12,
    ) -> OrchestratorResult:
        shared = tools or []
        tasks = [Task(goal=g, tools=list(shared), max_steps=max_steps) for g in goals]
        return await self.run(tasks)
