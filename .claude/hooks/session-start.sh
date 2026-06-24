#!/bin/bash
# SessionStart hook for Project June.
# Installs the package + dev tools so tests and the linter run in fresh
# Claude Code on the web containers. Idempotent and non-interactive.
set -euo pipefail

# Only do the heavy install in remote (web) sessions; locals usually have a venv.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"

# Editable install pulls in anthropic (runtime) + pytest/ruff (dev) and puts the
# `june` entry point on PATH. A normal editable install (not a clean reinstall)
# lets the container cache be reused across sessions.
python3 -m pip install --quiet -e ".[dev]"

echo "Project June environment ready."
