"""Fan-out of server events to every connected WebSocket, in strict FIFO order, callable from any thread."""
from __future__ import annotations

import asyncio
import contextlib
from enum import Enum
from typing import Any

from fastapi import WebSocket


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


class ConnectionHub:
    def __init__(self) -> None:
        self._clients: set[Any] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[dict[str, Any]] | None = None
        self._pump_task: asyncio.Task[None] | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._queue = asyncio.Queue()
        self._pump_task = loop.create_task(self._pump())

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("ConnectionHub.bind_loop() has not been called")
        return self._loop

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, type_: str, payload: Any) -> None:
        assert self._queue is not None
        self._queue.put_nowait(self._message(type_, payload))

    def emit(self, type_: str, payload: Any) -> None:
        assert self._queue is not None
        self.loop.call_soon_threadsafe(self._queue.put_nowait, self._message(type_, payload))

    async def drain(self) -> None:
        assert self._queue is not None
        await asyncio.sleep(0)
        await self._queue.join()

    async def close(self) -> None:
        if self._pump_task is not None:
            self._pump_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pump_task
            self._pump_task = None

    @staticmethod
    def _message(type_: str, payload: Any) -> dict[str, Any]:
        return {"type": str(_plain(type_)), "payload": _plain(payload)}

    async def _pump(self) -> None:
        assert self._queue is not None
        while True:
            message = await self._queue.get()
            try:
                for ws in list(self._clients):
                    try:
                        await ws.send_json(message)
                    except Exception:
                        self._clients.discard(ws)
            finally:
                self._queue.task_done()