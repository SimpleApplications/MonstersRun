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


@tool
def list_directory(path: str = ".", max_entries: int = 100) -> str:
    """List the entries in a directory (directories marked with a trailing /).

    Args:
        path: Directory to list. Defaults to the current directory.
        max_entries: Cap on how many entries to return. Defaults to 100.
    """
    p = Path(path).expanduser()
    if not p.is_dir():
        return f"Error: not a directory: {path}"
    entries = sorted(
        (c.name + ("/" if c.is_dir() else "") for c in p.iterdir()),
        key=str.lower,
    )
    shown = entries[:max_entries]
    out = "\n".join(shown) if shown else "(empty)"
    if len(entries) > max_entries:
        out += f"\n... [{len(entries) - max_entries} more]"
    return out


@tool
def write_file(path: str, content: str) -> str:
    """Write text to a file, confined to the current working directory tree.

    Writes outside the working directory are refused (the path is model-supplied).

    Args:
        path: Destination path (relative to, or inside, the working directory).
        content: The UTF-8 text to write.
    """
    root = Path.cwd().resolve()
    dest = (root / Path(path)).resolve()
    if dest != root and root not in dest.parents:
        return f"Error: refusing to write outside the working directory: {path}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {dest.relative_to(root)}"


# Read-only, side-effect-free tools, safe to hand to any agent by default.
DEFAULT_TOOLS = [current_time, calculate, read_file, list_directory]

# Tools with side effects — opt in explicitly.
WRITE_TOOLS = [write_file]

# Anthropic server-tool specs (run server-side; pass via AgentConfig.server_tools).
# Use the latest variants on Opus 4.6+/Sonnet 4.6; older models need the basic ones.
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search"}
WEB_FETCH = {"type": "web_fetch_20260209", "name": "web_fetch"}
