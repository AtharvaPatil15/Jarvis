"""Factory for the default tool set. Later tasks register more tools here."""
from __future__ import annotations

from typing import Any

from assistant.config import Settings
from assistant.tools.builtin.calculator import CalculateTool
from assistant.tools.builtin.files import CreateFolderTool, ReadFileTool, SearchFilesTool
from assistant.tools.builtin.memory_tools import ForgetTool, RecallTool, RememberTool
from assistant.tools.builtin.reminders import ListRemindersTool, SetReminderTool
from assistant.tools.builtin.screen import ReadScreenTool
from assistant.tools.builtin.system import MediaControlTool, OpenAppTool, OpenUrlTool
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
    registry.register(SearchFilesTool(settings.file_roots))
    registry.register(ReadFileTool(settings.file_roots))
    registry.register(CreateFolderTool(settings.file_roots))
    registry.register(ReadScreenTool())
    registry.register(OpenAppTool())
    registry.register(OpenUrlTool())
    registry.register(MediaControlTool())
    if memory is not None:
        registry.register(RememberTool(memory))
        registry.register(RecallTool(memory))
        registry.register(ForgetTool(memory))
    if scheduler is not None:
        registry.register(SetReminderTool(scheduler, settings.timezone))
        registry.register(ListRemindersTool(scheduler, settings.timezone))
    return registry
