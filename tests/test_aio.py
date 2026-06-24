"""Tests for the async agents/orchestrator (no network, no pytest-asyncio).

We drive coroutines with asyncio.run() and a stub whose messages.create is an
async function.
"""

import asyncio
import threading
from types import SimpleNamespace

from project_june import AsyncAgent, AsyncOrchestrator, Task
from project_june.aio import AsyncAutonomousAgent


def text_block(t):
    return SimpleNamespace(type="text", text=t)


def tool_use_block(name, inp, id="t"):
    return SimpleNamespace(type="tool_use", name=name, input=inp, id=id)


def response(content, stop_reason="end_turn", usage=None):
    return SimpleNamespace(content=content, stop_reason=stop_reason, stop_details=None, usage=usage)


def usage(inp=100, out=50):
    return SimpleNamespace(
        input_tokens=inp, output_tokens=out,
        cache_read_input_tokens=0, cache_creation_input_tokens=0,
    )


class AsyncStub:
    def __init__(self, responses, delay=0.0):
        self._responses = list(responses)
        self._delay = delay
        self.lock = threading.Lock()
        self.in_flight = 0
        self.max_in_flight = 0
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        with self.lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(self._delay)
        with self.lock:
            self.in_flight -= 1
        return self._responses.pop(0)


class GoalEchoStub:
    """Each create() returns a complete_task echoing the goal text."""

    def __init__(self, delay=0.01):
        self._delay = delay
        self.lock = threading.Lock()
        self.in_flight = 0
        self.max_in_flight = 0
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        with self.lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(self._delay)
        goal = kwargs["messages"][0]["content"]
        with self.lock:
            self.in_flight -= 1
        return response(
            [tool_use_block("complete_task", {"summary": f"done: {goal[:18]}"})],
            stop_reason="tool_use",
            usage=usage(),
        )


def test_async_agent_runs_tool_then_answers():
    client = AsyncStub([
        response([tool_use_block("noop", {})], stop_reason="tool_use"),
        response([text_block("done")]),
    ])

    # 'noop' is unknown -> error tool_result, but the loop recovers on next turn.
    agent = AsyncAgent(client=client)
    out = asyncio.run(agent.run("go"))
    assert out == "done"


class _AsyncStreamCtx:
    def __init__(self, chunks, final):
        self._chunks = chunks
        self._final = final

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def text_stream(self):
        async def gen():
            for c in self._chunks:
                yield c
        return gen()

    async def get_final_message(self):
        return self._final


class AsyncStreamStub:
    def __init__(self, turns):
        self._turns = list(turns)
        self.messages = SimpleNamespace(stream=self._stream)

    def _stream(self, **kwargs):
        chunks, final = self._turns.pop(0)
        return _AsyncStreamCtx(chunks, final)


def test_async_agent_stream_emits_text_and_runs_tools():
    collected = []
    client = AsyncStreamStub(
        [
            (["Let me ", "check."], response(
                [tool_use_block("noop", {})], stop_reason="tool_use")),
            (["All ", "done."], response([text_block("All done.")])),
        ]
    )
    agent = AsyncAgent(client=client)
    out = asyncio.run(agent.stream("go", on_text=collected.append))
    assert out == "All done."
    assert "".join(collected) == "Let me check.All done."


def test_async_autonomous_completes():
    client = GoalEchoStub(delay=0)
    agent = AsyncAutonomousAgent(client=client)
    result = asyncio.run(agent.run("achieve X"))
    assert result.completed
    assert "achieve" in result.result
    assert result.usage.input_tokens == 100


def test_async_autonomous_fires_on_step():
    # Parity with the sync AutonomousAgent's on_step hook.
    seen = []
    client = GoalEchoStub(delay=0)
    agent = AsyncAutonomousAgent(client=client, on_step=lambda step, resp: seen.append(step))
    asyncio.run(agent.run("do it"))
    assert seen == [1]


def test_async_orchestrator_runs_concurrently():
    client = GoalEchoStub(delay=0.05)
    orch = AsyncOrchestrator(client=client, max_concurrency=8)
    out = asyncio.run(orch.map_goals([f"goal {i}" for i in range(6)]))
    assert len(out.results) == 6
    assert out.all_completed
    # Order preserved.
    for i, r in enumerate(out.results):
        assert f"goal {i}"[:18] in r.result
    # Genuinely concurrent.
    assert client.max_in_flight > 1


def test_async_orchestrator_respects_concurrency_cap():
    client = GoalEchoStub(delay=0.03)
    orch = AsyncOrchestrator(client=client, max_concurrency=2)
    asyncio.run(orch.run([Task(goal=f"g{i}") for i in range(6)]))
    assert client.max_in_flight <= 2
