from assistant.brain.fake_llm import FakeLLM
from assistant.brain.session import Session
from assistant.config import Settings
from assistant.memory.db import MemoryDB
from assistant.memory.manager import MemoryManager
from assistant.orchestrator import Orchestrator
from assistant.runtime import build_runtime
from assistant.safety.permissions import AllowAllGate
from assistant.tools.registry import ToolRegistry


async def test_turns_are_logged_with_redaction(tmp_path, events) -> None:
    db = MemoryDB(tmp_path / "m.db")
    orchestrator = Orchestrator(FakeLLM(), ToolRegistry(), Session(lambda: "SYS"), AllowAllGate(), events,
                                memory=MemoryManager(db, FakeLLM()))
    await orchestrator.handle("my email is a.b@example.com")
    assert db.recent_messages(orchestrator.session_id, 10) == [
        ("user", "my email is [email]"),
        ("assistant", "You said: my email is [email]"),
    ]


def test_runtime_creates_the_database_in_the_data_dir(tmp_path) -> None:
    settings = Settings(_env_file=None, llm_backend="fake", data_dir=tmp_path / "data")
    runtime = build_runtime(settings, emit=lambda t, p: None, gate=AllowAllGate())
    assert (tmp_path / "data" / "jarvis.db").is_file()
    assert runtime.memory is not None and runtime.orchestrator.memory is runtime.memory
