"""Long-term memory: turn logging, fact storage with semantic search, and fact extraction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from assistant.memory.db import MemoryDB
from assistant.memory.redact import redact
from assistant.utils.json_utils import extract_json

EXTRACTION_PROMPT = (
    "You maintain long-term memory for a personal assistant. From the exchange below, extract durable facts about the "
    "USER that will still matter in future conversations: preferences, names of people close to them, goals, projects, "
    "routines and personal details they chose to share. Ignore questions, requests, small talk and general world facts. "
    'Write each fact as a short statement. Reply with JSON only, exactly {"facts": ["..."]}, '
    'or {"facts": []} when nothing is worth remembering.'
)
MAX_FACTS = 5
MAX_FACT_CHARS = 200


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

    @staticmethod
    def _normalised(vector: list[float]) -> np.ndarray:
        array = np.asarray(vector, dtype=np.float32)
        norm = float(np.linalg.norm(array))
        return array / norm if norm else array
