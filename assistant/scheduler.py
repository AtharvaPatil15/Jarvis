"""Polls the database for due reminders and notifies listeners exactly once per reminder."""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone

from assistant.memory.db import MemoryDB

log = logging.getLogger("jarvis.scheduler")


class ReminderScheduler:
    def __init__(self, db: MemoryDB, on_due: Callable[[int, str], None], poll_s: float = 5.0,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._db = db
        self._on_due = on_due
        self._poll_s = poll_s
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def schedule(self, text: str, due_at: datetime) -> int:
        return self._db.add_reminder(text, due_at)

    def pending(self) -> list[tuple[int, str, datetime]]:
        return self._db.pending_reminders()

    def check_now(self) -> list[int]:
        fired: list[int] = []
        for reminder_id, text, _ in self._db.due_reminders(self._clock()):
            self._db.mark_reminder_done(reminder_id)
            fired.append(reminder_id)
            try:
                self._on_due(reminder_id, text)
            except Exception:
                log.exception("reminder listener failed for %s", reminder_id)
        return fired

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="reminders", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.check_now()
            except Exception:
                log.exception("reminder check failed")
            self._stop.wait(self._poll_s)