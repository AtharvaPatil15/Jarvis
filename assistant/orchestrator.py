# assistant/orchestrator.py
import logging
from datetime import datetime
from assistant.brain.llm import LocalLLM
from assistant.brain.planner import Planner
from assistant.tools.smart_search import SmartSearchTool
from assistant.memory.store import MemoryStore

class Orchestrator:
    def __init__(self):
        self.llm = LocalLLM()
        self.planner = Planner(self.llm)
        self.memory = MemoryStore()
        self.search_tool = SmartSearchTool()
        self.user_profile = self.memory  # simple alias for now

    def _construct_system_prompt(self):
        """Builds a dynamic system prompt with time and context."""
        now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        return (
            f"SYSTEM CONTEXT:\n"
            f"- Current Date/Time: {now}\n"
            f"- Location: Pimpri-Chinchwad, Maharashtra, India\n"
            f"- User: Engineering Student (Final Year)\n"
            f"\n"
            f"IDENTITY:\n"
            f"You are Jarvis. You are helpful, precise, and have a slight dry wit.\n"
            f"You are NOT a generic AI. You HAVE access to real-time data via your tools.\n"
            f"Keep voice responses concise (1-2 sentences) unless asked for details.\n"
        )

    def handle_input(self, user_input: str) -> str:
        """
        Main loop: Input -> Plan -> Execute -> Response
        """
        # 1. Update System Prompt with fresh time
        system_prompt = self._construct_system_prompt()
        
        # 2. Check for Search Intent (Simple routing)
        lower_input = user_input.lower()
        if any(w in lower_input for w in ["search", "google", "find", "weather", "news", "price", "who is", "when is"]):
            print(f"🕵️ Routing to Smart Search: {user_input}")
            search_result = self.search_tool.run(query=user_input)
            
            # Synthesize answer
            context_prompt = (
                f"{system_prompt}\n"
                f"SEARCH RESULTS:\n{search_result}\n\n"
                f"USER QUERY: {user_input}\n"
                f"INSTRUCTION: Answer the user's question based on the search results."
            )
            return self.llm.generate(context_prompt)

        # 3. Direct Chat (Time, Math, General)
        # We inject the time into the prompt so the LLM can "see" it
        full_prompt = (
            f"{system_prompt}\n\n"
            f"User: {user_input}\n"
            f"Jarvis:"
        )
        return self.llm.generate(full_prompt)

    def respond(self, user_input: str) -> str:
        # Wrapper for backward compatibility if needed
        return self.handle_input(user_input)
