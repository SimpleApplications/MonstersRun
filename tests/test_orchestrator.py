"""Tests for concurrent multi-agent orchestration (stub client, no network)."""

import threading
import time
from types import SimpleNamespace

from project_june import Orchestrator, Task
from project_june.orchestrator import synthesize


def complete_block(summary):
    return SimpleNamespace(
        type="tool_use", name="complete_task", input={"summary": summary}, id="tu"
    )


def response(content, stop_reason="tool_use", usage=None):
    return SimpleNamespace(
        content=content, stop_reason=stop_reason, stop_details=None, usage=usage
    )


def usage(inp=100, out=50):
    return SimpleNamespace(
        input_tokens=inp,
        output_tokens=out,
        cache_read_input_tokens=0,
        cache_creation_input_tokens=0,
    )


class ConcurrentStubClient:
    """Thread-safe stub. Each create() returns a complete_task echoing the goal,
    and records how many calls were in-flight concurrently.
    """

    def __init__(self, delay=0.05):
        self.delay = delay
        self._lock = threading.Lock()
        self.in_flight = 0
        self.max_in_flight = 0
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        time.sleep(self.delay)
        # Echo the goal text back so each agent's result is distinguishable.
        goal = kwargs["messages"][0]["content"]
        with self._lock:
            self.in_flight -= 1
        return response([complete_block(f"done: {goal[:20]}")], usage=usage())


def test_runs_tasks_concurrently_and_preserves_order():
    client = ConcurrentStubClient()
    orch = Orchestrator(client=client, max_workers=4)
    tasks = [Task(goal=f"goal {i}", label=f"t{i}") for i in range(4)]
    out = orch.run(tasks)

    assert len(out.results) == 4
    assert out.all_completed
    # Results stay in submission order.
    for i, r in enumerate(out.results):
        assert f"goal {i}"[:20] in r.result
    assert out.labels == ["t0", "t1", "t2", "t3"]
    # Genuinely concurrent: more than one create() overlapped.
    assert client.max_in_flight > 1


def test_combined_usage_and_cost():
    client = ConcurrentStubClient(delay=0)
    orch = Orchestrator(client=client, max_workers=2)
    out = orch.map_goals(["a", "b", "c"])
    assert out.usage.input_tokens == 300  # 3 agents * 100
    assert out.usage.output_tokens == 150
    # Default model has a price, so cost is positive.
    assert out.cost > 0


def test_on_result_callback_fires_per_task():
    client = ConcurrentStubClient(delay=0)
    seen = []
    orch = Orchestrator(client=client, on_result=lambda label, r: seen.append(label))
    orch.map_goals(["x", "y"])
    assert sorted(seen) == ["task-0", "task-1"]


def test_synthesize_combines_findings():
    client = ConcurrentStubClient(delay=0)
    orch = Orchestrator(client=client)
    fan = orch.map_goals(["research A", "research B"])
    final = synthesize("What did we find?", fan, client=client)
    assert final.completed
