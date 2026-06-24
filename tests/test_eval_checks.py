"""Tests for the eval check combinators and matchers (no network)."""

from project_june import RunResult, Usage
from project_june.evals import (
    any_of,
    completed,
    contains,
    cost_under,
    is_json,
    matches,
    negate,
    steps_under,
)


def result(text="hello world", completed_=True, steps=2, cost_model="claude-opus-4-8"):
    return RunResult(
        completed=completed_,
        result=text,
        steps=steps,
        usage=Usage(input_tokens=10, output_tokens=5, turns=steps),
        model=cost_model,
    )


def passed(check, r):
    out = check(r)
    return out[0] if isinstance(out, tuple) else out


def test_matches_regex():
    assert passed(matches(r"\bworld\b"), result()) is True
    assert passed(matches(r"\d{4}"), result()) is False


def test_is_json():
    assert passed(is_json(), result('{"a": 1}')) is True
    assert passed(is_json(), result("not json")) is False


def test_any_of():
    check = any_of(contains("nope"), contains("world"))
    assert passed(check, result()) is True
    assert passed(any_of(contains("x"), contains("y")), result()) is False


def test_negate():
    assert passed(negate(contains("absent")), result()) is True
    assert passed(negate(contains("world")), result()) is False


def test_cost_and_steps_bounds():
    r = result(steps=3)
    assert passed(steps_under(5), r) is True
    assert passed(steps_under(2), r) is False
    # cost is tiny but > 0 for a known model
    assert passed(cost_under(1.0), r) is True
    assert passed(cost_under(0.0), r) is False


def test_completed_check():
    assert passed(completed(), result(completed_=True)) is True
    assert passed(completed(), result(completed_=False)) is False
