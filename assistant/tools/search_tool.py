import re
from assistant.tools.base_tool import BaseTool
from assistant.tools.smart_search import SmartSearchTool


def clean_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    clean = re.sub(r'<.*?>', '', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


class SearchTool(BaseTool):
    name = "search"
    description = "Search the internet for information"

    def __init__(self):
        self.engine = SmartSearchTool()

    def execute(self, input_text: str) -> str:
        result = self.engine.run(query=input_text)

        if isinstance(result, str):
            # Strip HTML tags if present
            if "<" in result and ">" in result:
                result = clean_html(result)

            # Safety trim to keep TTS responses short
            return result[:300].strip()

        return str(result)
