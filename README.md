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
  gate tool execution, cap iterations, and inspect usage. Prompt caching on by
  default; one-shot structured output via `run_json`.
- **`AutonomousAgent`** — give it a *goal*; it works across turns and terminates
  itself via a built-in `complete_task` tool, returning a `RunResult` with token
  usage and estimated cost.
- **`Orchestrator`** — run many independent agents **concurrently** toward
  sub-goals; aggregate results, usage, and cost. `synthesize()` for fan-out →
  combine.
- **Persistent memory** — a path-safe `MemoryStore` + `memory_tools` so agents
  carry learnings across runs.
- **Observability** — `Usage`/cost accounting and `save_run` to persist a run's
  transcript for auditing.
- **CLI** — chat, one-off prompts, single goals, or concurrent multi-goal runs.
- **Tests with no network** — every loop is covered by a stub client (39 tests).

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
print(result.completed, result.steps, f"${result.cost:.4f}")
print(result.result)
```

Many independent agents, concurrently
--------------------------------------

```python
from project_june import Orchestrator
from project_june.orchestrator import synthesize

orch = Orchestrator(max_workers=4)
fan = orch.map_goals([
    "Summarize prompt caching in two sentences.",
    "Summarize adaptive thinking in two sentences.",
    "Summarize tool-use loops in two sentences.",
])
print(f"{len(fan.results)} agents, ${fan.cost:.4f}")
answer = synthesize("Give me a short primer on Claude agents.", fan)
print(answer.result)
```

Persistent memory + structured output
--------------------------------------

```python
from project_june import Agent, AutonomousAgent, MemoryStore, memory_tools

# Agents that remember across runs:
store = MemoryStore(".june_memory")
agent = AutonomousAgent(tools=memory_tools(store))

# One-shot structured extraction:
schema = {"type": "object",
          "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
          "required": ["name", "age"], "additionalProperties": False}
print(Agent().run_json("Extract: Ada Lovelace, 36.", schema))
```

Command line
------------

```bash
june                                        # interactive chat
june "What is 47 * 89, and the UTC time?"   # one-off
june --goal "Compute 17! and report it"     # one independent agent to completion
june --goal "research X" --memory --save    # with persistent memory; save transcript
june --goals "summarize A" "summarize B"    # several independent agents, concurrently
```

Built-in example tools: `current_time`, `calculate`, `read_file`
(`src/project_june/builtin_tools.py`).

Project layout
--------------

```
src/project_june/
  agent.py          # the core agentic loop (+ run_json structured output)
  autonomous.py     # AutonomousAgent + RunResult (independent goal pursuit)
  orchestrator.py   # Orchestrator + synthesize (concurrent multi-agent)
  memory.py         # MemoryStore + memory_tools (persistent, path-safe)
  usage.py          # token/cost accounting
  tracing.py        # save_run (persist run transcripts)
  config.py         # AgentConfig (model, system, effort, thinking, cache, limits)
  tools.py          # Tool + the @tool decorator (schema from type hints)
  builtin_tools.py  # example tools
  cli.py            # `june` entry point
docs/architecture.md  # how the layers fit together
tests/              # stub-client tests (no network)
examples/           # runnable examples (require a real API key)
```

Development
-----------

```bash
pytest -q                   # 39 tests, no network needed
ruff check src tests        # lint
```

See [docs/architecture.md](docs/architecture.md) for how the layers fit together.

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
