"""Tests for the @tool decorator and built-in tools (no network needed)."""

from typing import Literal

from project_june import tool
from project_june.builtin_tools import calculate, current_time, read_file


def test_schema_from_signature():
    @tool
    def get_weather(city: str, unit: str = "celsius") -> str:
        """Get the current weather for a city.

        Args:
            city: City name.
            unit: Temperature unit.
        """
        return "sunny"

    assert get_weather.name == "get_weather"
    assert get_weather.description == "Get the current weather for a city."
    schema = get_weather.input_schema
    assert schema["type"] == "object"
    assert schema["properties"]["city"]["type"] == "string"
    assert schema["properties"]["city"]["description"] == "City name."
    # Only the parameter without a default is required.
    assert schema["required"] == ["city"]
    assert schema["additionalProperties"] is False


def test_literal_becomes_enum():
    @tool
    def pick(mode: Literal["fast", "slow"]) -> str:
        """Pick a mode.

        Args:
            mode: The mode to use.
        """
        return mode

    assert pick.input_schema["properties"]["mode"]["enum"] == ["fast", "slow"]


def test_int_return_coerced_to_string():
    @tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    assert add.input_schema["properties"]["a"]["type"] == "integer"
    assert add.run(a=2, b=3) == "5"  # run() stringifies for tool_result


def test_calculate_blocks_non_arithmetic():
    assert calculate.run(expression="2 * (3 + 4)") == "14"
    assert "only contain" in calculate.run(expression="__import__('os')")


def test_current_time_runs():
    assert "UTC" in current_time.run(timezone="UTC")


def test_read_file_missing(tmp_path):
    assert "no such file" in read_file.run(path=str(tmp_path / "nope.txt"))


def test_read_file_truncates(tmp_path):
    p = tmp_path / "big.txt"
    p.write_text("x" * 100, encoding="utf-8")
    out = read_file.run(path=str(p), max_chars=10)
    assert "truncated" in out
