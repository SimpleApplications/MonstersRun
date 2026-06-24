"""Persistent, file-backed memory for independent agents.

A `MemoryStore` is a directory of small text documents an agent can read and
write across runs, so an independent agent can carry learnings from one session
into the next. `memory_tools(store)` exposes it to an agent as a set of tools.

Security: every key is validated to stay inside the store's root directory —
path-traversal attempts (``..``, absolute paths, symlinks pointing out) are
rejected, because tool inputs are model-controlled.
"""

from __future__ import annotations

from pathlib import Path

from .tools import Tool, tool


class MemoryError(Exception):
    """Raised for invalid keys or unsafe paths."""


class MemoryStore:
    def __init__(self, root: str | Path = ".june_memory") -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        key = key.strip().lstrip("/")
        if not key:
            raise MemoryError("memory key must be non-empty")
        candidate = (self.root / key).resolve()
        # Confine to the store root — reject traversal / absolute escapes.
        if candidate != self.root and self.root not in candidate.parents:
            raise MemoryError(f"unsafe memory key: {key!r}")
        return candidate

    def read(self, key: str) -> str:
        path = self._path(key)
        if not path.is_file():
            raise MemoryError(f"no memory at {key!r}")
        return path.read_text(encoding="utf-8")

    def write(self, key: str, content: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def append(self, key: str, content: str) -> None:
        existing = ""
        try:
            existing = self.read(key)
        except MemoryError:
            pass
        sep = "" if not existing or existing.endswith("\n") else "\n"
        self.write(key, existing + sep + content)

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if path.is_file():
            path.unlink()
            return True
        return False

    def list(self) -> list[str]:
        """Return all memory keys (relative paths), sorted."""
        return sorted(
            str(p.relative_to(self.root))
            for p in self.root.rglob("*")
            if p.is_file()
        )


def memory_tools(store: MemoryStore) -> list[Tool]:
    """Build the set of memory tools bound to `store`.

    Hand these to an Agent / AutonomousAgent so it can persist and recall notes
    across runs.
    """

    @tool
    def memory_write(key: str, content: str) -> str:
        """Save a note to persistent memory, overwriting any existing note.

        Args:
            key: A short path-like name, e.g. "facts/user" or "todo.md".
            content: The text to store.
        """
        store.write(key, content)
        return f"saved {key!r} ({len(content)} chars)"

    @tool
    def memory_append(key: str, content: str) -> str:
        """Append a line to a memory note, creating it if needed.

        Args:
            key: The note's path-like name.
            content: The text to append.
        """
        store.append(key, content)
        return f"appended to {key!r}"

    @tool
    def memory_read(key: str) -> str:
        """Read a note from persistent memory.

        Args:
            key: The note's path-like name.
        """
        return store.read(key)

    @tool
    def memory_list() -> str:
        """List the keys of all stored memory notes."""
        keys = store.list()
        return "\n".join(keys) if keys else "(memory is empty)"

    return [memory_write, memory_append, memory_read, memory_list]
