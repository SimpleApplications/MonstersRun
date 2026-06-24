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
  agent.py          Agent — one user turn to completion (tool-use loop) +
                    run_json (structured output) + stream (live tokens)
  autonomous.py     AutonomousAgent — pursues a goal across turns, self-terminates
                    via a built-in complete_task tool; returns a RunResult
  orchestrator.py   Orchestrator — runs many independent agents concurrently
                    (threads); synthesize() for fan-out -> combine
  aio.py            AsyncAgent / AsyncAutonomousAgent / AsyncOrchestrator (asyncio)
  delegation.py     agent_tool — wrap an AutonomousAgent as a Tool (sub-agents)
  evals.py          run_eval + EvalCase + checks — score agents on task suites
  mcp_bridge.py     mcp_tools — expose any MCP server's tools to an agent
  memory.py         MemoryStore + memory_tools — persistent, path-safe notes
  context.py        compact_messages — keep long histories under a token budget
  usage.py          Usage — token/cost accounting (per-model price table)
  tracing.py        save_run — persist a run (transcript + usage + cost) to JSON
  config.py         AgentConfig (model, system, effort, thinking, cache,
                    max_context_tokens, max_retries, limits)
  tools.py          Tool + @tool decorator (JSON schema from type hints + docstring)
  builtin_tools.py  Example tools: current_time, calculate, read_file,
                    list_directory (DEFAULT_TOOLS); write_file (WRITE_TOOLS)
  cli.py            `june` entry point (chat / one-off / --goal / --goals)
tests/              Stub-client tests — no network (74 tests; live tests opt-in)
examples/           Runnable examples (require a real API key)
docs/architecture.md  Layer-by-layer design overview
```

The agent loop is **manual on purpose** (not the SDK tool runner): it gives one
readable place to log steps, gate tool execution, cap iterations, and inspect
usage. `AutonomousAgent` builds on `Agent` for cross-turn goal pursuit;
`Orchestrator` (threads) and `AsyncOrchestrator` (asyncio) run many of those
concurrently; `agent_tool` lets one agent delegate to others. Layering:
Orchestrator → AutonomousAgent → Agent → tools/memory/mcp → usage/tracing/context
→ SDK.

When adding a module: mirror it across sync/async if it touches the loop, keep
the no-network stub-test pattern, export it from `__init__.py`, and run
`ruff check src tests` + `pytest -q` before committing.

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
