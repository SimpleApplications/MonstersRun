"""Example: build an agent with your own custom tool.

Run with:  python examples/custom_tool.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

from claude_agents import Agent, AgentConfig, tool
from claude_agents.builtin_tools import current_time


@tool
def word_count(text: str) -> int:
    """Count the number of words in a piece of text.

    Args:
        text: The text to count words in.
    """
    return len(text.split())


def main() -> None:
    agent = Agent(
        tools=[word_count, current_time],
        config=AgentConfig(
            system="You are a concise writing assistant.",
            effort="high",
        ),
        on_tool=lambda name, inp, out: print(f"[tool] {name} -> {out}"),
    )

    answer = agent.run(
        "How many words are in the sentence 'the quick brown fox jumps', "
        "and what's the current UTC time?"
    )
    print("\n" + answer)


if __name__ == "__main__":
    main()
