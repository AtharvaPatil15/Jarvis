from assistant.tools.base_tool import BaseTool
from assistant.tools.smart_search import SmartSearchTool

class SearchTool(BaseTool):
    name = "search"
    description = "Search the internet for information"

    def __init__(self):
        self.engine = SmartSearchTool()

    def execute(self, input_text: str) -> str:
        result = self.engine.run(query=input_text)

        # Clean result
        if isinstance(result, str):
            # Remove HTML tags if present
            if "<html" in result.lower():
                return "I found results, but the page returned raw data. Let me refine that in the future."
            return result[:300]  # safety trim

        return str(result)
