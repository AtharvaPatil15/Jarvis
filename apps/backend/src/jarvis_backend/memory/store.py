import json

from jarvis_backend.paths import STATE_DIR, ensure_runtime_dirs


ensure_runtime_dirs()
MEMORY_FILE = STATE_DIR / "assistant_memory.json"


class MemoryStore:
    def __init__(self):
        if not MEMORY_FILE.exists():
            MEMORY_FILE.write_text(json.dumps({}))
        self.conversation_history = []

    def add_turn(self, user_text: str, assistant_text: str):
        self.conversation_history.append({
            "user": user_text,
            "assistant": assistant_text,
        })
        self.conversation_history = self.conversation_history[-5:]

    def get_recent_history(self):
        return self.conversation_history

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
