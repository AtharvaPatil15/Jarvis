from __future__ import annotations

import time
from collections.abc import Callable


def wait_until(predicate: Callable[[], bool], timeout: float = 2.0, interval: float = 0.02) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    raise AssertionError(f"condition not met within {timeout} s")