---
name: new-tool
description: Scaffold a new agent tool for Project June. Use when adding a capability an agent can call — a @tool function in builtin_tools.py (or a new module) plus its stub test. Triggers on "add a tool", "new tool", "give the agent a way to ...".
---

# Add a tool to Project June

Tools are how a Project June agent acts on the world. A tool is a plain Python
function with type hints + a Google-style `Args:` docstring, decorated with
`@tool` (from `project_june.tools`). The JSON schema sent to Claude is generated
from the signature and docstring — so the function *is* the spec.

## Steps

1. **Write the function** in `src/project_june/builtin_tools.py` (or a new module
   if it's a cohesive group). Pattern:

   ```python
   @tool
   def my_tool(query: str, limit: int = 10) -> str:
       """One-line summary Claude reads to decide when to call this.

       Args:
           query: What to search for.
           limit: Max results. Defaults to 10.
       """
       # Validate model-supplied inputs BEFORE acting (see calculate's allowlist
       # and MemoryStore's path confinement for the pattern).
       ...
       return result  # return a string, or a value that stringifies cleanly
   ```

2. **Validate inputs** — tool inputs are model output. Allowlist characters,
   confine paths to a root, bound sizes. Never trust them.

3. **Decide default vs opt-in.** Read-only, side-effect-free tools may join
   `DEFAULT_TOOLS`. Anything with side effects (writes, network, money) goes in a
   separate opt-in list (e.g. `WRITE_TOOLS`) — never `DEFAULT_TOOLS`.

4. **Surface errors, don't raise.** Return an error *string* (e.g.
   `"Error: no such file"`); the agent loop turns a raised exception into a
   tool_result with `is_error: True` so the model can recover either way.

5. **Test it with no network.** Add a test that calls `my_tool.run(**kwargs)` and
   asserts on the returned string, plus the schema:

   ```python
   def test_my_tool_schema_and_run():
       assert my_tool.input_schema["required"] == ["query"]
       assert "expected" in my_tool.run(query="x")
   ```

6. **Run the gate:** `ruff check src tests` and `pytest -q`. Both must pass.

7. **Export if public** — if it's part of the public surface, add it to
   `src/project_june/__init__.py`.

## Notes
- For tools that wrap an external service, prefer the MCP bridge
  (`mcp_tools`) over hand-writing a tool per endpoint.
- To let an agent delegate to a sub-agent, use `agent_tool()` rather than a
  plain tool.
