# Project June — Architecture

Project June is a layered framework for building independent Claude agents. Each
layer builds on the one below and is independently usable.

```
Orchestrator / AsyncOrchestrator   run many independent agents concurrently
    │
AutonomousAgent   pursue a goal across turns; self-terminate via complete_task
    │               (agent_tool wraps one as a Tool → sub-agents / delegation)
Agent             one user turn → completion (the tool-use loop; + stream, run_json)
    │
tools / memory / mcp   @tool decorator, MemoryStore, mcp_tools, builtin tools
    │
usage / tracing / context   token+cost accounting, transcripts, compaction
    │
anthropic SDK     Messages API (claude-opus-4-8, adaptive thinking, caching)
```

Cross-cutting: `evals.py` (score agents on suites) sits beside the orchestrator;
`aio.py` mirrors the sync stack on `AsyncAnthropic`.

## Layers

### `Agent` (`agent.py`)
The core loop. `run(prompt)` sends the conversation plus tool definitions to the
Messages API, executes any requested tools locally, feeds results back, and
repeats until the model stops calling tools. A **manual** loop (not the SDK tool
runner) so there is one readable place to:

- log every tool call (`on_tool` hook),
- enforce `max_iterations`,
- accumulate token usage,
- handle `refusal` and `pause_turn` stop reasons.

It also exposes `run_json(prompt, schema)` for one-shot structured output via
`output_config.format`.

### `AutonomousAgent` (`autonomous.py`)
Wraps an `Agent` and adds a goal-pursuit loop. The agent is given a goal and a
built-in `complete_task` tool; it works across turns and signals completion
itself. A step budget bounds the run. Returns a `RunResult` carrying the outcome,
transcript, token usage, and estimated cost.

### `Orchestrator` (`orchestrator.py`)
Runs N `AutonomousAgent`s concurrently (thread pool, shared thread-safe client),
preserving input order and aggregating usage/cost. `synthesize()` implements the
fan-out → combine pattern: several agents research in parallel, a final agent
merges their findings.

## Cross-cutting

### Tools (`tools.py`, `builtin_tools.py`, `memory.py`)
`@tool` turns a typed, documented function into a tool, generating the JSON schema
from type hints and the docstring's `Args:` block. `MemoryStore` + `memory_tools`
give agents persistent, path-safe notes across runs.

### Observability (`usage.py`, `tracing.py`)
`Usage` accumulates token counts and estimates cost from a per-model price table
(cache reads at 0.1×, writes at 1.25× of input price). `save_run` serializes a
run — outcome, usage, cost, and a readable transcript — to `.june_runs/`.

## Design choices

- **Default model `claude-opus-4-8`** with adaptive thinking and prompt caching
  on by default — the most capable setup for agentic work.
- **Tool inputs are untrusted** — validate before acting (see `calculate`'s
  allowlist and `MemoryStore`'s path confinement).
- **Errors return to the model** (`is_error: True`) so it can recover, rather than
  raising out of the loop.
- **Stateless API** — the full message history is resent each turn; prompt caching
  makes the repeated prefix cheap.
