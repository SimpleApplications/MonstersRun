"""Tests for the MCP -> Tool bridge."""

from types import SimpleNamespace

from project_june import Agent, StaticMCPProvider, mcp_tools
from project_june.mcp_bridge import MCPProvider, MCPToolSpec, _sanitize_schema


def make_provider():
    provider = StaticMCPProvider()
    provider.add(
        "add",
        "Add two integers.",
        {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
        lambda a, b: a + b,
    )
    provider.add("ping", "Ping.", {"type": "object", "properties": {}}, lambda: "pong")
    return provider


def test_static_provider_satisfies_protocol():
    assert isinstance(make_provider(), MCPProvider)


def test_mcp_tools_builds_tools_with_server_schema():
    tools = {t.name: t for t in mcp_tools(make_provider())}
    assert set(tools) == {"add", "ping"}
    assert tools["add"].description == "Add two integers."
    assert tools["add"].input_schema["required"] == ["a", "b"]
    # The tool actually forwards to the provider.
    assert tools["add"].run(a=2, b=3) == "5"
    assert tools["ping"].run() == "pong"


def test_prefix_and_filter():
    tools = {t.name: t for t in mcp_tools(make_provider(), prefix="calc_", only=["add"])}
    assert set(tools) == {"calc_add"}


def test_sanitize_schema_fixes_non_object():
    assert _sanitize_schema(None) == {"type": "object", "properties": {}}
    assert _sanitize_schema({"type": "string"}) == {"type": "object", "properties": {}}
    fixed = _sanitize_schema({"type": "object"})
    assert fixed["properties"] == {}


def test_spec_dataclass_defaults():
    spec = MCPToolSpec("n", "d")
    assert spec.input_schema == {}


def test_agent_can_call_mcp_tool():
    # End-to-end through the agent loop with a stub client.
    tools = mcp_tools(make_provider())

    def tool_use(name, inp, id="t"):
        return SimpleNamespace(type="tool_use", name=name, input=inp, id=id)

    def text(t):
        return SimpleNamespace(type="text", text=t)

    def resp(content, stop="tool_use"):
        return SimpleNamespace(content=content, stop_reason=stop, stop_details=None, usage=None)

    class Client:
        def __init__(self):
            self._r = [
                resp([tool_use("add", {"a": 4, "b": 5})]),
                resp([text("The sum is 9.")], stop="end_turn"),
            ]
            self.messages = SimpleNamespace(create=lambda **kw: self._r.pop(0))

    agent = Agent(tools=tools, client=Client())
    assert agent.run("add 4 and 5") == "The sum is 9."
