from assistant.brain.fake_llm import FakeLLM
from assistant.brain.llm import LLMError
from assistant.brain.session import Session
from assistant.memory.db import MemoryDB
from assistant.memory.manager import MemoryManager
from assistant.orchestrator import Orchestrator
from assistant.safety.permissions import AllowAllGate
from assistant.tools.registry import ToolRegistry


def orchestrator_with(memory, llm, events) -> Orchestrator:
    box: dict[str, Orchestrator] = {}
    session = Session(lambda: "SYS\n" + "\n".join(box["o"].current_memories))
    box["o"] = Orchestrator(llm, ToolRegistry(), session, AllowAllGate(), events, memory=memory)
    return box["o"]


async def test_relevant_memories_are_injected_into_the_system_prompt(tmp_path, events) -> None:
    memory = MemoryManager(MemoryDB(tmp_path / "m.db"), FakeLLM())
    memory.remember("favourite colour is teal")
    memory.remember("sister is called Priya")
    llm = FakeLLM()
    await orchestrator_with(memory, llm, events).handle("what is my favourite colour")
    system = llm.calls[0]["messages"][0]["content"]
    assert "favourite colour is teal" in system
    assert "Priya" not in system


class BrokenSearch(MemoryManager):
    def search(self, *args, **kwargs):
        raise LLMError("embedding model missing")


async def test_memory_failure_does_not_break_the_turn(tmp_path, events) -> None:
    memory = BrokenSearch(MemoryDB(tmp_path / "m.db"), FakeLLM())
    orchestrator = orchestrator_with(memory, FakeLLM(), events)
    assert await orchestrator.handle("hello") == "You said: hello"
    assert orchestrator.current_memories == []
