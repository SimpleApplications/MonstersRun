"""Run many independent agents concurrently.

An `Orchestrator` fans a set of goals out to separate `AutonomousAgent`s that run
in parallel threads, then collects their results. Each agent is fully independent
— its own conversation, tools, and memory of the run — which is exactly the
"independent agents" model: decompose a problem, let N agents work at once, and
gather what they produce.

The Anthropic SDK client is thread-safe, so the agents share one client (and its
connection pool) by default. Parallelism is bounded by `max_workers`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Iterable

import anthropic

from .autonomous import AutonomousAgent, RunResult
from .config import AgentConfig
from .tools import Tool
from .usage import Usage


@dataclass
class Task:
    """One unit of work for an independent agent."""

    goal: str
    tools: list[Tool] = field(default_factory=list)
    config: AgentConfig | None = None
    max_steps: int = 12
    label: str | None = None


@dataclass
class OrchestratorResult:
    """The combined outcome of a concurrent run."""

    results: list[RunResult]
    labels: list[str]

    @property
    def usage(self) -> Usage:
        total = Usage()
        for r in self.results:
            total = total + r.usage
        return total

    @property
    def cost(self) -> float:
        return sum(r.cost for r in self.results)

    @property
    def all_completed(self) -> bool:
        return all(r.completed for r in self.results)

    def __iter__(self):
        return iter(self.results)


class Orchestrator:
    def __init__(
        self,
        config: AgentConfig | None = None,
        client: anthropic.Anthropic | None = None,
        max_workers: int = 8,
        on_result: Callable[[str, RunResult], None] | None = None,
    ) -> None:
        self.config = config or AgentConfig()
        # One shared, thread-safe client → shared connection pool across agents.
        self.client = client or anthropic.Anthropic()
        self.max_workers = max_workers
        self.on_result = on_result

    def run(self, tasks: Iterable[Task]) -> OrchestratorResult:
        """Run `tasks` concurrently and return results in input order."""
        task_list = list(tasks)
        labels = [t.label or f"task-{i}" for i, t in enumerate(task_list)]

        def run_one(task: Task) -> RunResult:
            agent = AutonomousAgent(
                tools=task.tools,
                config=task.config or self.config,
                client=self.client,
            )
            return agent.run(task.goal, max_steps=task.max_steps)

        results: list[RunResult] = [None] * len(task_list)  # type: ignore[list-item]
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {pool.submit(run_one, t): i for i, t in enumerate(task_list)}
            for future in futures:
                idx = futures[future]
                results[idx] = future.result()
                if self.on_result:
                    self.on_result(labels[idx], results[idx])

        return OrchestratorResult(results=results, labels=labels)

    def map_goals(
        self,
        goals: Iterable[str],
        tools: list[Tool] | None = None,
        max_steps: int = 12,
    ) -> OrchestratorResult:
        """Convenience: run one independent agent per goal string, concurrently."""
        shared_tools = tools or []
        tasks = [Task(goal=g, tools=list(shared_tools), max_steps=max_steps) for g in goals]
        return self.run(tasks)


def synthesize(
    question: str,
    fan_out: OrchestratorResult,
    config: AgentConfig | None = None,
    client: anthropic.Anthropic | None = None,
) -> RunResult:
    """Combine independent agents' findings into one answer.

    A common pattern: fan a question out to several agents, then hand all their
    results to a final agent that synthesizes a single coherent answer.
    """
    findings = "\n\n".join(
        f"## {label}\n{r.result}" for label, r in zip(fan_out.labels, fan_out.results)
    )
    synthesizer = AutonomousAgent(
        config=config or AgentConfig(system="You synthesize findings into one clear answer."),
        client=client,
    )
    goal = (
        f"Question:\n{question}\n\n"
        f"Independent agents produced these findings:\n\n{findings}\n\n"
        "Synthesize them into a single, well-organized answer to the question. "
        "Resolve disagreements and note any gaps."
    )
    return synthesizer.run(goal, max_steps=3)
