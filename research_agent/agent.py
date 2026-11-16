"""The agent loop.

Each call to `ResearchAgent.ask()` runs this loop:

1. Send the conversation to Claude (streamed, so text appears as it is written).
2. Claude may use server tools (web search / web fetch) inside the same turn -
   Anthropic runs those, and the results come back in the response.
3. If Claude calls a client tool (save_report), we run it locally and send the
   result back.
4. Repeat until Claude gives a final answer with no more tool calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

import anthropic

from .prompts import SYSTEM_PROMPT
from .tools import REPORTS_DIR, SAVE_REPORT_TOOL, run_client_tool

DEFAULT_MODEL = "claude-opus-5-5"

# Server-side refusal fallback: if the main model declines a request, the API
# re-runs it on a suitable fallback model within the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class AgentConfig:
    model: str = DEFAULT_MODEL
    effort: str = "high"  # low | medium | high | xhigh | max
    max_tokens: int = 64000
    max_searches: int = 8  # web_search calls allowed per request
    max_fetches: int = 6  # web_fetch calls allowed per request
    max_fetch_tokens: int = 20000  # cap on tokens read from each fetched page
    max_turns: int = 25  # safety cap on loop iterations per question
    save_reports: bool = True
    show_thinking: bool = False
    reports_dir: Path = REPORTS_DIR


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    searches: int = 0
    fetches: int = 0

    def add(self, usage: Any) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage, "output_tokens", 0) or 0
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0


@dataclass
class ResearchAgent:
    config: AgentConfig = field(default_factory=AgentConfig)
    client: anthropic.Anthropic = field(default_factory=anthropic.Anthropic)
    output: Callable[[str], None] = lambda text: print(text, end="", flush=True)
    messages: list[dict[str, Any]] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)

    # ------------------------------------------------------------------ setup

    def _tools(self) -> list[dict[str, Any]]:
        cfg = self.config
        tools: list[dict[str, Any]] = [
            {"type": "web_search_20260209", "name": "web_search", "max_uses": cfg.max_searches},
            {
                "type": "web_fetch_20260209",
                "name": "web_fetch",
                "max_uses": cfg.max_fetches,
                "max_content_tokens": cfg.max_fetch_tokens,
            },
        ]
        if cfg.save_reports:
            tools.append(SAVE_REPORT_TOOL)
        return tools

    # --------------------------------------------------------------- the loop

    def ask(self, question: str) -> str:
        """Research `question` and return Claude's final answer text.

        The conversation is kept, so follow-up questions have context.
        """
        if not self.messages:
            question = f"(Today's date: {date.today().isoformat()})\n\n{question}"
        self.messages.append({"role": "user", "content": question})

        json_retries = 0
        response = None

        for _ in range(self.config.max_turns):
            try:
                response = self._stream_turn()
                json_retries = 0
            except ValueError:
                # The SDK could not parse a streamed tool input at all. No
                # complete tool_use block exists to answer, so re-issue the turn.
                # (API errors are not ValueError and propagate normally.)
                json_retries += 1
                if json_retries > 2:
                    raise
                self.output("\n[retrying turn: malformed tool input]\n")
                continue

            self.usage.add(response.usage)
            # Always append the full content (thinking, tool blocks, text)
            # unchanged - later requests depend on it.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "pause_turn":
                # A long server-tool turn paused; send it back to continue.
                continue

            if response.stop_reason == "refusal":
                self.output("\n[the model declined this request]\n")
                break

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                break  # final answer

            if response.stop_reason == "max_tokens":
                # A truncated tool input can look valid - never run it.
                self.output("\n[stopped: output limit reached mid tool call]\n")
                break

            self.messages.append({"role": "user", "content": self._run_tools(tool_uses)})
        else:
            self.output(f"\n[stopped after {self.config.max_turns} turns]\n")

        if response is None:
            return ""
        return "".join(b.text for b in response.content if b.type == "text")

    def _stream_turn(self) -> Any:
        cfg = self.config
        thinking = {"type": "adaptive", "display": "summarized" if cfg.show_thinking else "omitted"}

        with self.client.beta.messages.stream(
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            system=SYSTEM_PROMPT,
            tools=self._tools(),
            messages=self.messages,
            thinking=thinking,
            output_config={"effort": cfg.effort},
            cache_control={"type": "ephemeral"},  # cache the growing conversation
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            for event in stream:
                self._render(event)
            return stream.get_final_message()

    # ------------------------------------------------------------- rendering

    def _render(self, event: Any) -> None:
        if event.type == "text":
            self.output(event.text)
        elif event.type == "content_block_delta" and event.delta.type == "thinking_delta":
            if self.config.show_thinking:
                self.output(event.delta.thinking)
        elif event.type == "content_block_start":
            block = event.content_block
            if block.type == "thinking" and self.config.show_thinking:
                self.output("\n[thinking] ")
            elif block.type == "tool_use":
                self.output(f"\n[{block.name}] writing...\n")
        elif event.type == "content_block_stop":
            block = getattr(event, "content_block", None)
            if block is not None and block.type == "server_tool_use":
                self._log_server_tool(block)

    def _log_server_tool(self, block: Any) -> None:
        args = block.input if isinstance(block.input, dict) else {}
        if block.name == "web_search":
            self.usage.searches += 1
            self.output(f"\n[search] {args.get('query', '')}\n")
        elif block.name == "web_fetch":
            self.usage.fetches += 1
            self.output(f"\n[fetch] {args.get('url', '')}\n")
        else:
            self.output(f"\n[{block.name}]\n")

    # --------------------------------------------------------- client tools

    def _run_tools(self, tool_uses: list[Any]) -> list[dict[str, Any]]:
        """Run every client tool call and return all results in one message."""
        results = []
        for block in tool_uses:
            text, is_error = run_client_tool(block.name, block.input, self.config.reports_dir)
            if is_error and "invalid input" in text:
                # Echo what we received so Claude can correct itself.
                text = json.dumps({"INVALID_INPUT": text, "received": str(block.input)[:500]})
            self.output(f"[{block.name}] {text}\n")
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": is_error}
            )
        return results
