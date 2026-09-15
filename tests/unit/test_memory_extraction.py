from assistant.brain.fake_llm import FakeLLM
from assistant.brain.llm import ChatResult, LLMError, ToolCall
from assistant.brain.session import Session
from assistant.memory.db import MemoryDB
from assistant.memory.manager import MemoryManager
from assistant.orchestrator import Orchestrator
from assistant.safety.permissions import AllowAllGate
from assistant.tools.builtin.memory_tools import RememberTool
from assistant.tools.registry import ToolRegistry


def reply(text: str) -> ChatResult:
    return ChatResult(content=text, tool_calls=[])


def manager(tmp_path, *contents: str) -> MemoryManager:
    return MemoryManager(MemoryDB(tmp_path / "m.db"), FakeLLM(script=[reply(c) for c in contents]))


def test_facts_are_parsed_from_json_even_with_surrounding_text(tmp_path) -> None:
    memory = manager(tmp_path, 'Sure! {"facts": ["Favourite colour is teal", "Sister is called Priya"]} Done.')
    assert memory.extract_facts("my favourite colour is teal and my sister is Priya", "Noted.") == [
        "Favourite colour is teal", "Sister is called Priya"]


def test_bad_output_yields_no_facts(tmp_path) -> None:
    memory = manager(tmp_path, "no json here", '{"facts": "teal"}', '{"facts": [1, "", "  ok  "]}')
    assert memory.extract_facts("a", "b") == []
    assert memory.extract_facts("a", "b") == []
    assert memory.extract_facts("a", "b") == ["ok"]


def test_facts_are_capped_in_number_and_length(tmp_path) -> None:
    many = '{"facts": [' + ", ".join(f'"fact number {i} ' + "x" * 300 + '"' for i in range(8)) + "]}"
    facts = manager(tmp_path, many).extract_facts("a", "b")
    assert len(facts) == 5 and all(len(f) <= 200 for f in facts)


def test_process_exchange_stores_new_facts_once(tmp_path) -> None:
    memory = manager(tmp_path, '{"facts": ["Owns a cat named Tofu"]}', '{"facts": ["Owns a cat named Tofu"]}')
    assert len(memory.process_exchange("I have a cat called Tofu", "Lovely.")) == 1
    assert memory.process_exchange("Tofu is my cat", "Yes.") == []


async def test_orchestrator_learns_in_the_background(tmp_path, events) -> None:
    memory = manager(tmp_path, '{"facts": ["Favourite colour is teal"]}')
    orchestrator = Orchestrator(FakeLLM(), ToolRegistry(), Session(lambda: "SYS"), AllowAllGate(), events, memory=memory)
    await orchestrator.handle("my favourite colour is teal")
    await orchestrator.wait_background()
    assert [f.text for f in memory.search("favourite colour", min_score=0.0)] == ["Favourite colour is teal"]


class BrokenChat(FakeLLM):
    def chat(self, *args, **kwargs):
        raise LLMError("offline")


async def test_extraction_failure_is_swallowed(tmp_path, events) -> None:
    memory = MemoryManager(MemoryDB(tmp_path / "m.db"), BrokenChat())
    orchestrator = Orchestrator(FakeLLM(), ToolRegistry(), Session(lambda: "SYS"), AllowAllGate(), events, memory=memory)
    assert await orchestrator.handle("hello") == "You said: hello"
    await orchestrator.wait_background()


async def test_no_background_extraction_when_remember_was_used(tmp_path, events) -> None:
    memory = manager(tmp_path, '{"facts": ["Should not be stored"]}')
    registry = ToolRegistry()
    registry.register(RememberTool(memory))
    llm = FakeLLM(script=[ChatResult(content="", tool_calls=[ToolCall(id="r", name="remember",
                                                                        arguments={"fact": "Likes chai"})]),
                          reply("Noted.")])
    orchestrator = Orchestrator(llm, registry, Session(lambda: "SYS"), AllowAllGate(), events, memory=memory)
    await orchestrator.handle("remember that I like chai")
    await orchestrator.wait_background()
    assert [f.text for f in memory.search("chai stored", min_score=0.0)] == ["Likes chai"]
