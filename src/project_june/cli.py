"""Command-line entry point for Project June.

Usage:
    june                          # interactive chat with a tool-equipped agent
    june "one-off task"           # run a single prompt and exit
    june --goal "a goal to pursue"  # run an independent agent to completion

Requires ANTHROPIC_API_KEY in the environment (or a .env you've sourced).
"""

from __future__ import annotations

import os
import sys

from .agent import Agent
from .autonomous import AutonomousAgent
from .builtin_tools import DEFAULT_TOOLS
from .config import AgentConfig

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


def _require_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: set ANTHROPIC_API_KEY in your environment first.", file=sys.stderr)
        raise SystemExit(1)


def _run_goal(goal: str) -> None:
    agent = AutonomousAgent(
        tools=DEFAULT_TOOLS,
        config=AgentConfig(system=SYSTEM),
        on_tool=_log_tool,
        on_step=lambda step, resp: print(_dim(f"  · step {step}"), file=sys.stderr),
    )
    result = agent.run(goal)
    status = "completed" if result.completed else f"stopped after {result.steps} steps"
    print(f"\n\033[1m[{status}]\033[0m\n{result.result}")


def _chat() -> None:
    agent = Agent(tools=DEFAULT_TOOLS, config=AgentConfig(system=SYSTEM), on_tool=_log_tool)
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


def main() -> None:
    _require_key()
    args = sys.argv[1:]

    if args and args[0] == "--goal":
        goal = " ".join(args[1:]).strip()
        if not goal:
            print("error: --goal needs a goal string.", file=sys.stderr)
            raise SystemExit(1)
        _run_goal(goal)
        return

    if args:
        print(Agent(tools=DEFAULT_TOOLS, config=AgentConfig(system=SYSTEM)).run(" ".join(args)))
        return

    _chat()


if __name__ == "__main__":
    main()
