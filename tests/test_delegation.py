"""Tests for agent-as-tool delegation (stub client, no network)."""

from types import SimpleNamespace

from project_june import Agent, agent_tool, tool


def text_block(t):
    return SimpleNamespace(type="text", text=t)


def tool_use_block(name, inp, id="t"):
    return SimpleNamespace(type="tool_use", name=name, input=inp, id=id)


def response(content, stop_reason="tool_use"):
    return SimpleNamespace(content=content, stop_reason=stop_reason, stop_details=None, usage=None)


def test_agent_tool_builds_expected_schema():
    t = agent_tool("research", "Delegate research.", max_steps=3)
    assert t.name == "research"
    assert t.input_schema["required"] == ["task"]
    assert t.input_schema["properties"]["task"]["type"] == "string"


def test_delegated_subagent_runs_and_returns_result():
    # The sub-agent completes immediately via complete_task.
    class SubClient:
        def __init__(self):
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            return response(
                [tool_use_block("complete_task", {"summary": "subtask done: 42"})]
            )

    t = agent_tool("worker", "Do a subtask.", client=SubClient(), max_steps=3)
    out = t.run(task="compute the answer")
    assert out == "subtask done: 42"


def test_coordinator_delegates_to_subagent_end_to_end():
    # One stub client serves BOTH the coordinator and the delegated sub-agent.
    # Sequence of create() calls:
    #   1) coordinator asks to call the 'worker' tool
    #   2) sub-agent (inside the tool) completes its task
    #   3) coordinator gives the final answer
    scripted = [
        response([tool_use_block("worker", {"task": "do it"})]),
        response([tool_use_block("complete_task", {"summary": "worker result"})]),
        response([text_block("Coordinator: the worker said 'worker result'.")],
                 stop_reason="end_turn"),
    ]

    class SharedClient:
        def __init__(self):
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            return scripted.pop(0)

    client = SharedClient()
    worker = agent_tool("worker", "Delegate a subtask.", client=client, max_steps=3)
    coordinator = Agent(tools=[worker], client=client)
    final = coordinator.run("Delegate the work and summarize.")
    assert "worker result" in final


def test_unused_extra_tools_accepted():
    @tool
    def noop() -> str:
        """No-op."""
        return "ok"

    t = agent_tool("w", "desc", tools=[noop])
    assert t.name == "w"
