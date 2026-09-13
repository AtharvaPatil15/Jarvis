# Phase 4 — Long-term memory

Order: **P4-T1 → P4-T2 → P4-T3 → P4-T4**. After P4-T4: full gate, then `git push origin testing`.

---

## P4-T1: `MemoryDB`, redaction, and logging every turn

**Goal:** A single SQLite database (`data/jarvis.db`) for messages, facts and reminders; sensitive values are redacted
before anything is written; every user and assistant turn is logged. Tests never touch the real `data/` folder.

**Depends on:** P2-T6.

**Files:**
- Create: `assistant/memory/db.py`, `assistant/memory/redact.py`, `assistant/memory/manager.py`,
  `tests/unit/test_memory_db.py`, `tests/unit/test_redact.py`, `tests/unit/test_memory_logging.py`, `docs/proof/P4-T1.md`
- Modify: `assistant/orchestrator.py` (log turns), `assistant/runtime.py` (build DB + manager), `tests/conftest.py`
  (isolated data dir)
- Delete (`git rm`, after `git grep` shows no importers): `assistant/memory/store.py`, `assistant/memory/cache.py`,
  `assistant/memory/contacts.py`, `assistant/memory/user_profile.py`

**Interfaces — Produces:** `MemoryDB` (PLAN §3.8) plus `close() -> None`; `redact(text) -> str`;
`MemoryManager(db, llm, dedupe_threshold=0.9)` with `log_turn` (the rest arrives in P4-T2/T3);
`Runtime.db`, `Runtime.memory`. Reminder datetimes must be timezone-aware (naive → `ValueError`); they are stored in
UTC and returned as aware UTC datetimes.

- [ ] **Step 1: Isolate test data** — append to `tests/conftest.py`

```python
@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path / "data"))
```

- [ ] **Step 2: Write the failing tests**

`tests/unit/test_memory_db.py`:
```python
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from assistant.memory.db import MemoryDB

IST = ZoneInfo("Asia/Kolkata")


def test_messages_are_stored_per_session_in_order(tmp_path) -> None:
    db = MemoryDB(tmp_path / "m.db")
    for i in range(5):
        db.add_message("s1", "user", f"hello {i}")
    db.add_message("s2", "user", "other session")
    assert db.recent_messages("s1", 3) == [("user", "hello 2"), ("user", "hello 3"), ("user", "hello 4")]
    assert db.recent_messages("s2", 10) == [("user", "other session")]


def test_facts_round_trip_embeddings_as_float32(tmp_path) -> None:
    db = MemoryDB(tmp_path / "m.db")
    fact_id = db.add_fact("likes teal", [0.1, 0.2, 0.3])
    (row,) = db.all_facts()
    assert row[0] == fact_id and row[1] == "likes teal"
    assert row[2].dtype == np.float32 and np.allclose(row[2], [0.1, 0.2, 0.3])
    assert db.delete_fact(fact_id) is True
    assert db.delete_fact(fact_id) is False
    assert db.all_facts() == []


def test_reminders_due_pending_and_done_across_time_zones(tmp_path) -> None:
    db = MemoryDB(tmp_path / "m.db")
    now = datetime(2026, 9, 13, 18, 0, tzinfo=IST)
    past = db.add_reminder("stretch", now - timedelta(minutes=5))
    future = db.add_reminder("call mom", now + timedelta(hours=1))
    due = db.due_reminders(now)
    assert [(i, text) for i, text, _ in due] == [(past, "stretch")]
    assert due[0][2] == now - timedelta(minutes=5)
    assert [i for i, _, _ in db.pending_reminders()] == [past, future]
    db.mark_reminder_done(past)
    assert db.due_reminders(now) == []
    assert [i for i, _, _ in db.pending_reminders()] == [future]


def test_naive_reminder_times_are_rejected(tmp_path) -> None:
    with pytest.raises(ValueError):
        MemoryDB(tmp_path / "m.db").add_reminder("x", datetime(2026, 1, 1, 9, 0))


def test_data_survives_reopening(tmp_path) -> None:
    path = tmp_path / "nested" / "m.db"
    db = MemoryDB(path)
    db.add_fact("owns a cat", [1.0, 0.0])
    db.close()
    assert [text for _, text, _ in MemoryDB(path).all_facts()] == ["owns a cat"]


def test_concurrent_writes_are_safe(tmp_path) -> None:
    db = MemoryDB(tmp_path / "m.db")

    def writer(n: int) -> None:
        for i in range(50):
            db.add_message(f"s{n}", "user", str(i))

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(len(db.recent_messages(f"s{n}", 100)) for n in range(4)) == 200
```

`tests/unit/test_redact.py`:
```python
import pytest

from assistant.memory.redact import redact


@pytest.mark.parametrize(("text", "expected"), [
    ("mail me at atharva.p@example.com please", "mail me at [email] please"),
    ("my number is +91 98765 43210", "my number is [phone]"),
    ("card 4111 1111 1111 1111 expires soon", "card [card] expires soon"),
    ("aadhaar 1234 5678 9012", "aadhaar [id-number]"),
    ("my password is hunter2", "my password is [redacted]"),
    ("PIN: 4821", "PIN: [redacted]"),
])
def test_sensitive_values_are_replaced(text: str, expected: str) -> None:
    assert redact(text) == expected


def test_api_keys_are_replaced() -> None:
    key = "sk-" + "a" * 24
    assert redact(f"use {key} now") == "use [secret] now"


@pytest.mark.parametrize("text", ["meet at 5:30 tomorrow", "the year 2026 was busy", "call me at 10", "room 404"])
def test_ordinary_text_is_untouched(text: str) -> None:
    assert redact(text) == text
```

`tests/unit/test_memory_logging.py`:
```python
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
```
Run: `.venv/Scripts/python.exe -m pytest tests/unit/test_memory_db.py tests/unit/test_redact.py tests/unit/test_memory_logging.py -q`
Expected: FAIL — modules missing.

- [ ] **Step 3: Write `assistant/memory/redact.py`**

```python
"""Replaces sensitive values before anything is written to disk."""
from __future__ import annotations

import re

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:sk-|gh[pousr]_|AIza)[A-Za-z0-9_-]{16,}\b"), "[secret]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email]"),
    (re.compile(r"\b\d(?:[ -]?\d){12,18}\b"), "[card]"),
    (re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b"), "[id-number]"),
    (re.compile(r"(?<!\w)(?:\+?\d{1,3}[ -]?)?\d(?:[ -]?\d){9,11}(?!\w)"), "[phone]"),
    (re.compile(r"(?i)\b(password|passcode|pin|otp)\b(\s*(?:is|:|=)\s*)\S+"), r"\1\2[redacted]"),
]


def redact(text: str) -> str:
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text
```

- [ ] **Step 4: Write `assistant/memory/db.py`**

```python
"""SQLite storage for conversation messages, remembered facts and reminders."""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
    content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, embedding BLOB NOT NULL,
    dim INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL, due_at TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_utc_text(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("reminder times must be timezone-aware")
    return moment.astimezone(timezone.utc).isoformat()


class MemoryDB:
    def __init__(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)

    def add_message(self, session_id: str, role: str, content: str) -> int:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, _utc_now()))
            return int(cursor.lastrowid)

    def recent_messages(self, session_id: str, limit: int) -> list[tuple[str, str]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)).fetchall()
        return [(role, content) for role, content in reversed(rows)]

    def add_fact(self, text: str, embedding: list[float]) -> int:
        vector = np.asarray(embedding, dtype=np.float32)
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO facts(text, embedding, dim, created_at) VALUES (?, ?, ?, ?)",
                (text, vector.tobytes(), int(vector.size), _utc_now()))
            return int(cursor.lastrowid)

    def all_facts(self) -> list[tuple[int, str, np.ndarray]]:
        with self._lock:
            rows = self._conn.execute("SELECT id, text, embedding FROM facts ORDER BY id").fetchall()
        return [(int(i), text, np.frombuffer(blob, dtype=np.float32).copy()) for i, text, blob in rows]

    def delete_fact(self, fact_id: int) -> bool:
        with self._lock, self._conn:
            return self._conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,)).rowcount > 0

    def add_reminder(self, text: str, due_at: datetime) -> int:
        due = _to_utc_text(due_at)
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "INSERT INTO reminders(text, due_at, created_at) VALUES (?, ?, ?)", (text, due, _utc_now()))
            return int(cursor.lastrowid)

    def due_reminders(self, now: datetime) -> list[tuple[int, str, datetime]]:
        return self._reminders("done = 0 AND due_at <= ?", (_to_utc_text(now),))

    def pending_reminders(self) -> list[tuple[int, str, datetime]]:
        return self._reminders("done = 0", ())

    def mark_reminder_done(self, reminder_id: int) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _reminders(self, where: str, params: tuple) -> list[tuple[int, str, datetime]]:
        with self._lock:
            rows = self._conn.execute(
                f"SELECT id, text, due_at FROM reminders WHERE {where} ORDER BY due_at, id", params).fetchall()
        return [(int(i), text, datetime.fromisoformat(due)) for i, text, due in rows]
```

- [ ] **Step 5: Write the first part of `assistant/memory/manager.py`**

```python
"""Long-term memory: turn logging, fact storage with semantic search, and fact extraction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from assistant.memory.db import MemoryDB
from assistant.memory.redact import redact


@dataclass(frozen=True)
class Fact:
    id: int
    text: str
    score: float


class MemoryManager:
    def __init__(self, db: MemoryDB, llm: Any, dedupe_threshold: float = 0.9) -> None:
        self._db = db
        self._llm = llm
        self._dedupe = dedupe_threshold

    def log_turn(self, session_id: str, role: str, content: str) -> None:
        if content.strip():
            self._db.add_message(session_id, role, redact(content))
```

- [ ] **Step 6: Log turns in the orchestrator and build memory in the runtime**

In `assistant/orchestrator.py` add:
```python
    async def _log(self, role: str, content: str) -> None:
        if self.memory is None:
            return
        try:
            await asyncio.to_thread(self.memory.log_turn, self.session_id, role, content)
        except Exception:
            log.exception("could not log %s turn", role)
```
Call `await self._log("user", text)` right after `self.session.add_user(text)`, and `await self._log("assistant", reply)`
immediately before `self._emit(EventType.AI_RESPONSE, reply)`.

In `assistant/runtime.py`: add `db: MemoryDB` and `memory: MemoryManager` fields to `Runtime`; in `build_runtime` create
`db = MemoryDB(settings.data_dir / "jarvis.db")` and `memory = MemoryManager(db, llm)`, call
`build_default_registry(settings, memory=memory)`, pass `memory=memory` to `Orchestrator`, and return both new fields.

- [ ] **Step 7: Remove the unused legacy memory modules**

```powershell
git grep -nE "memory\.store|memory\.cache|memory\.contacts|memory\.user_profile|MemoryStore|KnowledgeCache|ContactBook|UserProfile" -- "*.py"
```
Must print nothing; then `git rm assistant/memory/store.py assistant/memory/cache.py assistant/memory/contacts.py assistant/memory/user_profile.py`.

- [ ] **Step 8: Verify, gate, proof, commit**

```powershell
.venv/Scripts/python.exe -m pytest tests/unit -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add assistant/memory assistant/orchestrator.py assistant/runtime.py tests/conftest.py tests/unit/test_memory_db.py tests/unit/test_redact.py tests/unit/test_memory_logging.py docs/proof/P4-T1.md docs/PROGRESS.md
git status --short
git commit -m "feat(memory): SQLite memory store with redaction and turn logging [P4-T1]" -m "Proof: docs/proof/P4-T1.md"
```
Expected: `6` DB + `11` redaction + `2` logging tests pass; whole suite green.

**Acceptance criteria:** nothing sensitive in the test list reaches the database; tests never write to `./data`.

---

## P4-T2: Remember, search, forget — and relevant memories in the system prompt

**Goal:** Facts are stored with embeddings, near-duplicates are skipped, and before every turn the most relevant facts
are placed in the system prompt.

**Depends on:** P4-T1.

**Files:**
- Modify: `assistant/memory/manager.py`, `assistant/orchestrator.py` (`current_memories`), `assistant/runtime.py` (prompt uses them)
- Create: `tests/unit/test_memory_manager.py`, `tests/unit/test_memory_recall.py`, `docs/proof/P4-T2.md`

**Interfaces — Produces:** `MemoryManager.remember/search/forget`, `Fact` (PLAN §3.8); `Orchestrator.current_memories: list[str]`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_memory_manager.py`:
```python
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
```

`tests/unit/test_memory_recall.py`:
```python
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
```
Run → FAIL.

- [ ] **Step 2: Add to `MemoryManager`**

```python
    def remember(self, text: str) -> int | None:
        clean = redact(text).strip()
        if not clean:
            return None
        vector = self._normalised(self._llm.embed([clean])[0])
        for _, _, existing in self._db.all_facts():
            if existing.shape == vector.shape and float(existing @ vector) >= self._dedupe:
                return None
        return self._db.add_fact(clean, vector.tolist())

    def search(self, query: str, k: int = 5, min_score: float = 0.35) -> list[Fact]:
        facts = self._db.all_facts()
        if not facts or not query.strip():
            return []
        target = self._normalised(self._llm.embed([query])[0])
        scored = [Fact(id=i, text=text, score=float(vector @ target))
                  for i, text, vector in facts if vector.shape == target.shape]
        matches = sorted((f for f in scored if f.score >= min_score), key=lambda f: f.score, reverse=True)
        return matches[:k]

    def forget(self, fact_id: int) -> bool:
        return self._db.delete_fact(fact_id)

    @staticmethod
    def _normalised(vector: list[float]) -> np.ndarray:
        array = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(array))
        return array / norm if norm else array
```

- [ ] **Step 3: Recall before each turn**

In `Orchestrator.__init__` add `self.current_memories: list[str] = []`. Add:
```python
    async def _recall(self, text: str) -> list[str]:
        if self.memory is None:
            return []
        try:
            return [fact.text for fact in await asyncio.to_thread(self.memory.search, text)]
        except Exception as exc:
            log.warning("memory search failed: %s", exc)
            return []
```
In `handle`, right after logging the user turn: `self.current_memories = await self._recall(text)`.

In `assistant/runtime.py`, make the prompt read them:
```python
    box: dict[str, Orchestrator] = {}
    session = Session(lambda: build_system_prompt(settings, datetime.now(zone), box["orchestrator"].current_memories),
                      max_chars=settings.history_max_chars)
    orchestrator = Orchestrator(llm, registry, session, gate, emit, memory=memory, max_steps=settings.max_agent_steps)
    box["orchestrator"] = orchestrator
```

- [ ] **Step 4: Verify, gate, proof, commit**

```powershell
.venv/Scripts/python.exe -m pytest tests/unit -q
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add assistant/memory/manager.py assistant/orchestrator.py assistant/runtime.py tests/unit/test_memory_manager.py tests/unit/test_memory_recall.py docs/proof/P4-T2.md docs/PROGRESS.md
git commit -m "feat(memory): semantic fact memory injected into the system prompt [P4-T2]" -m "Proof: docs/proof/P4-T2.md"
```

**Acceptance criteria:** only relevant facts reach the prompt; a failing embedding model never breaks a turn.

---

## P4-T3: Automatic fact extraction and memory tools

**Goal:** After each exchange JARVIS quietly extracts durable facts about the user (in the background, never delaying the
reply), and the model can explicitly `remember`, `recall` and `forget` (forget needs permission).

**Depends on:** P4-T2.

**Files:**
- Modify: `assistant/memory/manager.py` (`extract_facts`, `process_exchange`), `assistant/orchestrator.py` (background
  learning, `wait_background`), `assistant/tools/builtin/__init__.py` (register memory tools)
- Create: `assistant/tools/builtin/memory_tools.py`, `tests/unit/test_memory_extraction.py`, `tests/unit/test_memory_tools.py`,
  `tests/live/test_memory_live.py`, `docs/proof/P4-T3.md`

**Interfaces — Produces:** `MemoryManager.extract_facts(user_text, assistant_text) -> list[str]` (≤ 5 facts, each ≤ 200 chars),
`process_exchange(...) -> list[int]`; constant `EXTRACTION_PROMPT`; `Orchestrator.wait_background() -> None` (awaits pending
learning tasks); tools `RememberTool(memory)` (`remember`, arg `fact: str`), `RecallTool(memory)` (`recall`, arg `query: str`,
output lines `"<id>: <fact>"` or `"Nothing relevant is remembered."`), `ForgetTool(memory)` (`forget`, arg `fact_id: int`,
`requires_permission = True`). Background extraction is skipped when the turn already called `remember` successfully or
when the reply is the LLM-failure apology.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_memory_extraction.py`:
```python
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
```

`tests/unit/test_memory_tools.py`:
```python
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
```
Run → FAIL.

- [ ] **Step 2: Extraction in `MemoryManager`**

Add `from assistant.utils.json_utils import extract_json` and:
```python
EXTRACTION_PROMPT = (
    "You maintain long-term memory for a personal assistant. From the exchange below, extract durable facts about the "
    "USER that will still matter in future conversations: preferences, names of people close to them, goals, projects, "
    "routines and personal details they chose to share. Ignore questions, requests, small talk and general world facts. "
    'Write each fact as a short statement. Reply with JSON only, exactly {"facts": ["..."]}, '
    'or {"facts": []} when nothing is worth remembering.'
)
MAX_FACTS = 5
MAX_FACT_CHARS = 200
```
Methods:
```python
    def extract_facts(self, user_text: str, assistant_text: str) -> list[str]:
        messages = [{"role": "system", "content": EXTRACTION_PROMPT},
                    {"role": "user", "content": f"USER: {user_text}\nASSISTANT: {assistant_text}"}]
        data = extract_json(self._llm.chat(messages, temperature=0.0, max_tokens=256).content)
        facts = data.get("facts") if isinstance(data, dict) else None
        if not isinstance(facts, list):
            return []
        cleaned = [f.strip()[:MAX_FACT_CHARS] for f in facts if isinstance(f, str) and f.strip()]
        return cleaned[:MAX_FACTS]

    def process_exchange(self, user_text: str, assistant_text: str) -> list[int]:
        stored = []
        for fact in self.extract_facts(user_text, assistant_text):
            fact_id = self.remember(fact)
            if fact_id is not None:
                stored.append(fact_id)
        return stored
```

- [ ] **Step 3: Write `assistant/tools/builtin/memory_tools.py`**

```python
from __future__ import annotations

from pydantic import BaseModel, Field

from assistant.memory.manager import MemoryManager
from assistant.tools.base import BaseTool


class RememberArgs(BaseModel):
    fact: str = Field(description="Short statement about the user to keep, e.g. 'Favourite colour is teal'")


class RememberTool(BaseTool):
    name = "remember"
    description = "Save a fact about the user to long-term memory when they ask you to remember something."
    Args = RememberArgs

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def run(self, args: RememberArgs) -> str:
        fact_id = self._memory.remember(args.fact)
        return "I already remember that." if fact_id is None else f"Remembered (id {fact_id}): {args.fact}"


class RecallArgs(BaseModel):
    query: str = Field(description="What to look up in long-term memory")


class RecallTool(BaseTool):
    name = "recall"
    description = "Search long-term memory for facts about the user. Each line is '<id>: <fact>'."
    Args = RecallArgs

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def run(self, args: RecallArgs) -> str:
        facts = self._memory.search(args.query, k=5, min_score=0.25)
        return "\n".join(f"{f.id}: {f.text}" for f in facts) if facts else "Nothing relevant is remembered."


class ForgetArgs(BaseModel):
    fact_id: int = Field(description="Id of the fact to delete, as shown by recall")


class ForgetTool(BaseTool):
    name = "forget"
    description = "Delete one remembered fact by id. Call recall first to find the id."
    Args = ForgetArgs
    requires_permission = True

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def run(self, args: ForgetArgs) -> str:
        if self._memory.forget(args.fact_id):
            return f"Forgotten fact {args.fact_id}."
        return f"ERROR: no remembered fact with id {args.fact_id}"
```
In `build_default_registry`, when `memory is not None`, register `RememberTool(memory)`, `RecallTool(memory)`, `ForgetTool(memory)`.

- [ ] **Step 4: Background learning in `Orchestrator`**

In `__init__`: `self._background: set[asyncio.Task[None]] = set()` and `self._turn_tools: list[tuple[str, bool]] = []`.
At the start of `handle` (after the blank check): `self._turn_tools = []`. At the end of `_run_tool`, before returning:
`self._turn_tools.append((call.name, ok))`. In `handle`, after emitting `AI_RESPONSE`:
```python
        remembered = any(name == "remember" and ok for name, ok in self._turn_tools)
        if self.memory is not None and reply != APOLOGY and not remembered:
            task = asyncio.create_task(self._learn(text, reply))
            self._background.add(task)
            task.add_done_callback(self._background.discard)
```
Add:
```python
    async def _learn(self, user_text: str, reply: str) -> None:
        try:
            await asyncio.to_thread(self.memory.process_exchange, user_text, reply)
        except Exception as exc:
            log.warning("memory extraction failed: %s", exc)

    async def wait_background(self) -> None:
        if self._background:
            await asyncio.gather(*list(self._background), return_exceptions=True)
```
Run the unit tests → `7` extraction + `2` tool tests pass, whole suite green.

- [ ] **Step 5: Live extraction and embedding test** — `tests/live/test_memory_live.py`

```python
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
```
Run → `3 passed`. If extraction is unreliable, improve `EXTRACTION_PROMPT` (never the assertions) and record it.

- [ ] **Step 6: Gate, proof, commit**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add assistant/memory/manager.py assistant/orchestrator.py assistant/tools/builtin tests/unit/test_memory_extraction.py tests/unit/test_memory_tools.py tests/live/test_memory_live.py docs/proof/P4-T3.md docs/PROGRESS.md
git commit -m "feat(memory): background fact extraction and remember/recall/forget tools [P4-T3]" -m "Proof: docs/proof/P4-T3.md"
```

**Acceptance criteria:** replies never wait for extraction; forgetting requires permission; live extraction passes.

---

## P4-T4: Memory survives a restart — live proof

**Goal:** Prove with the real model and real database that JARVIS remembers across backend restarts and can forget on
request (with permission).

**Depends on:** P4-T3.

**Files:**
- Create: `tests/live/test_memory_persistence_live.py`, `scripts/memory_inspect.py`, `docs/proof/P4-T4.md`

- [ ] **Step 1: Write the live test**

```python
import pytest
from fastapi.testclient import TestClient

import server
from assistant.config import Settings
from assistant.memory.db import MemoryDB
from tests.helpers import IDLE

pytestmark = [pytest.mark.live, pytest.mark.timeout(900)]


def converse(settings: Settings, utterances: list[str], approve: bool = True) -> list[str]:
    app = server.create_app(settings)
    replies: list[str] = []
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        for text in utterances:
            ws.send_json({"type": "user_text", "payload": text})
            while True:
                message = ws.receive_json()
                if message["type"] == "permission_request":
                    ws.send_json({"type": "permission_response",
                                  "payload": {"id": message["payload"]["id"], "allowed": approve}})
                elif message["type"] == "ai_response":
                    replies.append(message["payload"])
                elif message == IDLE:
                    break
        client.portal.call(app.state.orchestrator.wait_background)
    return replies


def teal_facts(settings: Settings) -> list[str]:
    db = MemoryDB(settings.data_dir / "jarvis.db")
    try:
        return [text for _, text, _ in db.all_facts() if "teal" in text.lower()]
    finally:
        db.close()


def test_memory_survives_restart_and_can_be_forgotten(tmp_path) -> None:
    settings = Settings(_env_file=None, voice_enabled=False, data_dir=tmp_path / "data")
    converse(settings, ["Please remember that my favourite colour is teal."])
    assert teal_facts(settings), "fact was not stored"
    (answer,) = converse(settings, ["What is my favourite colour?"])
    assert "teal" in answer.lower()
    converse(settings, ["Please forget my favourite colour."])
    assert teal_facts(settings) == []
```

- [ ] **Step 2: Write `scripts/memory_inspect.py`**

```python
"""Print what JARVIS remembers (facts, message count, pending reminders) from the configured database."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from assistant.config import get_settings  # noqa: E402
from assistant.memory.db import MemoryDB  # noqa: E402


def main() -> int:
    path = get_settings().data_dir / "jarvis.db"
    if not path.is_file():
        print(f"no database at {path}")
        return 1
    db = MemoryDB(path)
    facts = db.all_facts()
    print(f"database: {path}")
    print(f"facts: {len(facts)}")
    for fact_id, text, _ in facts:
        print(f"  {fact_id}: {text}")
    print(f"pending reminders: {len(db.pending_reminders())}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the live test and a restart transcript on the real backend**

```powershell
.venv/Scripts/python.exe -m pytest tests/live/test_memory_persistence_live.py -q
$env:JARVIS_DATA_DIR = "docs/proof/tmp/memory-proof"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Start -NoVoice
.venv/Scripts/python.exe scripts/conversation_smoke.py "Please remember that my favourite colour is teal."
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Stop
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Start -NoVoice
.venv/Scripts/python.exe scripts/conversation_smoke.py "What is my favourite colour?"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/backend.ps1 -Stop
.venv/Scripts/python.exe scripts/memory_inspect.py
Remove-Item Env:JARVIS_DATA_DIR
```
Expected: live test `1 passed`; the second transcript's answer mentions teal after a full process restart;
`memory_inspect.py` lists the teal fact.

- [ ] **Step 4: Gates, proof, commit, push (end of phase)**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1 -Quick
git add tests/live/test_memory_persistence_live.py scripts/memory_inspect.py docs/proof/P4-T4.md docs/PROGRESS.md
git commit -m "test(memory): live proof that memory survives restarts and can be forgotten [P4-T4]" -m "Proof: docs/proof/P4-T4.md"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_all.ps1
git push origin testing
```

**Acceptance criteria:** the live test and the two-process transcript both show recall after restart; forgetting removes
the fact only after permission is granted.
