"""Context-window management for long-running agents.

A long autonomous run accumulates many tool rounds. `compact_messages` keeps the
history under a token budget by dropping the *oldest* exchanges while preserving
correctness:

- the initial user message (the goal/task) is always kept, so the agent never
  forgets what it's doing;
- the kept tail always begins at an assistant turn, so it never starts with an
  orphan tool_result (the API requires each tool_use to be paired with its
  result, and the first message to be a user turn).

Token counts are estimated from text length (~4 chars/token) — cheap and good
enough for a guard. It only trims when over budget, so short runs are untouched.
"""

from __future__ import annotations

from typing import Any

_CHARS_PER_TOKEN = 4


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough token estimate for a message history."""
    chars = 0
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, str):
            chars += len(content)
        else:
            chars += len(str(content))
    return chars // _CHARS_PER_TOKEN


def compact_messages(
    messages: list[dict[str, Any]],
    max_tokens: int,
    keep_recent: int = 6,
) -> list[dict[str, Any]]:
    """Return a history under `max_tokens`, dropping the oldest middle exchanges.

    Keeps `messages[0]` (the task) plus a recent tail. The tail is extended back
    to the nearest assistant turn so the result is always a valid conversation.
    If the history is already small enough, it's returned unchanged.
    """
    if max_tokens <= 0 or len(messages) <= keep_recent + 1:
        return messages
    if estimate_tokens(messages) <= max_tokens:
        return messages

    head = messages[:1]
    start = len(messages) - keep_recent
    # Move the tail start forward to the first assistant turn, so we never begin
    # the tail with an orphan tool_result (a user turn carrying tool results).
    while start < len(messages) and messages[start].get("role") != "assistant":
        start += 1
    if start >= len(messages):
        # No assistant turn in the window — nothing safe to keep but the head.
        return head if head else messages

    tail = messages[start:]
    # If trimming wouldn't actually drop anything, return as-is.
    if start <= 1:
        return messages
    return head + tail
