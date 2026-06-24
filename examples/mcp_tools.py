"""Example: give an agent tools from an MCP server.

This uses StaticMCPProvider (an in-memory provider) so it runs without a real
server. To bridge a real MCP server, implement the same two methods —
list_tools() and call_tool() — on a wrapper around your MCP client session.

Run with:  python examples/mcp_tools.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

from project_june import Agent, StaticMCPProvider, mcp_tools


def build_provider() -> StaticMCPProvider:
    provider = StaticMCPProvider()
    provider.add(
        "fx_rate",
        "Get the (pretend) USD exchange rate for a currency code.",
        {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "e.g. EUR"}},
            "required": ["code"],
        },
        lambda code: f"1 USD = {0.92 if code == 'EUR' else 1.0} {code}",
    )
    return provider


def main() -> None:
    agent = Agent(
        tools=mcp_tools(build_provider(), prefix="mcp_"),
        on_tool=lambda name, inp, out: print(f"  {name}{inp} -> {out}"),
    )
    print(agent.run("What's the USD to EUR rate? Use the available tool."))


if __name__ == "__main__":
    main()
