"""Tool definitions for agents.

A `Tool` pairs a JSON-schema description (sent to Claude) with a Python callable
(run locally when Claude asks for it). The `@tool` decorator builds the schema
automatically from a function's type hints and docstring, so defining a tool is
just writing a normal, documented function.

    @tool
    def get_weather(city: str) -> str:
        '''Get the current weather for a city.

        Args:
            city: City name, e.g. "Paris".
        '''
        ...
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, get_args, get_origin, get_type_hints

# Map Python types to JSON-schema types. Anything not listed falls back to "string".
_JSON_TYPES: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _json_type(py_type: Any) -> str:
    origin = get_origin(py_type)
    if origin is not None:
        py_type = origin
    return _JSON_TYPES.get(py_type, "string")


def _parse_arg_docs(docstring: str | None) -> dict[str, str]:
    """Pull per-argument descriptions out of a Google-style 'Args:' block."""
    if not docstring:
        return {}
    lines = docstring.splitlines()
    descriptions: dict[str, str] = {}
    in_args = False
    for raw in lines:
        line = raw.strip()
        if line.lower() in {"args:", "arguments:", "parameters:"}:
            in_args = True
            continue
        if in_args:
            # Blank line or a new section header ends the Args block.
            if not line or line.endswith(":") and " " not in line.rstrip(":"):
                break
            if ":" in line:
                name, _, desc = line.partition(":")
                descriptions[name.strip()] = desc.strip()
    return descriptions


@dataclass
class Tool:
    """A callable tool exposed to the agent."""

    name: str
    description: str
    input_schema: dict[str, Any]
    func: Callable[..., Any]

    def to_api(self) -> dict[str, Any]:
        """Render the tool definition in the shape the Messages API expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def run(self, **kwargs: Any) -> str:
        """Execute the tool and coerce the result to a string for tool_result."""
        result = self.func(**kwargs)
        return result if isinstance(result, str) else str(result)


def tool(func: Callable[..., Any]) -> Tool:
    """Decorator that turns a typed, documented function into a `Tool`.

    The function's name becomes the tool name, the first paragraph of its
    docstring becomes the description, and its parameters (with type hints and
    'Args:' docs) become the input schema.
    """
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    summary = doc.split("\n\n", 1)[0].strip() or func.__name__
    arg_docs = _parse_arg_docs(doc)

    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        py_type = hints.get(param_name, str)
        prop: dict[str, Any] = {"type": _json_type(py_type)}

        # Surface Literal/Enum choices as a JSON-schema enum.
        if get_origin(py_type) is not None:
            args = [a for a in get_args(py_type) if isinstance(a, (str, int, float, bool))]
            if args and all(isinstance(a, type(args[0])) for a in args):
                prop["enum"] = list(args)

        if param_name in arg_docs:
            prop["description"] = arg_docs[param_name]
        properties[param_name] = prop

        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }

    return Tool(
        name=func.__name__,
        description=summary,
        input_schema=input_schema,
        func=func,
    )
