"""Print what JARVIS remembers (facts, message count, pending reminders) from the configured database."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from assistant.config import get_settings  # noqa: E402
from assistant.memory.db import MemoryDB  # noqa: E402


def main() -> int:
    path = get_settings().data_dir / "jarvis.db"
    if not path.is_file():
        print(f"no database at {path}")
        return 1
    db = MemoryDB(path)
    facts = db.all_facts()
    print(f"database: {path}")
    print(f"facts: {len(facts)}")
    for fact_id, text, _ in facts:
        print(f"  {fact_id}: {text}")
    print(f"pending reminders: {len(db.pending_reminders())}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
