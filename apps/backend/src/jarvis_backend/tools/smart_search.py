import requests
from ddgs import DDGS

from jarvis_backend.tools.base import BaseTool


class SmartSearchTool(BaseTool):
    name = "smart_search"
    description = "Search the web and gather readable public information"
    requires_permission = False

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (JarvisAssistant/1.0)",
    }

    def run(self, **kwargs) -> str:
        query = kwargs.get("query", "")
        if not query:
            return "Error: 'query' parameter is required."

        collected = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return "No relevant information was found online."

        for result in results:
            snippet = result.get("body")
            url = result.get("href")

            if snippet:
                collected.append(snippet)

            if url:
                try:
                    response = requests.get(url, headers=self.HEADERS, timeout=6)
                    if response.status_code == 200:
                        collected.append(response.text[:2000])
                except Exception:
                    pass

            if len(collected) >= 3:
                break

        return "\n\n".join(collected)
