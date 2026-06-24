"""Smoke tests for CLI argument parsing (no network)."""

from project_june.cli import _parser


def test_parser_defaults():
    args = _parser().parse_args(["hello", "world"])
    assert args.prompt == ["hello", "world"]
    assert args.effort == "high"
    assert args.max_steps == 12
    assert args.memory is False


def test_parser_goal_flags():
    args = _parser().parse_args(["--goal", "do it", "--memory", "--save", "--effort", "low"])
    assert args.goal == "do it"
    assert args.memory is True
    assert args.save is True
    assert args.effort == "low"


def test_parser_multi_goals():
    args = _parser().parse_args(["--goals", "a", "b", "c", "--max-steps", "5"])
    assert args.goals == ["a", "b", "c"]
    assert args.max_steps == 5
