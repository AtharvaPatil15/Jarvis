"""Text chat with JARVIS in the terminal: .venv/Scripts/python.exe main.py"""
from __future__ import annotations

import asyncio
from collections.abc import Callable

from assistant.config import get_settings
from assistant.runtime import build_runtime


class ConsolePermissionGate:
    async def request(self, tool_name: str, summary: str) -> bool:
        answer = await asyncio.to_thread(input, f"Allow {summary}? [y/N] ")
        return answer.strip().lower() in ("y", "yes")


async def repl(read: Callable[[str], str] = input, write: Callable[[str], None] = print) -> None:
    runtime = build_runtime(get_settings(), emit=lambda type_, payload: None, gate=ConsolePermissionGate())
    runtime.reminder_listeners.append(lambda _id, text: write(f"jarvis> Reminder: {text}"))
    runtime.scheduler.start()
    try:
        write("JARVIS text mode. Type 'exit' to quit.")
        while True:
            try:
                line = await asyncio.to_thread(read, "you> ")
            except EOFError:
                break
            if line.strip().lower() in ("exit", "quit"):
                break
            reply = await runtime.orchestrator.handle(line)
            if reply:
                write(f"jarvis> {reply}")
    finally:
        runtime.scheduler.stop()


if __name__ == "__main__":
    asyncio.run(repl())