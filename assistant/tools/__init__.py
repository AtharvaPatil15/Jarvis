from assistant.tools.search_tool import SearchTool
from assistant.tools.time_tool import TimeTool
from assistant.tools.tool_registry import ToolRegistry

def build_tool_registry():
    registry = ToolRegistry()
    registry.register(SearchTool())
    registry.register(TimeTool())
    return registry
