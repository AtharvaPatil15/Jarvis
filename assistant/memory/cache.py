# assistant/memory/cache.py
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("assistant_memory.db")


class KnowledgeCache:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT UNIQUE,
            answer TEXT,
            last_used TIMESTAMP
        )
        """)
        self.conn.commit()

    def get(self, query: str) -> str | None:
        cur = self.conn.execute(
            "SELECT answer FROM knowledge_cache WHERE query = ?",
            (query.lower(),)
        )
        row = cur.fetchone()
        if row:
            self.conn.execute(
                "UPDATE knowledge_cache SET last_used = ? WHERE query = ?",
                (datetime.utcnow(), query.lower())
            )
            self.conn.commit()
            return row[0]
        return None

    def set(self, query: str, answer: str):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO knowledge_cache (query, answer, last_used)
            VALUES (?, ?, ?)
            """,
            (query.lower(), answer, datetime.utcnow())
        )
        self.conn.commit()
