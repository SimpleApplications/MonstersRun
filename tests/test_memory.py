"""Tests for the persistent MemoryStore and its tools."""

import pytest

from project_june.memory import MemoryError, MemoryStore, memory_tools


def test_write_read_roundtrip(tmp_path):
    store = MemoryStore(tmp_path)
    store.write("facts/user", "name is Alice")
    assert store.read("facts/user") == "name is Alice"


def test_append_creates_and_extends(tmp_path):
    store = MemoryStore(tmp_path)
    store.append("log", "first")
    store.append("log", "second")
    assert store.read("log") == "first\nsecond"


def test_list_and_delete(tmp_path):
    store = MemoryStore(tmp_path)
    store.write("a.md", "x")
    store.write("nested/b.md", "y")
    assert store.list() == ["a.md", "nested/b.md"]
    assert store.delete("a.md") is True
    assert store.delete("a.md") is False
    assert store.list() == ["nested/b.md"]


def test_read_missing_raises(tmp_path):
    with pytest.raises(MemoryError):
        MemoryStore(tmp_path).read("nope")


def test_path_traversal_rejected(tmp_path):
    store = MemoryStore(tmp_path / "root")
    for bad in ["../escape", "../../etc/passwd", "nested/../../escape"]:
        with pytest.raises(MemoryError):
            store.write(bad, "x")


def test_absolute_key_is_neutralized_into_root(tmp_path):
    # A leading slash is stripped, so "/abs/x" lands safely inside the store.
    store = MemoryStore(tmp_path / "root")
    store.write("/abs/x", "contained")
    assert store.read("abs/x") == "contained"
    assert store.list() == ["abs/x"]


def test_empty_key_rejected(tmp_path):
    with pytest.raises(MemoryError):
        MemoryStore(tmp_path).write("   ", "x")


def test_memory_tools_bind_to_store(tmp_path):
    store = MemoryStore(tmp_path)
    tools = {t.name: t for t in memory_tools(store)}
    assert set(tools) == {"memory_write", "memory_append", "memory_read", "memory_list"}

    assert "saved" in tools["memory_write"].run(key="note", content="hello")
    assert tools["memory_read"].run(key="note") == "hello"
    tools["memory_append"].run(key="note", content="world")
    assert tools["memory_read"].run(key="note") == "hello\nworld"
    assert "note" in tools["memory_list"].run()
