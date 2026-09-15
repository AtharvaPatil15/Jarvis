from assistant.brain.fake_llm import FakeLLM
from assistant.memory.db import MemoryDB
from assistant.memory.manager import MemoryManager


def make(tmp_path) -> MemoryManager:
    return MemoryManager(MemoryDB(tmp_path / "m.db"), FakeLLM())


def test_remember_redacts_and_skips_near_duplicates(tmp_path) -> None:
    memory = make(tmp_path)
    assert isinstance(memory.remember("My favourite colour is teal"), int)
    assert memory.remember("my favourite colour is teal!") is None
    assert isinstance(memory.remember("my email is x@y.com"), int)
    assert memory.search("email", k=5, min_score=0.0)[0].text == "my email is [email]"


def test_search_ranks_relevant_facts_and_applies_limits(tmp_path) -> None:
    memory = make(tmp_path)
    for text in ["favourite colour is teal", "sister is called Priya", "works on a JARVIS assistant project"]:
        memory.remember(text)
    results = memory.search("what is my favourite colour")
    assert results[0].text == "favourite colour is teal"
    assert all(fact.score >= 0.35 for fact in results)
    assert len(memory.search("favourite colour sister project", k=2, min_score=0.0)) == 2


def test_empty_memory_and_blank_queries_return_nothing(tmp_path) -> None:
    memory = make(tmp_path)
    assert memory.search("anything") == []
    memory.remember("owns a cat")
    assert memory.search("   ") == []


def test_forget_removes_a_fact(tmp_path) -> None:
    memory = make(tmp_path)
    fact_id = memory.remember("owns a cat")
    assert memory.forget(fact_id) is True
    assert memory.search("cat", min_score=0.0) == []
    assert memory.forget(fact_id) is False
