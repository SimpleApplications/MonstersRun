"""Example: fan many independent agents out concurrently with asyncio.

Run with:  python examples/async_agents.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

import asyncio

from project_june import AsyncOrchestrator


async def main() -> None:
    orch = AsyncOrchestrator(
        max_concurrency=8,
        on_result=lambda label, r: print(f"[{label}] done ({r.steps} steps, ${r.cost:.4f})"),
    )
    out = await orch.map_goals(
        [
            "In one sentence, what is an agentic loop?",
            "In one sentence, what is prompt caching?",
            "In one sentence, what is adaptive thinking?",
            "In one sentence, what is the Model Context Protocol?",
        ],
        max_steps=3,
    )
    print(f"\n{len(out.results)} agents, total ${out.cost:.4f}\n")
    for label, r in zip(out.labels, out.results):
        print(f"- {label}: {r.result}")


if __name__ == "__main__":
    asyncio.run(main())
