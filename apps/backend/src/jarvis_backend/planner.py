class Planner:
    """
    Simple step planner for multi-tool tasks.
    """

    def plan(self, text: str):
        """
        Returns a list of steps.
        Each step is a dictionary:
        {
            "type": "tool" or "llm",
            "name": tool_name (if tool),
            "input": step_input
        }
        """

        text = text.lower()
        steps = []

        # Detect time intent
        wants_time = "time" in text

        # Detect search intent
        search_keywords = [
            "search",
            "capital",
            "weather",
            "who is",
            "what is",
            "tell me about"
        ]
        wants_search = any(word in text for word in search_keywords)

        # Multi-step case
        if wants_search and wants_time:
            steps.append({
                "type": "tool",
                "name": "search",
                "input": text
            })
            steps.append({
                "type": "tool",
                "name": "time",
                "input": text
            })
            return steps

        # Single search
        if wants_search:
            steps.append({
                "type": "tool",
                "name": "search",
                "input": text
            })
            return steps

        # Single time
        if wants_time:
            steps.append({
                "type": "tool",
                "name": "time",
                "input": text
            })
            return steps

        # Default: LLM
        steps.append({
            "type": "llm",
            "input": text
        })

        return steps