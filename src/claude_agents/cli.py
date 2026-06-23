"""Command-line entry point: an interactive REPL backed by an Agent.

Usage:
    claude-agent                 # interactive chat
    claude-agent "one-off task"  # run a single prompt and exit

Requires ANTHROPIC_API_KEY in the environment (or a .env you've sourced).
"""

from __future__ import annotations

import os
import sys

from .agent import Agent
from .builtin_tools import DEFAULT_TOOLS
from .config import AgentConfig

SYSTEM = (
    "You are a helpful, capable assistant with access to tools. "
    "Use the tools when they would improve your answer, and explain your results clearly."
)


def _log_tool(name: str, tool_input: dict, result: str) -> None:
    preview = result.replace("\n", " ")
    if len(preview) > 80:
        preview = preview[:80] + "…"
    print(f"  \033[2m↳ {name}({tool_input}) → {preview}\033[0m", file=sys.stderr)


def _build_agent() -> Agent:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("error: set ANTHROPIC_API_KEY in your environment first.", file=sys.stderr)
        raise SystemExit(1)
    return Agent(
        tools=DEFAULT_TOOLS,
        config=AgentConfig(system=SYSTEM),
        on_tool=_log_tool,
    )


def main() -> None:
    agent = _build_agent()

    # One-off mode: everything after the program name is a single prompt.
    if len(sys.argv) > 1:
        print(agent.run(" ".join(sys.argv[1:])))
        return

    print("claude-agent — type a message, or 'exit' to quit.")
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


if __name__ == "__main__":
    main()
