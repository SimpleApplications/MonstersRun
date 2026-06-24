"""Tests for the evaluation harness (stub client, no network)."""

from types import SimpleNamespace

from project_june import EvalCase, all_of, completed, contains, run_eval


def complete_block(summary):
    return SimpleNamespace(
        type="tool_use", name="complete_task", input={"summary": summary}, id="tu"
    )


def usage():
    return SimpleNamespace(
        input_tokens=10, output_tokens=5,
        cache_read_input_tokens=0, cache_creation_input_tokens=0,
    )


class GoalEchoClient:
    """Each agent completes immediately, echoing its goal as the summary."""

    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        goal = kwargs["messages"][0]["content"]
        # Echo the goal text so checks can match on it.
        return SimpleNamespace(
            content=[complete_block(f"result for: {goal}")],
            stop_reason="tool_use",
            stop_details=None,
            usage=usage(),
        )


def test_run_eval_reports_pass_and_fail():
    cases = [
        EvalCase("has-X", "Produce the letter combo ZZZ.", check=contains("ZZZ")),
        EvalCase("completes", "Do something.", check=completed()),
        EvalCase("missing", "Whatever.", check=contains("not-present-anywhere")),
    ]
    report = run_eval(cases, client=GoalEchoClient())

    by_name = {r.name: r for r in report.results}
    assert by_name["has-X"].passed is True
    assert by_name["completes"].passed is True
    assert by_name["missing"].passed is False
    assert "missing" in by_name["missing"].detail

    assert report.passed == 2
    assert report.failed == 1
    assert abs(report.pass_rate - 2 / 3) < 1e-9
    assert report.cost > 0
    assert "2/3 passed" in report.summary()


def test_all_of_combines_checks():
    cases = [EvalCase("combo", "make ABC and DEF appear", check=all_of(
        contains("ABC"), completed()))]
    report = run_eval(cases, client=GoalEchoClient())
    assert report.results[0].passed is True


def test_check_that_raises_is_a_failure():
    def boom(_r):
        raise RuntimeError("kaboom")

    report = run_eval([EvalCase("boom", "go", check=boom)], client=GoalEchoClient())
    assert report.results[0].passed is False
    assert "kaboom" in report.results[0].detail
