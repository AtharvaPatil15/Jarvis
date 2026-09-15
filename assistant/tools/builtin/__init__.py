"""Factory for the default tool set. Later tasks register more tools here."""
from __future__ import annotations

from typing import Any

from assistant.config import Settings
from assistant.tools.builtin.calculator import CalculateTool
from assistant.tools.builtin.memory_tools import ForgetTool, RecallTool, RememberTool
from assistant.tools.builtin.time_tool import GetTimeTool
from assistant.tools.builtin.weather import GetWeatherTool
from assistant.tools.builtin.web_search import FetchPageTool, WebSearchTool
from assistant.tools.registry import ToolRegistry


def build_default_registry(settings: Settings, memory: Any | None = None, scheduler: Any | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(GetTimeTool(timezone=settings.timezone))
    registry.register(CalculateTool())
    registry.register(WebSearchTool())
    registry.register(FetchPageTool())
    registry.register(GetWeatherTool(settings.location_name, settings.latitude, settings.longitude))
    if memory is not None:
        registry.register(RememberTool(memory))
        registry.register(RecallTool(memory))
        registry.register(ForgetTool(memory))
    return registry
