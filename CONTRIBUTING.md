# Contributing to Project June

Thanks for helping build Project June. The codebase is small and intentionally
readable — keep it that way.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Before you commit

```bash
ruff check src tests examples    # lint (line length 100)
pytest -q                        # 74 tests, no network or API key needed
```

Both must pass. CI runs the same on Python 3.10 and 3.12.

## Conventions

- **Model:** default to `claude-opus-4-8` with adaptive thinking on. Don't
  downgrade without a stated reason.
- **Tools:** plain functions with type hints + a Google-style `Args:` docstring,
  decorated with `@tool`. Return strings (or values that stringify cleanly).
- **Tool inputs are untrusted** — validate before acting (see `calculate`'s
  allowlist and `MemoryStore`'s path confinement).
- **Errors return to the model** (`is_error: True`) so it can recover, rather
  than raising out of the loop.
- **Tests use the stub-client pattern** — no network. See `tests/test_agent.py`
  for the stub shape (`messages.create` returning objects with `.stop_reason`
  and `.content`). Live API tests live in `tests/test_live.py` and are skipped
  unless `ANTHROPIC_API_KEY` is set.

## Adding a feature

1. If it touches the agent loop, mirror it across the sync (`agent.py`,
   `autonomous.py`) and async (`aio.py`) paths.
2. Export the public surface from `src/project_june/__init__.py`.
3. Add stub-client tests covering the happy path and the tricky edges.
4. Update `README.md`, `CHANGELOG.md`, and the module map in `CLAUDE.md`.
5. Keep commits focused; run lint + tests; then push.

See [docs/architecture.md](docs/architecture.md) for how the layers fit together.
