"""Tests for run persistence / tracing."""

import json
from types import SimpleNamespace

from project_june import RunResult, Usage
from project_june.tracing import block_to_dict, run_to_dict, save_run, transcript_to_dicts


def test_block_to_dict_handles_dicts_and_objects():
    assert block_to_dict({"type": "tool_result", "content": "x"})["type"] == "tool_result"

    text = SimpleNamespace(type="text", text="hello")
    assert block_to_dict(text) == {"type": "text", "text": "hello"}

    tu = SimpleNamespace(type="tool_use", name="echo", input={"a": 1}, id="t1")
    out = block_to_dict(tu)
    assert out["name"] == "echo" and out["input"] == {"a": 1}


def test_transcript_serializes_mixed_messages():
    messages = [
        {"role": "user", "content": "do it"},
        {"role": "assistant", "content": [SimpleNamespace(type="text", text="ok")]},
        {"role": "user", "content": [{"type": "tool_result", "content": "42"}]},
    ]
    dicts = transcript_to_dicts(messages)
    assert dicts[0]["content"] == "do it"
    assert dicts[1]["content"][0]["text"] == "ok"
    assert dicts[2]["content"][0]["content"] == "42"


def make_result():
    return RunResult(
        completed=True,
        result="all done",
        steps=2,
        transcript=[{"role": "user", "content": "go"}],
        usage=Usage(input_tokens=100, output_tokens=50, turns=2),
        model="claude-opus-4-8",
    )


def test_run_to_dict_includes_usage_and_cost():
    d = run_to_dict(make_result())
    assert d["completed"] is True
    assert d["usage"]["input_tokens"] == 100
    assert d["cost_usd"] > 0
    assert d["model"] == "claude-opus-4-8"


def test_save_run_writes_json(tmp_path):
    path = save_run(make_result(), directory=tmp_path, name="myrun")
    assert path.exists()
    loaded = json.loads(path.read_text())
    assert loaded["result"] == "all done"
    assert loaded["steps"] == 2
