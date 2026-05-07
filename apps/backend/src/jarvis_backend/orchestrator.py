import re
from datetime import datetime

from jarvis_backend.brain.llm import LocalLLM
from jarvis_backend.memory.store import MemoryStore
from jarvis_backend.planner import Planner
from jarvis_backend.tools import build_tool_registry


def shape_response(text: str) -> str:
    if not text:
        return text

    banned_phrases = [
        "as an ai",
        "i am an ai",
        "i think",
        "it appears",
        "according to",
        "based on",
    ]

    for phrase in banned_phrases:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub("", text)

    sentences = [sentence.strip() for sentence in text.split(".") if sentence.strip()]
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
        steps = self.planner.plan(input_text)
        results = []

        for step in steps:
            if step["type"] == "tool":
                tool = self.tool_registry.get(step["name"])
                if tool:
                    print(f"Executing tool: {step['name']}")
                    results.append(tool.execute(step["input"]))
            elif step["type"] == "llm":
                system_prompt = self._construct_system_prompt()
                full_prompt = f"{system_prompt}\n\nUser: {step['input']}\nJarvis:"
                raw_response = self.llm.generate(full_prompt)
                results.append(shape_response(raw_response))

        return {
            "type": "final_response",
            "content": " ".join(results),
        }

    def respond(self, user_input: str) -> str:
        return self.handle_input(user_input)["content"]
