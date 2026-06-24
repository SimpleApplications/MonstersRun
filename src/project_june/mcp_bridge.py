"""Bridge MCP (Model Context Protocol) servers into Project June tools.

An MCP server exposes a set of tools with JSON-schema inputs. `mcp_tools` turns
those into native `Tool` objects an `Agent` / `AutonomousAgent` can call — so an
independent agent can use any MCP server (GitHub, Slack, a filesystem, your own)
alongside its local tools.

You supply a *provider* implementing the small `MCPProvider` protocol:

    class MyProvider:
        def list_tools(self) -> list[MCPToolSpec]: ...
        def call_tool(self, name: str, arguments: dict) -> str: ...

The official `mcp` Python SDK's `ClientSession` is async; wrap it so `list_tools`
/ `call_tool` are synchronous (e.g. drive a private event loop), or use any sync
transport. `StaticMCPProvider` is a ready-made in-memory provider for tests and
local tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

from .tools import Tool


@dataclass
class MCPToolSpec:
    """A tool as advertised by an MCP server."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class MCPProvider(Protocol):
    """The minimal surface `mcp_tools` needs from an MCP client."""

    def list_tools(self) -> list[MCPToolSpec]:
        ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        ...


def _sanitize_schema(schema: dict[str, Any] | None) -> dict[str, Any]:
    """Coerce an MCP input schema into the object schema the Messages API wants."""
    if not isinstance(schema, dict) or schema.get("type") != "object":
        return {"type": "object", "properties": {}}
    out = dict(schema)
    out.setdefault("properties", {})
    return out


def mcp_tools(
    provider: MCPProvider,
    prefix: str = "",
    only: list[str] | None = None,
) -> list[Tool]:
    """Build native Tools from an MCP provider's advertised tools.

    Args:
        provider: An object exposing list_tools() and call_tool().
        prefix: Optional name prefix (e.g. "github_") to avoid collisions when
            bridging several servers into one agent.
        only: If given, only bridge tools whose (unprefixed) name is in this list.
    """
    tools: list[Tool] = []
    for spec in provider.list_tools():
        if only is not None and spec.name not in only:
            continue
        tools.append(
            Tool(
                name=f"{prefix}{spec.name}",
                description=spec.description or spec.name,
                input_schema=_sanitize_schema(spec.input_schema),
                func=_make_caller(provider, spec.name),
            )
        )
    return tools


def _make_caller(provider: MCPProvider, tool_name: str) -> Callable[..., str]:
    """Return a function that forwards a tool call to the provider."""

    def call(**arguments: Any) -> str:
        return provider.call_tool(tool_name, arguments)

    return call


class StaticMCPProvider:
    """An in-memory MCP provider built from local Python callables.

    Handy for tests and for exposing a fixed tool set without a running server.

        provider = StaticMCPProvider()
        provider.add("add", "Add two numbers", {...schema...}, lambda a, b: a + b)
        agent = Agent(tools=mcp_tools(provider))
    """

    def __init__(self) -> None:
        self._specs: list[MCPToolSpec] = []
        self._funcs: dict[str, Callable[..., Any]] = {}

    def add(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        func: Callable[..., Any],
    ) -> None:
        self._specs.append(MCPToolSpec(name, description, input_schema))
        self._funcs[name] = func

    def list_tools(self) -> list[MCPToolSpec]:
        return list(self._specs)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        if name not in self._funcs:
            raise KeyError(f"unknown MCP tool: {name!r}")
        result = self._funcs[name](**arguments)
        return result if isinstance(result, str) else str(result)
