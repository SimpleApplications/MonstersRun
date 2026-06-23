"""A small set of ready-to-use tools.

These double as worked examples of the `@tool` decorator. Import the ones you
want and pass them to an Agent, or write your own the same way.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

from .tools import tool


@tool
def current_time(timezone: str = "UTC") -> str:
    """Return the current date and time.

    Args:
        timezone: Either "UTC" or "local". Defaults to "UTC".
    """
    if timezone.lower() == "local":
        now = _dt.datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S (local)")
    now = _dt.datetime.now(_dt.timezone.utc)
    return now.strftime("%Y-%m-%d %H:%M:%S UTC")


@tool
def calculate(expression: str) -> str:
    """Evaluate a basic arithmetic expression and return the result.

    Supports + - * / ** % and parentheses over numbers only.

    Args:
        expression: e.g. "2 * (3 + 4) ** 2".
    """
    allowed = set("0123456789+-*/%(). ")
    if not set(expression) <= allowed:
        return "Error: expression may only contain numbers and + - * / % ( ) ."
    try:
        # Numbers-only character set above keeps eval to pure arithmetic.
        return str(eval(expression, {"__builtins__": {}}, {}))  # noqa: S307
    except Exception as exc:
        return f"Error: {exc}"


@tool
def read_file(path: str, max_chars: int = 4000) -> str:
    """Read a UTF-8 text file from the local filesystem.

    Args:
        path: Path to the file.
        max_chars: Truncate output to this many characters. Defaults to 4000.
    """
    p = Path(path).expanduser()
    if not p.is_file():
        return f"Error: no such file: {path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + f"\n... [truncated, {len(text)} chars total]"
    return text


DEFAULT_TOOLS = [current_time, calculate, read_file]
