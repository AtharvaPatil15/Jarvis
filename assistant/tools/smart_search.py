# assistant/tools/smart_search.py
import requests
from assistant.tools.base import BaseTool
from ddgs import DDGS


class SmartSearchTool(BaseTool):
    name = "smart_search"
    description = "Search the web and gather readable public information"
    requires_permission = False

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (JarvisAssistant/1.0)"
    }

    def run(self, **kwargs) -> str:
        """
        Robust, Grabber-style logic:
        - Use DuckDuckGo text search (ddgs)
        - Prefer snippets (most reliable)
        - Lightly fetch pages if possible
        """
        query = kwargs.get("query", "")
        
        if not query:
            return "Error: 'query' parameter is required."

        collected = []

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))

        if not results:
            return "No relevant information was found online."

        for r in results:
            snippet = r.get("body")
            url = r.get("href")

            if snippet:
                collected.append(snippet)

            # Page fetch is optional — snippets are enough
            if url:
                try:
                    resp = requests.get(url, headers=self.HEADERS, timeout=6)
                    if resp.status_code == 200:
                        collected.append(resp.text[:2000])
                except Exception:
                    pass

            if len(collected) >= 3:
                break

        return "\n\n".join(collected)
