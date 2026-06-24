"""Example: an agent that can search the web (Anthropic server-side tool).

The web_search tool runs on Anthropic's infrastructure — no local execution.
Combine it with local tools freely.

Run with:  python examples/web_search_agent.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

from project_june import Agent, AgentConfig
from project_june.builtin_tools import DEFAULT_TOOLS, WEB_SEARCH


def main() -> None:
    agent = Agent(
        tools=DEFAULT_TOOLS,
        config=AgentConfig(
            system="You are a concise research assistant. Cite what you find.",
            server_tools=[WEB_SEARCH],
        ),
    )
    print(agent.run("What did Anthropic most recently announce? Search the web and summarize."))
    print(f"\n[{agent.usage.summary(agent.config.model)}]")


if __name__ == "__main__":
    main()
