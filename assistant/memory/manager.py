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
