# assistant/memory/store.py
import json
from pathlib import Path

MEMORY_FILE = Path("assistant_memory.json")

class MemoryStore:
    def __init__(self):
        if not MEMORY_FILE.exists():
            MEMORY_FILE.write_text(json.dumps({}))

    def load(self) -> dict:
        return json.loads(MEMORY_FILE.read_text())

    def save(self, data: dict):
        MEMORY_FILE.write_text(json.dumps(data, indent=2))

    def get(self, key, default=None):
        data = self.load()
        return data.get(key, default)

    def set(self, key, value):
        data = self.load()
        data[key] = value
        self.save(data)
