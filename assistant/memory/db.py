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
