from jarvis_backend.tools.search_tool import SearchTool
from jarvis_backend.tools.time_tool import TimeTool
from jarvis_backend.tools.tool_registry import ToolRegistry


def build_tool_registry():
    registry = ToolRegistry()
    registry.register(SearchTool())
    registry.register(TimeTool())
    return registry
