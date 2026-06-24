"""Tests for the agent loops using a stubbed client (no network).

The stub mimics the shape Project June relies on from the Anthropic SDK:
a `messages.create(**kwargs)` that returns an object with `.stop_reason` and
`.content` (a list of blocks with `.type` and the relevant fields).
"""

from types import SimpleNamespace

from project_june import Agent, AutonomousAgent, tool


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(name, input, id="tu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=input, id=id)


def response(content, stop_reason="end_turn", usage=None):
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        stop_details=None,
        usage=usage,
    )


def usage(input_tokens=0, output_tokens=0):
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )


class StubClient:
    """Returns a scripted sequence of responses, one per create() call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        # Snapshot messages at call time — the agent mutates the live list.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self._responses.pop(0)


class _StreamCtx:
    """Mimics the SDK's streaming context manager for one turn."""

    def __init__(self, chunks, final):
        self._chunks = chunks
        self._final = final
        self.text_stream = iter(chunks)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._final


class StreamStubClient:
    """Stub whose messages.stream() yields scripted text chunks per turn."""

    def __init__(self, turns):
        # turns: list of (chunks, final_response)
        self._turns = list(turns)
        self.messages = SimpleNamespace(stream=self._stream)

    def _stream(self, **kwargs):
        chunks, final = self._turns.pop(0)
        return _StreamCtx(chunks, final)


@tool
def echo(value: str) -> str:
    """Echo a value back.

    Args:
        value: The value to echo.
    """
    return f"echoed:{value}"


def test_agent_runs_tool_then_answers():
    client = StubClient(
        [
            response([tool_use_block("echo", {"value": "hi"})], stop_reason="tool_use"),
            response([text_block("All done.")], stop_reason="end_turn"),
        ]
    )
    agent = Agent(tools=[echo], client=client)
    assert agent.run("please echo hi") == "All done."
    assert len(client.calls) == 2
    # Second call's history must carry the tool_result back to the model.
    last_user = client.calls[1]["messages"][-1]
    assert last_user["role"] == "user"
    assert last_user["content"][0]["content"] == "echoed:hi"


def test_agent_handles_unknown_tool():
    client = StubClient(
        [
            response([tool_use_block("nope", {})], stop_reason="tool_use"),
            response([text_block("recovered")], stop_reason="end_turn"),
        ]
    )
    agent = Agent(tools=[echo], client=client)
    assert agent.run("call a missing tool") == "recovered"
    tool_result = client.calls[1]["messages"][-1]["content"][0]
    assert tool_result["is_error"] is True


def test_agent_handles_refusal():
    client = StubClient([response([], stop_reason="refusal")])
    agent = Agent(client=client)
    assert agent.run("bad").startswith("[refused]")


def test_run_json_parses_structured_output():
    client = StubClient([response([text_block('{"name": "Ada", "age": 36}')])])
    agent = Agent(client=client)
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
        "additionalProperties": False,
    }
    out = agent.run_json("Extract the person.", schema)
    assert out == {"name": "Ada", "age": 36}
    # The request carried the json_schema format.
    fmt = client.calls[0]["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"] == schema


def test_autonomous_completes_via_complete_task():
    client = StubClient(
        [
            response([tool_use_block("echo", {"value": "x"})], stop_reason="tool_use"),
            response(
                [tool_use_block("complete_task", {"summary": "goal met"}, id="tu_2")],
                stop_reason="tool_use",
            ),
        ]
    )
    agent = AutonomousAgent(tools=[echo], client=client)
    result = agent.run("do the thing", max_steps=5)
    assert result.completed is True
    assert result.result == "goal met"
    assert result.steps == 2


def test_autonomous_tracks_usage_and_cost():
    client = StubClient(
        [
            response(
                [tool_use_block("complete_task", {"summary": "done"})],
                stop_reason="tool_use",
                usage=usage(input_tokens=1_000, output_tokens=500),
            ),
        ]
    )
    from project_june import AgentConfig

    agent = AutonomousAgent(config=AgentConfig(model="claude-opus-4-8"), client=client)
    result = agent.run("go")
    assert result.usage.input_tokens == 1_000
    assert result.usage.output_tokens == 500
    assert result.model == "claude-opus-4-8"
    assert result.cost > 0


def test_stream_emits_text_and_runs_tools():
    collected = []
    client = StreamStubClient(
        [
            # Turn 1: streams some text, then asks for a tool.
            (["Let me ", "check."], response(
                [tool_use_block("echo", {"value": "hi"})], stop_reason="tool_use")),
            # Turn 2: streams the final answer.
            (["All ", "done."], response([text_block("All done.")])),
        ]
    )
    agent = Agent(tools=[echo], client=client)
    final = agent.stream("go", on_text=collected.append)
    assert final == "All done."
    assert "".join(collected) == "Let me check.All done."


def test_run_json_errors_on_truncation():
    import pytest

    client = StubClient([response([text_block("{")], stop_reason="max_tokens")])
    agent = Agent(client=client)
    with pytest.raises(ValueError, match="truncated"):
        agent.run_json("extract", {"type": "object"})


def test_no_arg_tool_with_none_input():
    # A zero-arg tool may arrive with input=None; _execute must not crash.
    @tool
    def ping() -> str:
        """Return pong."""
        return "pong"

    client = StubClient(
        [
            response(
                [SimpleNamespace(type="tool_use", name="ping", input=None, id="t0")],
                stop_reason="tool_use",
            ),
            response([text_block("done")]),
        ]
    )
    agent = Agent(tools=[ping], client=client)
    assert agent.run("ping it") == "done"
    assert client.calls[1]["messages"][-1]["content"][0]["content"] == "pong"


def test_autonomous_run_is_reusable_without_state_leak():
    # First run completes; a second run on the SAME instance must start fresh.
    client = StubClient(
        [
            response([tool_use_block("complete_task", {"summary": "one"})], stop_reason="tool_use"),
            response([tool_use_block("complete_task", {"summary": "two"})], stop_reason="tool_use"),
        ]
    )
    agent = AutonomousAgent(client=client)
    first = agent.run("goal one")
    second = agent.run("goal two")
    assert first.result == "one"
    assert second.result == "two"
    # Second run's history starts with its own goal, not the first run's.
    second_first_msg = client.calls[1]["messages"][0]["content"]
    assert "goal two" in second_first_msg
    assert "goal one" not in second_first_msg
    # Usage is per-run, not cumulative.
    assert second.steps == 1


def test_autonomous_nudges_then_stops_at_budget():
    # Agent keeps ending its turn without finishing; budget should stop it.
    client = StubClient([response([text_block("thinking...")]) for _ in range(3)])
    agent = AutonomousAgent(tools=[echo], client=client)
    result = agent.run("never-ending", max_steps=3)
    assert result.completed is False
    assert result.steps == 3
