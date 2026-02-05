# assistant/brain/planner.py
class Planner:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, user_input: str) -> str:
        prompt = f"""
You are an AI planner.

User instruction:
\"{user_input}\"

Respond with:
1. User intent (one sentence)
2. A short plan (1–3 steps)

Do NOT execute anything.
Be concise.
"""
        return self.llm.generate(prompt)
