"""A small evaluation harness for agents.

Define a suite of `EvalCase`s — a goal plus a check on the resulting `RunResult` —
and `run_eval` runs them concurrently (via the `Orchestrator`) and reports a pass
rate, per-case detail, and total cost. This is how you keep an agent reliable as
you change prompts, tools, or models.

    suite = [
        EvalCase("math", "Compute 6*7 and report it.", check=contains("42")),
        EvalCase("done", "Say hello.", check=completed()),
    ]
    report = run_eval(suite, tools=DEFAULT_TOOLS)
    print(report.summary())
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

import anthropic

from .autonomous import RunResult
from .config import AgentConfig
from .orchestrator import Orchestrator, Task
from .tools import Tool
from .usage import Usage

# A check returns either a bool or a (passed, detail) tuple.
Check = Callable[[RunResult], "bool | tuple[bool, str]"]


@dataclass
class EvalCase:
    name: str
    goal: str
    check: Check
    tools: list[Tool] = field(default_factory=list)
    max_steps: int = 8


@dataclass
class EvalResult:
    name: str
    passed: bool
    detail: str
    result: RunResult


@dataclass
class EvalReport:
    results: list[EvalResult]

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return len(self.results) - self.passed

    @property
    def pass_rate(self) -> float:
        return self.passed / len(self.results) if self.results else 0.0

    @property
    def usage(self) -> Usage:
        total = Usage()
        for r in self.results:
            total = total + r.result.usage
        return total

    @property
    def cost(self) -> float:
        return sum(r.result.cost for r in self.results)

    def summary(self) -> str:
        lines = [
            f"{'PASS' if r.passed else 'FAIL'}  {r.name}"
            + (f"  — {r.detail}" if r.detail else "")
            for r in self.results
        ]
        lines.append(
            f"\n{self.passed}/{len(self.results)} passed "
            f"({self.pass_rate:.0%}), ${self.cost:.4f}"
        )
        return "\n".join(lines)


def _normalize(outcome: "bool | tuple[bool, str]") -> tuple[bool, str]:
    if isinstance(outcome, tuple):
        return bool(outcome[0]), str(outcome[1])
    return bool(outcome), ""


def run_eval(
    cases: list[EvalCase],
    config: AgentConfig | None = None,
    tools: list[Tool] | None = None,
    client: anthropic.Anthropic | None = None,
    max_workers: int = 8,
) -> EvalReport:
    """Run an eval suite concurrently and return a report.

    `tools` are shared across cases; a case's own `tools` are added on top.
    """
    shared = tools or []
    orch = Orchestrator(config=config or AgentConfig(), client=client, max_workers=max_workers)
    tasks = [
        Task(goal=c.goal, tools=shared + c.tools, max_steps=c.max_steps, label=c.name)
        for c in cases
    ]
    fan = orch.run(tasks)

    results: list[EvalResult] = []
    for case, run_result in zip(cases, fan.results):
        try:
            passed, detail = _normalize(case.check(run_result))
        except Exception as exc:  # a check that throws is a failure, not a crash
            passed, detail = False, f"check raised: {exc}"
        results.append(EvalResult(case.name, passed, detail, run_result))
    return EvalReport(results=results)


# --- ready-made checks -------------------------------------------------------

def contains(substring: str, case_sensitive: bool = False) -> Check:
    """Pass if the agent's final result contains `substring`."""

    def check(r: RunResult) -> tuple[bool, str]:
        hay = r.result if case_sensitive else r.result.lower()
        needle = substring if case_sensitive else substring.lower()
        ok = needle in hay
        return ok, "" if ok else f"missing {substring!r}"

    return check


def completed() -> Check:
    """Pass if the agent reported the goal complete."""

    def check(r: RunResult) -> tuple[bool, str]:
        return r.completed, "" if r.completed else "did not complete"

    return check


def all_of(*checks: Check) -> Check:
    """Pass only if every check passes; reports the first failure detail."""

    def check(r: RunResult) -> tuple[bool, str]:
        for c in checks:
            ok, detail = _normalize(c(r))
            if not ok:
                return False, detail
        return True, ""

    return check


def any_of(*checks: Check) -> Check:
    """Pass if at least one check passes."""

    def check(r: RunResult) -> tuple[bool, str]:
        details = []
        for c in checks:
            ok, detail = _normalize(c(r))
            if ok:
                return True, ""
            details.append(detail)
        return False, "none passed: " + "; ".join(d for d in details if d)

    return check


def negate(inner: Check) -> Check:
    """Pass if the inner check fails (logical NOT)."""

    def check(r: RunResult) -> tuple[bool, str]:
        ok, _ = _normalize(inner(r))
        return (not ok), "" if not ok else "unexpectedly passed"

    return check


def matches(pattern: str) -> Check:
    """Pass if the agent's result matches the regex `pattern` (search)."""
    compiled = re.compile(pattern)

    def check(r: RunResult) -> tuple[bool, str]:
        ok = compiled.search(r.result) is not None
        return ok, "" if ok else f"no match for /{pattern}/"

    return check


def is_json() -> Check:
    """Pass if the agent's result parses as JSON."""

    def check(r: RunResult) -> tuple[bool, str]:
        try:
            json.loads(r.result)
            return True, ""
        except (ValueError, TypeError) as exc:
            return False, f"not JSON: {exc}"

    return check


def cost_under(max_usd: float) -> Check:
    """Pass if the run cost less than `max_usd`."""

    def check(r: RunResult) -> tuple[bool, str]:
        ok = r.cost < max_usd
        return ok, "" if ok else f"cost ${r.cost:.4f} >= ${max_usd:.4f}"

    return check


def steps_under(max_steps: int) -> Check:
    """Pass if the run used fewer than `max_steps` model turns."""

    def check(r: RunResult) -> tuple[bool, str]:
        ok = r.steps < max_steps
        return ok, "" if ok else f"{r.steps} steps >= {max_steps}"

    return check
