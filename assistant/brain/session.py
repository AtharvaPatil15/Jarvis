"""Conversation history for one session, trimmed by whole turns to a character budget."""
from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from assistant.brain.llm import ToolCall


def _size(message: dict[str, Any]) -> int:
    return len(message.get("content") or "") + (len(json.dumps(message["tool_calls"])) if "tool_calls" in message else 0)


class Session:
    def __init__(self, system_prompt: Callable[[], str], max_chars: int = 12000) -> None:
        self._system_prompt = system_prompt
        self.max_chars = max_chars
        self._turns: list[list[dict[str, Any]]] = []

    def add_user(self, text: str) -> None:
        self._turns.append([{"role": "user", "content": text}])

    def add_assistant(self, content: str, tool_calls: list[ToolCall] | None = None) -> None:
        message: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = [{"function": {"name": c.name, "arguments": c.arguments}} for c in tool_calls]
        self._current_turn().append(message)

    def add_tool_result(self, call: ToolCall, content: str) -> None:
        self._current_turn().append({"role": "tool", "tool_name": call.name, "content": content})

    def messages(self) -> list[dict[str, Any]]:
        system = {"role": "system", "content": self._system_prompt()}
        budget = self.max_chars - _size(system)
        kept: list[list[dict[str, Any]]] = []
        for turn in reversed(self._turns):
            size = sum(_size(m) for m in turn)
            if kept and size > budget:
                break
            kept.append(turn)
            budget -= size
        return [system] + [message for turn in reversed(kept) for message in turn]

    def clear(self) -> None:
        self._turns.clear()

    def _current_turn(self) -> list[dict[str, Any]]:
        if not self._turns:
            self._turns.append([])
        return self._turns[-1]