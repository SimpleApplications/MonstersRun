"""Example: fan a question out to independent agents, then synthesize.

Three agents research sub-questions in parallel; a fourth combines their
findings into one answer.

Run with:  python examples/multi_agent.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

from project_june import Orchestrator
from project_june.orchestrator import synthesize


def main() -> None:
    orch = Orchestrator(
        max_workers=3,
        on_result=lambda label, r: print(
            f"[{label}] done in {r.steps} steps (${r.cost:.4f})"
        ),
    )

    sub_questions = [
        "In two sentences, what is prompt caching and when does it help?",
        "In two sentences, what is adaptive thinking on Claude models?",
        "In two sentences, what is a tool-use agentic loop?",
    ]

    fan_out = orch.map_goals(sub_questions, max_steps=3)
    print(f"\nfan-out total cost: ${fan_out.cost:.4f}")

    final = synthesize(
        "Give me a short primer on building agents with the Claude API.",
        fan_out,
    )
    print("\n=== synthesized answer ===\n")
    print(final.result)


if __name__ == "__main__":
    main()
