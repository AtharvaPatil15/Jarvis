# orchestrator.py
import logging
from datetime import datetime
from assistant.brain.llm import LocalLLM
from assistant.planner import Planner
from assistant.memory.store import MemoryStore
from assistant.tools import build_tool_registry

class Orchestrator:
    def __init__(self):
        self.llm = LocalLLM()
        # Initialize the new Planner
        self.planner = Planner()
        self.memory = MemoryStore()
        self.user_profile = self.memory
        self.tool_registry = build_tool_registry()

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

    def handle_input(self, input_text: str):
        """
        Main agent loop using planner.
        """

        # 1. Get Plan
        steps = self.planner.plan(input_text)
        results = []

        # 2. Execute Steps
        for step in steps:
            if step["type"] == "tool":
                tool = self.tool_registry.get(step["name"])
                if tool:
                    print(f"🔧 Executing Tool: {step['name']}")
                    result = tool.execute(step["input"])
                    results.append(result)

            elif step["type"] == "llm":
                # Inject system context for personality
                system_prompt = self._construct_system_prompt()

                # Build conversation history context
                history = self.memory.get_recent_history()
                history_block = ""
                for turn in history:
                    history_block += f"User: {turn['user']}\nJarvis: {turn['assistant']}\n"

                full_prompt = f"{system_prompt}\n\n{history_block}User: {step['input']}\nJarvis:"
                
                # Execute LLM (Mapped to self.llm.generate)
                response = self.llm.generate(full_prompt)
                results.append(response)

        # 3. Combine results into final response
        final_response = " ".join(results)

        # 4. Store turn in short-term memory
        self.memory.add_turn(input_text, final_response)

        return {
            "type": "final_response",
            "content": final_response
        }

    def respond(self, user_input: str) -> str:
        # Backward compatibility wrapper
        result = self.handle_input(user_input)
        return result["content"]
