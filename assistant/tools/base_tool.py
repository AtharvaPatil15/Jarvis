class BaseTool:
    """
    Base class for all tools.
    Every tool must inherit from this.
    """

    name = "base"
    description = "Base tool"

    def execute(self, input_text: str) -> str:
        """
        Execute the tool with input text.
        Must return a string response.
        """
        raise NotImplementedError("Tool must implement execute()")
