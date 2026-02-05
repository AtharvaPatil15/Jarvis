# assistant/tools/search.py
from assistant.tools.base import BaseTool
import requests

class SearchTool(BaseTool):
    name = "search"
    description = "Search the internet for information"
    requires_permission = False  # SAFE TOOL

    def run(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        
        if not query:
            return "Error: 'query' parameter is required."
        
        # Simple DuckDuckGo instant answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": 1,
            "no_html": 1
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("AbstractText"):
            return data["AbstractText"]

        return "I found information online, but no concise summary was available."
