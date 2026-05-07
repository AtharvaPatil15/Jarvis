class ToolRegistry:
    """
    Central registry for all tools.
    """

    def __init__(self):
        self.tools = {}

    def register(self, tool):
        """
        Register a tool instance.
        """
        self.tools[tool.name] = tool

    def get(self, name: str):
        """
        Get a tool by name.
        """
        return self.tools.get(name)

    def list_tools(self):
        """
        Return list of tool names.
        """
        return list(self.tools.keys())
