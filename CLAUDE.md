# Project June

A Python framework for building **independent (autonomous) Claude agents** on the
Anthropic Claude API. Hand an agent a goal and a set of tools; it plans, calls
tools, and decides for itself when the goal is done.

## Commands

```bash
pip install -e ".[dev]"     # install package + dev tools (pytest, ruff)
pytest -q                   # run the test suite (no network; uses a stub client)
ruff check src tests        # lint
june "a one-off task"       # run a single prompt via the CLI
june --goal "pursue this"   # run an independent agent to completion
```

Tests require **no** network or API key — they drive the agent loops with a
stubbed client (`tests/test_agent.py`). Only the CLI and `examples/` make real
API calls, and those need `ANTHROPIC_API_KEY`.

## Architecture

```
src/project_june/
  agent.py          Agent — one user turn to completion (the tool-use loop) +
                    run_json (one-shot structured output)
  autonomous.py     AutonomousAgent — pursues a goal across turns, self-terminates
                    via a built-in complete_task tool; returns a RunResult
  orchestrator.py   Orchestrator — runs many independent agents concurrently;
                    synthesize() for fan-out -> combine
  memory.py         MemoryStore + memory_tools — persistent, path-safe notes
  usage.py          Usage — token/cost accounting (per-model price table)
  tracing.py        save_run — persist a run (transcript + usage + cost) to JSON
  config.py         AgentConfig (model, system, effort, thinking, cache, limits)
  tools.py          Tool + @tool decorator (JSON schema from type hints + docstring)
  builtin_tools.py  Example tools: current_time, calculate, read_file
  cli.py            `june` entry point (chat / one-off / --goal / --goals)
tests/              Stub-client tests — no network (39 tests)
examples/           Runnable examples (require a real API key)
docs/architecture.md  Layer-by-layer design overview
```

The agent loop is **manual on purpose** (not the SDK tool runner): it gives one
readable place to log steps, gate tool execution, cap iterations, and inspect
usage. `AutonomousAgent` builds on `Agent` for cross-turn goal pursuit;
`Orchestrator` runs many of those concurrently. Layering: Orchestrator →
AutonomousAgent → Agent → tools/memory → usage/tracing → SDK.

## Conventions

- **Model:** default to `claude-opus-4-8` with adaptive thinking on. Override via
  `AgentConfig(model=...)` or the `CLAUDE_AGENT_MODEL` env var. Do not downgrade
  the model without a stated reason.
- **Tools:** define them as plain functions with type hints + a Google-style
  `Args:` docstring, decorated with `@tool`. Keep tool functions pure-ish and
  return strings (or values that stringify cleanly).
- **Tool inputs:** always treat them as model output — validate before acting
  (see `calculate`'s character allowlist for the pattern).
- **Errors:** surface tool failures back to the model (`is_error: True`) so it can
  recover, rather than raising out of the loop.
- **Style:** match the surrounding code; line length 100; run `ruff` before
  committing.

## Claude API notes

- Adaptive thinking only on Opus 4.x: `thinking={"type": "adaptive"}`. Do **not**
  use `budget_tokens` (removed on 4.7/4.8 — returns 400).
- Effort lives under `output_config={"effort": "..."}` (`low`/`medium`/`high`/`max`).
- Always check `stop_reason == "refusal"` before reading `response.content`.
- Stream when `max_tokens` is large; the current defaults stay under that bound.
