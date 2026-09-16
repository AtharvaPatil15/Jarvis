"""Chooses the tools most relevant to a query by embedding similarity."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np

from assistant.tools.base import BaseTool
from assistant.tools.registry import ToolRegistry


def _unit(vector: list[float]) -> np.ndarray:
    array = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    return array / norm if norm else array


class ToolSelector:
    def __init__(self, llm: Any, always_include: Sequence[str] = ("get_time", "recall")) -> None:
        self._llm = llm
        self._always = tuple(always_include)
        self._cache: dict[str, np.ndarray] = {}

    def select(self, query: str, registry: ToolRegistry, k: int = 12) -> list[str]:
        tools = registry.all()
        if len(tools) <= k:
            return [tool.name for tool in tools]
        missing = [tool for tool in tools if self._key(tool) not in self._cache]
        if missing:
            vectors = self._llm.embed([f"{tool.name}: {tool.description}" for tool in missing])
            for tool, vector in zip(missing, vectors):
                self._cache[self._key(tool)] = _unit(vector)
        target = _unit(self._llm.embed([query])[0])
        ranked = sorted(tools, key=lambda tool: float(self._cache[self._key(tool)] @ target), reverse=True)
        chosen = [name for name in self._always if registry.get(name) is not None][:k]
        for tool in ranked:
            if len(chosen) >= k:
                break
            if tool.name not in chosen:
                chosen.append(tool.name)
        return chosen

    @staticmethod
    def _key(tool: BaseTool) -> str:
        return f"{tool.name}\x00{tool.description}"