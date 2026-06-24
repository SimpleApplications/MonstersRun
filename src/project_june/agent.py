"""The agent loop.

`Agent.run(prompt)` drives a manual agentic loop against the Messages API:

    1. send the conversation + tool definitions to Claude
    2. if Claude asks for tools, run them locally and feed the results back
    3. repeat until Claude stops calling tools (stop_reason == "end_turn")

A manual loop (rather than the SDK's tool runner) is the flexible/potent choice:
it gives you a single place to log every step, gate tool execution, enforce an
iteration ceiling, and inspect token usage.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable

import anthropic

from .config import AgentConfig
from .tools import Tool
from .usage import Usage

# A hook called after each tool runs: (tool_name, tool_input, result) -> None.
EventHook = Callable[[str, dict[str, Any], str], None]


class Agent:
    def __init__(
        self,
        tools: Iterable[Tool] | None = None,
        config: AgentConfig | None = None,
        client: anthropic.Anthropic | None = None,
        on_tool: EventHook | None = None,
    ) -> None:
        self.config = config or AgentConfig()
        # The SDK resolves ANTHROPIC_API_KEY from the environment by default.
        self.client = client or anthropic.Anthropic()
        self.tools: dict[str, Tool] = {t.name: t for t in (tools or [])}
        self.on_tool = on_tool
        # Conversation history — the API is stateless, so we resend it each turn.
        self.messages: list[dict[str, Any]] = []
        # Running token/cost accounting across every turn this agent makes.
        self.usage = Usage()

    def add_tool(self, t: Tool) -> None:
        self.tools[t.name] = t

    def _request_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": self.messages,
            "output_config": {"effort": self.config.effort},
        }
        if self.config.system:
            kwargs["system"] = self.config.system
        if self.config.thinking:
            # Adaptive thinking: Claude decides how much to think per turn.
            kwargs["thinking"] = {"type": "adaptive"}
        if self.tools:
            kwargs["tools"] = [t.to_api() for t in self.tools.values()]
        if self.config.cache and (self.config.system or self.tools):
            # Auto-cache the last cacheable block (the tools + system prefix), so
            # a multi-turn loop reprocesses that prefix at ~0.1x after turn one.
            kwargs["cache_control"] = {"type": "ephemeral"}
        return kwargs

    def run(self, prompt: str) -> str:
        """Run one user turn to completion and return Claude's final text."""
        self.messages.append({"role": "user", "content": prompt})

        for _ in range(self.config.max_iterations):
            response = self.client.messages.create(**self._request_kwargs())
            self.usage.add(getattr(response, "usage", None))

            if response.stop_reason == "refusal":
                detail = getattr(response, "stop_details", None)
                category = getattr(detail, "category", None)
                return f"[refused] The request was declined (category: {category})."

            # Preserve the full assistant turn (text + thinking + tool_use blocks).
            self.messages.append({"role": "assistant", "content": response.content})

            # A server-side tool hit its iteration cap. Re-send to let the server
            # resume; do not add a user message.
            if response.stop_reason == "pause_turn":
                continue

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                # No tools requested — we're done. Return the text blocks.
                return "".join(b.text for b in response.content if b.type == "text").strip()

            # Execute every requested tool and return all results in one user turn.
            results: list[dict[str, Any]] = []
            for block in tool_uses:
                results.append(self._execute(block))
            self.messages.append({"role": "user", "content": results})

        return "[stopped] Reached max_iterations without a final answer."

    def run_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """One-shot structured output: return a dict validated against `schema`.

        Uses the Messages API's `output_config.format` so the model's response is
        guaranteed to be JSON matching `schema`. This is a single call (no tool
        loop) — use it for extraction/classification, not multi-step work.

        Args:
            prompt: The instruction (e.g. "Extract the name and age from ...").
            schema: A JSON Schema object the response must conform to.
        """
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {
                "effort": self.config.effort,
                "format": {"type": "json_schema", "schema": schema},
            },
        }
        if self.config.system:
            kwargs["system"] = self.config.system
        if self.config.thinking:
            kwargs["thinking"] = {"type": "adaptive"}

        response = self.client.messages.create(**kwargs)
        self.usage.add(getattr(response, "usage", None))
        if response.stop_reason == "refusal":
            raise ValueError("request was declined (refusal)")
        if response.stop_reason == "max_tokens":
            raise ValueError("structured output truncated (hit max_tokens); raise max_tokens")
        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text.strip():
            raise ValueError(f"no JSON in response (stop_reason={response.stop_reason})")
        return json.loads(text)

    def _execute(self, block: Any) -> dict[str, Any]:
        """Run a single tool_use block, returning a tool_result block."""
        name, tool_input, use_id = block.name, dict(block.input or {}), block.id
        tool = self.tools.get(name)
        if tool is None:
            return {
                "type": "tool_result",
                "tool_use_id": use_id,
                "content": f"Error: unknown tool '{name}'.",
                "is_error": True,
            }
        try:
            output = tool.run(**tool_input)
            is_error = False
        except Exception as exc:  # surface the error to Claude so it can recover
            output = f"Error running '{name}': {exc}"
            is_error = True

        if self.on_tool:
            self.on_tool(name, tool_input, output)

        return {
            "type": "tool_result",
            "tool_use_id": use_id,
            "content": output,
            "is_error": is_error,
        }
