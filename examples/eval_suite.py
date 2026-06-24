"""Example: score an agent against a small eval suite.

Run with:  python examples/eval_suite.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

from project_june import EvalCase, all_of, completed, contains, run_eval
from project_june.builtin_tools import DEFAULT_TOOLS


def main() -> None:
    suite = [
        EvalCase(
            "factorial",
            "Use the calculator to compute 5 factorial (5*4*3*2*1) and report it.",
            check=all_of(completed(), contains("120")),
        ),
        EvalCase(
            "arithmetic",
            "What is 144 divided by 12? Use the calculator and report the number.",
            check=contains("12"),
        ),
        EvalCase(
            "time",
            "Report the current UTC time using your tools.",
            check=all_of(completed(), contains("UTC")),
        ),
    ]

    report = run_eval(suite, tools=DEFAULT_TOOLS, max_workers=3)
    print(report.summary())


if __name__ == "__main__":
    main()
