Project June
============

A Python framework for building **independent (autonomous) Claude agents** on the
[Anthropic Claude API](https://docs.claude.com/). Define tools as plain Python
functions, hand an agent a goal, and let it plan, call tools, and decide for
itself when the goal is done — driven by a transparent agentic loop you can
inspect and extend.

> This repository was repurposed from an earlier project ("MonstersRun"); none of
> that content remains.

Why this stack
--------------

Python + the official `anthropic` SDK is the most flexible, capable base for
agent work: first-class tool use, streaming, adaptive thinking, and the full
Messages API. Agents default to **`claude-opus-4-8`** with adaptive thinking on.

Features
--------

- **`@tool` decorator** — turns a typed, documented function into an agent tool;
  the JSON schema is generated from your type hints and docstring.
- **`Agent`** — a transparent manual agentic loop: one place to log every step,
  gate tool execution, cap iterations, and inspect usage.
- **`AutonomousAgent`** — give it a *goal*; it works across turns and terminates
  itself via a built-in `complete_task` tool, returning a `RunResult`.
- **CLI** — chat, one-off prompts, or autonomous goals from the terminal.
- **Tests with no network** — the agent loops are covered by a stub client.

Install
-------

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # then add your ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=sk-ant-...
```

Quick start — a tool-equipped agent
-----------------------------------

```python
from project_june import Agent, AgentConfig, tool


@tool
def word_count(text: str) -> int:
    """Count the number of words in a piece of text.

    Args:
        text: The text to count words in.
    """
    return len(text.split())


agent = Agent(tools=[word_count], config=AgentConfig(system="You are concise."))
print(agent.run("How many words are in 'the quick brown fox'?"))
```

An independent agent
--------------------

```python
from project_june import AutonomousAgent
from project_june.builtin_tools import DEFAULT_TOOLS

agent = AutonomousAgent(tools=DEFAULT_TOOLS)
result = agent.run("Compute 17! with the calculator and report the UTC time.")
print(result.completed, result.steps)
print(result.result)
```

Command line
------------

```bash
june                                  # interactive chat
june "What is 47 * 89, and the UTC time?"   # one-off
june --goal "Compute 17! and report it"     # run an independent agent to completion
```

Built-in example tools: `current_time`, `calculate`, `read_file`
(`src/project_june/builtin_tools.py`).

Project layout
--------------

```
src/project_june/
  agent.py          # the core agentic loop
  autonomous.py     # AutonomousAgent + RunResult (independent goal pursuit)
  config.py         # AgentConfig (model, system, effort, thinking, limits)
  tools.py          # Tool + the @tool decorator (schema from type hints)
  builtin_tools.py  # example tools
  cli.py            # `june` entry point
tests/              # stub-client tests (no network)
examples/           # runnable examples (require a real API key)
```

Development
-----------

```bash
pytest -q                   # 12 tests, no network needed
ruff check src tests        # lint
```

Claude Code setup
-----------------

- `CLAUDE.md` — project memory loaded into every session (architecture,
  commands, conventions).
- `.claude/hooks/session-start.sh` + `.claude/settings.json` — a SessionStart
  hook that installs the package and dev tools in fresh
  [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web)
  containers, so `pytest`/`ruff` work immediately.

Configuration
-------------

`AgentConfig` exposes the knobs worth tuning:

| Field            | Default            | Notes                                            |
|------------------|--------------------|--------------------------------------------------|
| `model`          | `claude-opus-4-8`  | Or set `CLAUDE_AGENT_MODEL`.                      |
| `system`         | `None`             | The agent's role / behavior.                     |
| `max_tokens`     | `16000`            | Per-response output cap.                          |
| `effort`         | `"high"`           | `low` / `medium` / `high` / `max`.               |
| `thinking`       | `True`             | Adaptive thinking.                               |
| `max_iterations` | `25`               | Safety bound on the per-turn tool-use loop.      |

License
-------

Apache 2.0 — see [LICENSE](LICENSE).
