claude-agents
=============

A small, flexible framework for building AI agents on the
[Anthropic Claude API](https://docs.claude.com/). Define tools as plain Python
functions, hand them to an `Agent`, and let Claude plan, call tools, and answer —
all driven by a transparent agentic loop you can inspect and extend.

> This project reuses the repository but is unrelated to the original MonstersRun
> contents.

Why this stack
--------------

Python + the official `anthropic` SDK is the most flexible, capable base for
agent work: first-class tool use, streaming, adaptive thinking, and the full
Messages API. Agents default to **`claude-opus-4-8`** with adaptive thinking on.

Features
--------

- **`@tool` decorator** — turns a typed, documented function into an agent tool;
  the JSON schema is generated from your type hints and docstring.
- **Manual agentic loop** — a single, readable place to log every step, gate
  tool execution, cap iterations, and inspect usage.
- **Adaptive thinking + effort control** — sensible, tunable defaults.
- **CLI REPL** — chat with a tool-equipped agent from your terminal.

Install
-------

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # then add your ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=sk-ant-...
```

Quick start
-----------

```python
from claude_agents import Agent, AgentConfig, tool


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

Command line
------------

```bash
claude-agent                      # interactive chat (Ctrl-D or 'exit' to quit)
claude-agent "What time is it in UTC, and what is 47 * 89?"
```

The built-in agent ships with example tools: `current_time`, `calculate`, and
`read_file` (see `src/claude_agents/builtin_tools.py`).

Project layout
--------------

```
src/claude_agents/
  agent.py          # the agentic loop
  config.py         # AgentConfig (model, system, effort, thinking, limits)
  tools.py          # Tool + the @tool decorator (schema from type hints)
  builtin_tools.py  # example tools
  cli.py            # interactive REPL / one-off runner
examples/
  custom_tool.py    # define and use your own tool
```

Defining a tool
---------------

Write a normal function with type hints and a Google-style docstring. The
decorator reads both to build the schema Claude sees:

```python
@tool
def get_weather(city: str, unit: str = "celsius") -> str:
    """Get the current weather for a city.

    Args:
        city: City name, e.g. "Paris".
        unit: "celsius" or "fahrenheit".
    """
    ...
```

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
| `max_iterations` | `25`               | Safety bound on the tool-use loop.               |

License
-------

Apache 2.0 — see [LICENSE](LICENSE).
