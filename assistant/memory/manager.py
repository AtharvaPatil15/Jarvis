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
