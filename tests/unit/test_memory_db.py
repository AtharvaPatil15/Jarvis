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
