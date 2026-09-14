"""Permission gates consulted before any tool with requires_permission=True runs."""
from __future__ import annotations

import asyncio
import uuid
from typing import Protocol

from assistant.events import Emit, EventType


class PermissionGate(Protocol):
    async def request(self, tool_name: str, summary: str) -> bool: ...


class AllowAllGate:
    async def request(self, tool_name: str, summary: str) -> bool:
        return True


class DenyAllGate:
    async def request(self, tool_name: str, summary: str) -> bool:
        return False


def _set_if_pending(future: asyncio.Future[bool], value: bool) -> None:
    if not future.done():
        future.set_result(value)


class WebSocketPermissionGate:
    """Asks the UI via a permission_request event; unanswered requests are denied after timeout_s."""

    def __init__(self, emit: Emit, timeout_s: float = 30.0) -> None:
        self._emit = emit
        self._timeout_s = timeout_s
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def request(self, tool_name: str, summary: str) -> bool:
        request_id = uuid.uuid4().hex[:12]
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        self._emit(EventType.PERMISSION_REQUEST, {"id": request_id, "tool": tool_name, "summary": summary})
        try:
            return await asyncio.wait_for(future, self._timeout_s)
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending.pop(request_id, None)

    def resolve(self, request_id: str, allowed: bool) -> None:
        future = self._pending.get(request_id)
        if future is not None and not future.done():
            future.get_loop().call_soon_threadsafe(_set_if_pending, future, bool(allowed))