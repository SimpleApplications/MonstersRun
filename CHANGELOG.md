# Changelog

All notable changes to Project June are documented here.

## [Unreleased]

### Added
- **Core agent loop** (`Agent`): manual tool-use loop with `run`, `stream`
  (live token streaming), and `run_json` (schema-validated structured output).
  Prompt caching and adaptive thinking on by default; handles `refusal` and
  `pause_turn` stop reasons.
- **Independent agents** (`AutonomousAgent`): goal pursuit across turns with a
  built-in `complete_task` tool and a step budget; returns a `RunResult` with
  usage and estimated cost. Reusable — each run resets state.
- **Concurrent orchestration** (`Orchestrator`, `synthesize`): run many
  independent agents in parallel threads; fan-out → combine.
- **Async** (`AsyncAgent`, `AsyncAutonomousAgent`, `AsyncOrchestrator`): asyncio
  variants for high-concurrency fan-out.
- **Delegation** (`agent_tool`): wrap an agent as a tool so a coordinator can
  spawn focused sub-agents.
- **MCP bridge** (`mcp_tools`, `StaticMCPProvider`): expose any MCP server's
  tools to an agent.
- **Evaluation harness** (`run_eval`, `EvalCase`, `contains`/`completed`/`all_of`):
  score agents against task suites concurrently.
- **Persistent memory** (`MemoryStore`, `memory_tools`): path-safe notes that
  survive across runs.
- **Context management** (`compact_messages`, `AgentConfig.max_context_tokens`):
  keep long histories under a token budget at safe boundaries.
- **Observability** (`Usage`, `save_run`): token/cost accounting and run
  transcript persistence.
- **Tools**: `@tool` decorator (schema from type hints + docstrings); builtin
  `current_time`, `calculate`, `read_file`, `list_directory`, and opt-in
  `write_file`.
- **CLI** (`june`): chat (streaming), one-off, `--goal`, concurrent `--goals`,
  `--memory`, `--save`.
- **Resilience**: `AgentConfig.max_retries` / `request_timeout` wired into the
  SDK client across all entry points.
- **Project setup**: `CLAUDE.md`, SessionStart hook + settings, GitHub Actions
  CI, `py.typed`, `docs/architecture.md`.
- **Tests**: 74 stub-client tests (no network) plus opt-in live API tests.
