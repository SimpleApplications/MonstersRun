"""Opt-in live tests that hit the real Claude API.

These are SKIPPED unless ANTHROPIC_API_KEY is set, so the default `pytest` run
stays network-free. Run them explicitly with:

    ANTHROPIC_API_KEY=sk-ant-... pytest tests/test_live.py -v

They are intentionally tiny (low token cost) and assert behavior, not exact text.
"""

import os

import pytest

from project_june import Agent, AgentConfig, AutonomousAgent, tool
from project_june.builtin_tools import DEFAULT_TOOLS

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skipping live API tests",
)

# Keep live runs cheap and snappy.
_FAST = AgentConfig(effort="low", thinking=False, max_tokens=1024)


def test_live_plain_answer():
    agent = Agent(config=_FAST)
    out = agent.run("Reply with exactly the word: pong")
    assert "pong" in out.lower()
    assert agent.usage.turns >= 1


def test_live_tool_use():
    @tool
    def secret_number() -> str:
        """Return the secret number."""
        return "42"

    agent = Agent(tools=[secret_number], config=_FAST)
    out = agent.run("Call the secret_number tool and tell me the number it returns.")
    assert "42" in out


def test_live_structured_output():
    agent = Agent(config=_FAST)
    schema = {
        "type": "object",
        "properties": {"sum": {"type": "integer"}},
        "required": ["sum"],
        "additionalProperties": False,
    }
    out = agent.run_json("What is 2 + 2? Respond as JSON with key 'sum'.", schema)
    assert out["sum"] == 4


def test_live_autonomous_goal():
    agent = AutonomousAgent(tools=DEFAULT_TOOLS, config=_FAST)
    result = agent.run("Use the calculator to compute 6 * 7, then report the result.", max_steps=6)
    assert result.completed
    assert "42" in result.result
    assert result.cost >= 0
