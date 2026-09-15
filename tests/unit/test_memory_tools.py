from assistant.brain.fake_llm import FakeLLM
from assistant.config import Settings
from assistant.memory.db import MemoryDB
from assistant.memory.manager import MemoryManager
from assistant.tools.builtin import build_default_registry
from assistant.tools.builtin.memory_tools import ForgetTool, RecallTool, RememberTool


def test_remember_recall_forget_round_trip(tmp_path) -> None:
    memory = MemoryManager(MemoryDB(tmp_path / "m.db"), FakeLLM())
    remember, recall, forget = RememberTool(memory), RecallTool(memory), ForgetTool(memory)
    assert remember.run(remember.parse_args({"fact": "Sister is called Priya"})).startswith("Remembered (id ")
    assert remember.run(remember.parse_args({"fact": "sister is called priya"})) == "I already remember that."
    listing = recall.run(recall.parse_args({"query": "sister"}))
    fact_id = int(listing.split(":")[0])
    assert listing == f"{fact_id}: Sister is called Priya"
    assert forget.requires_permission is True
    assert forget.run(forget.parse_args({"fact_id": fact_id})) == f"Forgotten fact {fact_id}."
    assert forget.run(forget.parse_args({"fact_id": fact_id})) == f"ERROR: no remembered fact with id {fact_id}"
    assert recall.run(recall.parse_args({"query": "sister"})) == "Nothing relevant is remembered."


def test_memory_tools_are_registered_only_with_memory(tmp_path) -> None:
    settings = Settings(_env_file=None)
    assert "recall" not in build_default_registry(settings).names()
    memory = MemoryManager(MemoryDB(tmp_path / "m.db"), FakeLLM())
    assert {"remember", "recall", "forget"} <= set(build_default_registry(settings, memory=memory).names())
