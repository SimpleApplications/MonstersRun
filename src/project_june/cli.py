"""Command-line entry point for Project June.

Examples:
    june                                   # interactive chat
    june "what is 47 * 89?"                # one-off prompt
    june --goal "compute 17! and report"   # run one independent agent to done
    june --goal "research X" --memory --save
    june --goals "summarize A" "summarize B" "summarize C"   # concurrent agents

Requires ANTHROPIC_API_KEY in the environment.
"""

from __future__ import annotations

import argparse
import os
import sys

from .agent import Agent
from .autonomous import AutonomousAgent
from .builtin_tools import DEFAULT_TOOLS
from .config import AgentConfig
from .memory import MemoryStore, memory_tools
from .orchestrator import Orchestrator
from .tracing import save_run

SYSTEM = (
    "You are a capable, independent assistant with access to tools. "
    "Use the tools when they would improve your answer, and explain results clearly."
)


def _dim(text: str) -> str:
    return f"\033[2m{text}\033[0m"


def _log_tool(name: str, tool_input: dict, result: str) -> None:
    preview = result.replace("\n", " ")
    if len(preview) > 80:
        preview = preview[:80] + "…"
    print(_dim(f"  ↳ {name}({tool_input}) → {preview}"), file=sys.stderr)


def _config(args: argparse.Namespace) -> AgentConfig:
    return AgentConfig(model=args.model, effort=args.effort, system=SYSTEM)


def _tools(args: argparse.Namespace):
    tools = list(DEFAULT_TOOLS)
    if args.memory:
        tools += memory_tools(MemoryStore(".june_memory"))
    return tools


def _run_goal(args: argparse.Namespace) -> None:
    agent = AutonomousAgent(
        tools=_tools(args),
        config=_config(args),
        on_tool=_log_tool,
        on_step=lambda step, resp: print(_dim(f"  · step {step}"), file=sys.stderr),
    )
    result = agent.run(args.goal, max_steps=args.max_steps)
    status = "completed" if result.completed else f"stopped after {result.steps} steps"
    print(f"\n\033[1m[{status}]\033[0m ({result.usage.summary(result.model)})\n{result.result}")
    if args.save:
        path = save_run(result)
        print(_dim(f"\nsaved run to {path}"))


def _run_goals(args: argparse.Namespace) -> None:
    orch = Orchestrator(
        config=_config(args),
        on_result=lambda label, r: print(
            _dim(f"  [{label}] {'done' if r.completed else 'stopped'} "
                 f"in {r.steps} steps (${r.cost:.4f})"),
            file=sys.stderr,
        ),
    )
    out = orch.map_goals(args.goals, tools=_tools(args), max_steps=args.max_steps)
    for label, r in zip(out.labels, out.results):
        print(f"\n\033[1m[{label}]\033[0m\n{r.result}")
    print(_dim(f"\ntotal: {len(out.results)} agents, ${out.cost:.4f}"))


def _chat(args: argparse.Namespace) -> None:
    agent = Agent(tools=_tools(args), config=_config(args), on_tool=_log_tool)
    print("Project June — type a message, or 'exit' to quit.")
    while True:
        try:
            prompt = input("\n\033[1myou ›\033[0m ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if prompt.strip().lower() in {"exit", "quit"}:
            break
        if not prompt.strip():
            continue
        print(f"\n\033[1magent ›\033[0m {agent.run(prompt)}")


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="june", description="Independent Claude agents.")
    p.add_argument("prompt", nargs="*", help="A one-off prompt to run and exit.")
    p.add_argument("--goal", help="Run one independent agent toward this goal.")
    p.add_argument("--goals", nargs="+", help="Run one independent agent per goal, concurrently.")
    p.add_argument("--memory", action="store_true", help="Give agents persistent memory tools.")
    p.add_argument("--save", action="store_true", help="Save the run transcript to .june_runs/.")
    p.add_argument("--model", default=AgentConfig.model, help="Claude model id.")
    p.add_argument("--effort", default="high", choices=["low", "medium", "high", "max"])
    p.add_argument("--max-steps", type=int, default=12, dest="max_steps")
    return p


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: set ANTHROPIC_API_KEY in your environment first.", file=sys.stderr)
        raise SystemExit(1)

    args = _parser().parse_args()

    if args.goals:
        _run_goals(args)
    elif args.goal:
        _run_goal(args)
    elif args.prompt:
        agent = Agent(tools=_tools(args), config=_config(args))
        print(agent.run(" ".join(args.prompt)))
    else:
        _chat(args)


if __name__ == "__main__":
    main()
