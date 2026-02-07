import logging
import re
from datetime import datetime
from assistant.brain.llm import LocalLLM
from assistant.planner import Planner
from assistant.memory.store import MemoryStore
from assistant.tools import build_tool_registry

def shape_response(text: str) -> str:
    """
    Post-processes LLM output to match Jarvis personality.
    """
    if not text:
        return text

    # Remove common AI phrases
    banned_phrases = [
        "as an ai",
        "i am an ai",
        "i think",
        "it appears",
        "according to",
        "based on"
    ]

    # Case-insensitive removal
    for phrase in banned_phrases:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub("", text)

    # Trim to 2 sentences max
    sentences = text.split(".")
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return ""
        
    text = ". ".join(sentences[:2])

    if not text.endswith("."):
        text += "."

    return text.strip()

class Orchestrator:
    def __init__(self):
        self.llm = LocalLLM()
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
            f"- User: Engineering Student\n"
            f"\n"
            f"IDENTITY:\n"
            f"You are Jarvis, a calm, intelligent, and confident AI assistant.\n"
            f"You speak with precision and subtle dry wit.\n"
            f"\n"
            f"SPEECH STYLE RULES:\n"
            f"- Responses must be short and natural for speech.\n"
            f"- Default: 1 short sentence.\n"
            f"- Maximum: 2 sentences unless the user asks for detail.\n"
            f"- No disclaimers, no AI mentions, no filler text.\n"
            f"- Never say: 'As an AI', 'I think', or 'It appears'.\n"
            f"- Sound confident and helpful.\n"
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
                full_prompt = f"{system_prompt}\n\nUser: {step['input']}\nJarvis:"
                
                # Execute LLM (Mapped to self.llm.generate)
                raw_response = self.llm.generate(full_prompt)
                
                # Apply Personality Shaping
                shaped_response = shape_response(raw_response)
                results.append(shaped_response)

        # 3. Combine results into final response
        final_response = " ".join(results)

        return {
            "type": "final_response",
            "content": final_response
        }

    def respond(self, user_input: str) -> str:
        # Backward compatibility wrapper
        result = self.handle_input(user_input)
        return result["content"]