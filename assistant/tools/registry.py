"""Name → tool lookup and schema export."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from assistant.tools.base import BaseTool

_VALID_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if not _VALID_NAME.fullmatch(tool.name):
            raise ValueError(f"invalid tool name: {tool.name!r}")
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools)

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def schemas(self, names: Iterable[str] | None = None) -> list[dict[str, Any]]:
        tools = self._tools.values() if names is None else [self._tools[n] for n in names if n in self._tools]
        return [tool.schema() for tool in tools]