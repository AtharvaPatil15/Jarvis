"""Deterministic stand-in for LLMClient: tests, e2e runs and JARVIS_LLM_BACKEND=fake."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from assistant.brain.llm import ChatResult, ToolCall


class FakeLLM:
    def __init__(self, script: Sequence[ChatResult] = (), healthy: bool = True, dim: int = 256) -> None:
        self.script: list[ChatResult] = list(script)
        self.calls: list[dict[str, Any]] = []
        self.healthy = healthy
        self.dim = dim
        self._tool_counter = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.4,
        max_tokens: int = 512,
        on_delta: Callable[[str], None] | None = None,
    ) -> ChatResult:
        self.calls.append({"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)})
        if self.script:
            result = self.script.pop(0)
        else:
            last = messages[-1] if messages else {}
            match = re.fullmatch(r"/tool (\w+) (\{.*\})", (last.get("content") or "").strip(), re.DOTALL)
            if last.get("role") == "user" and match:
                self._tool_counter += 1
                result = ChatResult(
                    content="",
                    tool_calls=[ToolCall(id=f"fake-{self._tool_counter}", name=match.group(1), arguments=json.loads(match.group(2)))],
                )
            else:
                last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
                result = ChatResult(content=f"You said: {last_user}", tool_calls=[])
        if on_delta is not None and result.content:
            for chunk in re.findall(r"\S+\s*", result.content):
                on_delta(chunk)
        return result

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = np.zeros(self.dim, dtype=np.float32)
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                vector[int.from_bytes(digest[:4], "little") % self.dim] += 1.0
            norm = float(np.linalg.norm(vector))
            vectors.append((vector / norm if norm else vector).tolist())
        return vectors

    def health(self) -> bool:
        return self.healthy