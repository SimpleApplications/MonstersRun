"""Token-usage accounting and cost estimation.

Every model turn reports a `usage` object. `Usage` accumulates those across a
run and estimates the dollar cost from a per-model price table. This is the
observability backbone the agents report through.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# USD per 1,000,000 tokens, as (input, output). Cache reads are billed at ~0.1x
# the input price and cache writes at ~1.25x (5-minute TTL). Source: the Claude
# pricing table; update here when prices change.
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-opus-4-5": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

_CACHE_READ_MULTIPLIER = 0.1
_CACHE_WRITE_MULTIPLIER = 1.25


@dataclass
class Usage:
    """Accumulated token counts across one or more model turns."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    turns: int = 0

    def add(self, response_usage: Any) -> None:
        """Fold one response's `.usage` object into the running total."""
        if response_usage is None:
            return
        self.input_tokens += _get(response_usage, "input_tokens")
        self.output_tokens += _get(response_usage, "output_tokens")
        self.cache_read_input_tokens += _get(response_usage, "cache_read_input_tokens")
        self.cache_creation_input_tokens += _get(response_usage, "cache_creation_input_tokens")
        self.turns += 1

    @property
    def total_input_tokens(self) -> int:
        """All input tokens, cached or not."""
        return (
            self.input_tokens
            + self.cache_read_input_tokens
            + self.cache_creation_input_tokens
        )

    def cost(self, model: str) -> float:
        """Estimate the USD cost for `model`. Unknown models cost 0.0."""
        in_price, out_price = MODEL_PRICES.get(model, (0.0, 0.0))
        dollars = (
            self.input_tokens * in_price
            + self.cache_read_input_tokens * in_price * _CACHE_READ_MULTIPLIER
            + self.cache_creation_input_tokens * in_price * _CACHE_WRITE_MULTIPLIER
            + self.output_tokens * out_price
        )
        return dollars / 1_000_000

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cache_read_input_tokens=self.cache_read_input_tokens + other.cache_read_input_tokens,
            cache_creation_input_tokens=self.cache_creation_input_tokens
            + other.cache_creation_input_tokens,
            turns=self.turns + other.turns,
        )

    def summary(self, model: str | None = None) -> str:
        parts = [
            f"{self.turns} turns",
            f"in={self.total_input_tokens}",
            f"out={self.output_tokens}",
        ]
        if self.cache_read_input_tokens:
            parts.append(f"cache_read={self.cache_read_input_tokens}")
        if model:
            parts.append(f"${self.cost(model):.4f}")
        return ", ".join(parts)


def _get(obj: Any, name: str) -> int:
    return getattr(obj, name, 0) or 0
