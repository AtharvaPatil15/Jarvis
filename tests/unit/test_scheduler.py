from datetime import datetime, timedelta, timezone

from assistant.memory.db import MemoryDB
from assistant.scheduler import ReminderScheduler
from tests.helpers import wait_until

NOW = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def test_due_reminders_fire_once_and_are_marked_done(tmp_path) -> None:
    fired: list[tuple[int, str]] = []
    scheduler = ReminderScheduler(MemoryDB(tmp_path / "m.db"), lambda i, t: fired.append((i, t)), clock=lambda: NOW)
    past = scheduler.schedule("stretch", NOW - timedelta(minutes=1))
    future = scheduler.schedule("call mom", NOW + timedelta(hours=1))
    assert scheduler.check_now() == [past]
    assert scheduler.check_now() == []
    assert fired == [(past, "stretch")]
    assert [i for i, _, _ in scheduler.pending()] == [future]


def test_background_thread_fires_and_survives_listener_errors(tmp_path) -> None:
    fired: list[str] = []

    def listener(reminder_id: int, text: str) -> None:
        fired.append(text)
        raise RuntimeError("listener bug")

    db = MemoryDB(tmp_path / "m.db")
    scheduler = ReminderScheduler(db, listener, poll_s=0.02)
    scheduler.schedule("first", datetime.now(timezone.utc) - timedelta(seconds=1))
    scheduler.start()
    try:
        wait_until(lambda: fired == ["first"], timeout=2)
        scheduler.schedule("second", datetime.now(timezone.utc) - timedelta(seconds=1))
        wait_until(lambda: fired == ["first", "second"], timeout=2)
    finally:
        scheduler.stop()


def test_reminders_survive_a_restart(tmp_path) -> None:
    path = tmp_path / "m.db"
    ReminderScheduler(MemoryDB(path), lambda i, t: None, clock=lambda: NOW).schedule("water", NOW + timedelta(minutes=5))
    later = NOW + timedelta(minutes=10)
    fired: list[str] = []
    assert len(ReminderScheduler(MemoryDB(path), lambda i, t: fired.append(t), clock=lambda: later).check_now()) == 1
    assert fired == ["water"]