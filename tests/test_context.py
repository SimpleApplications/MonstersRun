"""Tests for context-window compaction."""

from project_june.context import compact_messages, estimate_tokens


def build_history(rounds: int) -> list[dict]:
    """A realistic history: user goal, then assistant/tool-result pairs."""
    msgs = [{"role": "user", "content": "GOAL: " + "x" * 50}]
    for i in range(rounds):
        msgs.append({"role": "assistant", "content": f"thinking {i} " + "y" * 50})
        msgs.append({"role": "user", "content": [{"type": "tool_result", "content": "z" * 50}]})
    return msgs


def test_estimate_tokens_scales_with_length():
    small = [{"role": "user", "content": "hi"}]
    big = [{"role": "user", "content": "x" * 4000}]
    assert estimate_tokens(small) < estimate_tokens(big)
    assert estimate_tokens(big) == 1000  # 4000 chars / 4


def test_no_compaction_when_under_budget():
    msgs = build_history(2)
    assert compact_messages(msgs, max_tokens=10_000) is msgs


def test_no_compaction_for_short_history():
    msgs = build_history(1)
    assert compact_messages(msgs, max_tokens=1) is msgs


def test_compaction_keeps_goal_and_valid_tail():
    msgs = build_history(20)  # large
    out = compact_messages(msgs, max_tokens=50, keep_recent=6)
    assert len(out) < len(msgs)
    # Goal is preserved as the first message.
    assert out[0] is msgs[0]
    assert out[0]["content"].startswith("GOAL:")
    # The conversation starts with a user turn (API requirement)...
    assert out[0]["role"] == "user"
    # ...and the message right after the goal is an assistant turn, so we never
    # begin the tail with an orphan tool_result.
    assert out[1]["role"] == "assistant"


def test_compaction_result_has_no_orphan_tool_result_after_head():
    msgs = build_history(30)
    out = compact_messages(msgs, max_tokens=30, keep_recent=4)
    # No user(tool_result) immediately follows the head goal.
    second = out[1]
    assert second["role"] == "assistant"


def test_agent_applies_compaction_in_request_kwargs():
    from project_june import Agent, AgentConfig

    agent = Agent(config=AgentConfig(max_context_tokens=50), client=object())
    agent.messages = build_history(20)
    before = len(agent.messages)
    agent._request_kwargs()
    assert len(agent.messages) < before  # history was compacted in place
