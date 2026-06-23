"""Example: an independent agent that pursues a goal to completion.

Run with:  python examples/autonomous_goal.py
Requires:  ANTHROPIC_API_KEY in the environment.
"""

from project_june import AutonomousAgent, AgentConfig
from project_june.builtin_tools import DEFAULT_TOOLS


def main() -> None:
    agent = AutonomousAgent(
        tools=DEFAULT_TOOLS,
        config=AgentConfig(system="You are a meticulous research assistant."),
        on_step=lambda step, resp: print(f"[step {step}] stop_reason={resp.stop_reason}"),
        on_tool=lambda name, inp, out: print(f"  tool {name} -> {out[:60]}"),
    )

    result = agent.run(
        "Work out what 17 factorial is using the calculator tool, then report "
        "both the value and the current UTC time.",
        max_steps=8,
    )

    print(f"\ncompleted={result.completed} in {result.steps} steps")
    print(result.result)


if __name__ == "__main__":
    main()
