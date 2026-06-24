"""Example: an independent agent with persistent memory.

The agent can save notes that survive across runs — run this twice and it will
recall what it learned the first time.

Run with:  python examples/agent_with_memory.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

from project_june import AutonomousAgent, MemoryStore, memory_tools
from project_june.builtin_tools import DEFAULT_TOOLS


def main() -> None:
    store = MemoryStore(".june_memory")
    agent = AutonomousAgent(
        tools=DEFAULT_TOOLS + memory_tools(store),
        on_tool=lambda name, inp, out: print(f"  {name} -> {out[:60]}"),
    )

    result = agent.run(
        "Check your memory under 'profile' for what you know about me. If it's "
        "empty, record that my favorite language is Python and my timezone is UTC. "
        "Then tell me what you now know about me.",
    )

    print(f"\ncompleted={result.completed}  steps={result.steps}  "
          f"cost=${result.cost:.4f}")
    print(result.result)
    print("\nMemory keys now:", store.list())


if __name__ == "__main__":
    main()
