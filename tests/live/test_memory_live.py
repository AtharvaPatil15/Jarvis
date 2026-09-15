import pytest

from assistant.brain.llm import LLMClient
from assistant.config import Settings
from assistant.memory.db import MemoryDB
from assistant.memory.manager import MemoryManager

pytestmark = pytest.mark.live


@pytest.fixture
def memory(tmp_path) -> MemoryManager:
    s = Settings(_env_file=None)
    return MemoryManager(MemoryDB(tmp_path / "m.db"),
                         LLMClient(s.ollama_url, s.chat_model, s.embed_model, disable_thinking=s.llm_disable_thinking))


def test_live_extraction_finds_personal_facts(memory) -> None:
    facts = " ".join(memory.extract_facts("My favourite colour is teal and my sister is called Priya.", "Noted.")).lower()
    assert "teal" in facts and "priya" in facts


def test_live_extraction_ignores_plain_questions(memory) -> None:
    assert memory.extract_facts("What's the weather like in Mumbai today?", "It is sunny and 31 degrees.") == []


def test_live_semantic_search_prefers_the_right_fact(memory) -> None:
    memory.remember("The user's favourite colour is teal")
    memory.remember("The user's sister is called Priya")
    assert "teal" in memory.search("which colour do I like best?", min_score=0.0)[0].text
