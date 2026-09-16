"""Show which installed app each name resolves to, without launching anything."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from assistant.tools.builtin.system import OpenAppTool  # noqa: E402

if __name__ == "__main__":
    tool = OpenAppTool(launcher=lambda target: None)
    for name in sys.argv[1:] or ["chrome", "vs code", "spotify", "notepad", "calculator"]:
        print(f"{name!r:>16} -> {tool.resolve(name)}")
