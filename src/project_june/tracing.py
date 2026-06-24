"""Persist and inspect agent runs.

`save_run` writes a JSON record of an autonomous run — outcome, steps, usage,
cost, and a readable transcript — so you can audit what an independent agent did
after the fact. The transcript serializer handles both plain dict messages (user
turns, tool results) and the SDK's content-block objects (assistant turns).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from .autonomous import RunResult


def block_to_dict(block: Any) -> dict[str, Any]:
    """Convert one content block (dict or SDK object) to a JSON-able dict."""
    if isinstance(block, dict):
        return block
    # Real SDK blocks are pydantic models.
    dump = getattr(block, "model_dump", None)
    if callable(dump):
        try:
            return dump(mode="json")
        except Exception:  # pragma: no cover - defensive
            pass
    btype = getattr(block, "type", None)
    if btype == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "name": getattr(block, "name", ""),
            "input": dict(getattr(block, "input", {}) or {}),
            "id": getattr(block, "id", ""),
        }
    return {"type": btype or "unknown", "repr": str(block)}


def transcript_to_dicts(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Render a message history into JSON-able role/content dicts."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        content = msg["content"]
        if isinstance(content, str):
            out.append({"role": msg["role"], "content": content})
        else:
            out.append({"role": msg["role"], "content": [block_to_dict(b) for b in content]})
    return out


def run_to_dict(result: RunResult) -> dict[str, Any]:
    """Build the full JSON-able record for a run."""
    return {
        "completed": result.completed,
        "steps": result.steps,
        "result": result.result,
        "model": result.model,
        "usage": dataclasses.asdict(result.usage),
        "cost_usd": round(result.cost, 6),
        "transcript": transcript_to_dicts(result.transcript),
    }


def save_run(
    result: RunResult,
    directory: str | Path = ".june_runs",
    name: str | None = None,
) -> Path:
    """Write a run record to `directory/<name>.json` and return the path."""
    out_dir = Path(directory).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = (name or f"run-{result.steps}step").replace("/", "_")
    if not fname.endswith(".json"):
        fname += ".json"
    path = out_dir / fname
    path.write_text(json.dumps(run_to_dict(result), indent=2), encoding="utf-8")
    return path
