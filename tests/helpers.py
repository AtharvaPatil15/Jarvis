from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

IDLE = {"type": "state_change", "payload": "idle"}


def wait_until(predicate: Callable[[], bool], timeout: float = 2.0, interval: float = 0.02) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    raise AssertionError(f"condition not met within {timeout} s")


def receive_until_idle(ws: Any, limit: int = 200) -> list[dict]:
    received: list[dict] = []
    for _ in range(limit):
        message = ws.receive_json()
        received.append(message)
        if message == IDLE:
            return received
    raise AssertionError(f"no idle state within {limit} messages: {received[-10:]}")