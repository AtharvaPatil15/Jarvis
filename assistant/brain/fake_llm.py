"""Deterministic stand-in for LLMClient: tests, e2e runs and JARVIS_LLM_BACKEND=fake."""
from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from assistant.brain.llm import ChatResult


class FakeLLM:
    def __init__(self, script: Sequence[ChatResult] = (), healthy: bool = True, dim: int = 64) -> None:
        self.script: list[ChatResult] = list(script)
        self.calls: list[dict[str, Any]] = []
        self.healthy = healthy
        self.dim = dim

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